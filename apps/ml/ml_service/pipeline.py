import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable

import httpx
from pydantic import ValidationError
from tokenizers import Tokenizer

from assessment_contract.schemas import EvaluationRequest, EvaluationResult
from assessment_contract.rubric import parse_rubric, validate_result_for_rubric
from ml_service.config import Settings
from ml_service.errors import EvaluationFailure
from ml_service.extraction import DocumentInput, extract_isolated
from ml_service.grounding import GroundedAssessment, GroundingError, validate_and_adapt
from ml_service.prompts import PROMPT_VERSION, build_messages, correction_message

logger = logging.getLogger(__name__)


def ollama_output_schema(*, numeric: bool = False, criterion_count: int | None = None) -> dict:
    # Ollama 0.19's grammar parser rejects bounded repetitions above 2000.
    # Large string maxLength values become such repetitions and can stop its
    # runner. Omit them only from generation grammar; the full Pydantic result
    # validation below still enforces every length limit.
    schema = (GroundedAssessment if numeric else EvaluationResult).model_json_schema()
    if numeric and criterion_count is not None:
        schema["properties"]["criteria"].update(minItems=criterion_count, maxItems=criterion_count)
        schema["$defs"]["GroundedCriterion"]["properties"]["criterion_index"]["enum"] = list(range(criterion_count))
    if not numeric:
        # With no teacher scale, numerical grades are not a permitted output.
        schema["properties"]["score"] = {"type": "null"}
        schema["properties"]["max_score"] = {"type": "null"}
        schema["properties"]["criteria"]["maxItems"] = 0

    def remove_max_length(node: object) -> None:
        if isinstance(node, dict):
            node.pop("maxLength", None)
            for child in node.values():
                remove_max_length(child)
        elif isinstance(node, list):
            for child in node:
                remove_max_length(child)

    remove_max_length(schema)
    return schema


def check_context(messages: list[dict[str, str]], settings: Settings, tokenizer: Tokenizer | None = None) -> None:
    # Qwen byte-level BPE cannot require more tokens than source UTF-8 bytes.
    # Template/role overhead has its own margin; output reserve is separate.
    upper_bound = sum(
        len(tokenizer.encode(message["content"], add_special_tokens=False).ids)
        if tokenizer is not None else len(message["content"].encode("utf-8"))
        for message in messages
    )
    if upper_bound + settings.output_tokens + settings.context_margin_tokens > settings.context_tokens:
        raise EvaluationFailure("CONTEXT_TOO_LARGE", "Материалы и работа превышают безопасный бюджет контекста. Сократите документы или настройте больший контекст после проверки памяти.", status=413)


class Evaluator:
    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None,
                 extractor: Callable[[DocumentInput, Settings], Awaitable[str]] = extract_isolated):
        self.settings = settings
        self.client = client or httpx.AsyncClient(base_url=settings.ollama_url.rstrip("/"), trust_env=False)
        self._owns_client = client is None
        self.extractor = extractor
        self.gate = asyncio.Semaphore(1)
        self.tokenizer = Tokenizer.from_file(str(settings.tokenizer_path)) if settings.tokenizer_path is not None else None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def ready(self) -> bool:
        try:
            response = await self.client.get("/api/tags", timeout=5)
            response.raise_for_status()
            return any(model.get("name") == self.settings.ollama_model or model.get("model") == self.settings.ollama_model
                       for model in response.json().get("models", []))
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return False

    async def evaluate(self, metadata: EvaluationRequest, submission: DocumentInput,
                       files: dict[str, DocumentInput]) -> EvaluationResult:
        started = time.monotonic()
        try:
            await asyncio.wait_for(self.gate.acquire(), self.settings.queue_timeout_seconds)
        except TimeoutError as exc:
            raise EvaluationFailure("ML_BUSY", "Модель занята другой проверкой. Повторите запрос позднее.", retryable=True, status=503) from exc
        try:
            text = await self.extractor(submission, self.settings)
            materials = {}
            for category, material in metadata.materials.items():
                if material.text is not None:
                    materials[category] = material.text
                else:
                    if material.file_key not in files:
                        raise EvaluationFailure("INVALID_REQUEST", "Не передан файл материала преподавателя.", status=400)
                    materials[category] = await self.extractor(files[material.file_key], self.settings)
            try:
                rubric_text = re.sub(r"(?m)^\[Страница \d+\]\n?", "", materials.get("grading_criteria", ""))
                rubric = parse_rubric(rubric_text)
            except ValueError as exc:
                raise EvaluationFailure("INVALID_RUBRIC", "Числовые критерии имеют некорректный формат. Исправьте названия и максимальные баллы.") from exc
            base_messages = build_messages(metadata, text, materials, rubric)
            messages = base_messages
            numeric = rubric is not None
            for attempt in range(2):
                check_context(messages, self.settings, self.tokenizer)
                try:
                    raw = await self._generate(messages, numeric=numeric, criterion_count=len(rubric) if numeric else None)
                    data = json.loads(raw)
                    if numeric:
                        result = validate_and_adapt(data, rubric, text)
                    else:
                        result = EvaluationResult.model_validate(data)
                        validate_result_for_rubric(result, None)
                        limitation = "Числовая оценка не выставлялась: явная структурированная шкала с максимумами не задана."
                        if limitation not in result.conclusion:
                            data["conclusion"] = result.conclusion.rstrip() + " " + limitation
                            result = EvaluationResult.model_validate(data)
                    validate_result_for_rubric(result, rubric)
                    logger.info("evaluation_finished attempt_id=%r duration_seconds=%.3f model_calls=%d prompt_version=%s", metadata.attempt_id, time.monotonic() - started, attempt + 1, PROMPT_VERSION)
                    return result
                except (ValidationError, ValueError, TypeError, KeyError, EvaluationFailure) as exc:
                    if isinstance(exc, EvaluationFailure) and exc.code != "MODEL_INVALID_RESPONSE":
                        raise
                    hint = str(exc) if isinstance(exc, GroundingError) else "invalid_result"
                    if isinstance(exc, json.JSONDecodeError):
                        hint = "invalid_json"
                    logger.warning("assessment_validation_failed attempt_id=%r call=%d code=%s", metadata.attempt_id, attempt + 1, hint)
                    if attempt == 0:
                        messages = base_messages + [correction_message(hint, numeric=numeric)]
                    else:
                        raise EvaluationFailure("MODEL_INVALID_RESPONSE", "Модель не смогла вернуть корректный результат проверки.", status=502) from None
            raise AssertionError("unreachable")
        except EvaluationFailure as exc:
            logger.warning("evaluation_failed attempt_id=%r code=%s duration_seconds=%.3f", metadata.attempt_id, exc.code, time.monotonic() - started)
            raise
        finally:
            self.gate.release()

    async def _generate(self, messages: list[dict[str, str]], *, numeric: bool = False, criterion_count: int | None = None) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "format": ollama_output_schema(numeric=numeric, criterion_count=criterion_count),
            "stream": False,
            "keep_alive": "10m",
            "options": {"num_ctx": self.settings.context_tokens, "num_predict": self.settings.output_tokens, "temperature": 0, "seed": 42},
        }
        # Instruct-2507 is non-thinking. Other Qwen3 variants need this switch.
        if self.settings.ollama_model.startswith("qwen3:") and "instruct" not in self.settings.ollama_model:
            payload["think"] = False
        try:
            # An overall deadline also bounds servers that keep sending small chunks.
            async with asyncio.timeout(self.settings.ollama_timeout_seconds):
                async with self.client.stream("POST", "/api/chat", json=payload,
                                              timeout=httpx.Timeout(self.settings.ollama_timeout_seconds, connect=5)) as response:
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.settings.max_response_bytes:
                            raise EvaluationFailure("MODEL_INVALID_RESPONSE", "Ответ модели превышает допустимый размер.", status=502)
                    if response.is_error:
                        lower = bytes(body).lower()
                        if any(marker in lower for marker in (b"out of memory", b"cuda error", b"requires more system memory")):
                            raise EvaluationFailure("MODEL_OUT_OF_MEMORY", "Для запуска модели недостаточно памяти.", status=503)
                        raise EvaluationFailure("MODEL_UNAVAILABLE", "Модель недоступна или не загружена.", retryable=response.status_code >= 500 or response.status_code == 404, status=503)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise EvaluationFailure("MODEL_TIMEOUT", "Превышено время ожидания ответа модели.", retryable=True, status=504) from exc
        except httpx.HTTPError as exc:
            raise EvaluationFailure("MODEL_UNAVAILABLE", "Нет соединения с локальной моделью.", retryable=True, status=503) from exc
        try:
            output = json.loads(body)
            content = output["message"]["content"]
            if output.get("done") is not True or output.get("done_reason") == "length" or not isinstance(content, str):
                raise ValueError("incomplete model output")
            return content
        except (ValueError, KeyError, TypeError) as exc:
            raise EvaluationFailure("MODEL_INVALID_RESPONSE", "Модель вернула неполный или некорректный ответ.", status=502) from exc
