"""Bounded HTTP adapter; student files never go to cloud providers."""

import asyncio
import json
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from assessment_contract.schemas import EvaluationError, EvaluationRequest, EvaluationResult
from assessment_contract.rubric import parse_rubric, validate_result_for_rubric

from app.config import settings


MAX_RESPONSE_BYTES = 256 * 1024
ERROR_MESSAGES = {
    "ML_NOT_CONFIGURED": "Адрес сервиса автоматической проверки не настроен.",
    "ML_UNAVAILABLE": "Сервис проверки недоступен. Проверьте соединение с ML-сервером.",
    "ML_TIMEOUT": "Превышено время ожидания автоматической проверки.",
    "ML_AUTH_FAILED": "Backend не смог авторизоваться в сервисе проверки.",
    "ML_INVALID_RESPONSE": "Сервис проверки вернул некорректный результат.",
    "FILE_TOO_LARGE": "Размер документа превышает допустимый предел.",
    "UNSUPPORTED_FILE_TYPE": "Формат документа не поддерживается.",
    "DOCUMENT_EMPTY": "Документ пуст. Загрузите работу с текстом.",
    "DOCUMENT_INVALID": "Не удалось прочитать документ. Проверьте файл и загрузите его повторно.",
    "DOCUMENT_ENCRYPTED": "Документ защищён паролем. Загрузите доступную для чтения копию.",
    "DOCUMENT_TOO_LARGE": "Документ слишком велик для автоматической обработки.",
    "DOCUMENT_NO_TEXT": "В документе нет доступного текста. Сканы и текст на изображениях пока не распознаются.",
    "EXTRACTION_TIMEOUT": "Извлечение текста заняло слишком много времени.",
    "CONTEXT_TOO_LARGE": "Работа вместе с материалами превышает доступный объём контекста модели.",
    "INVALID_REQUEST": "Сервис проверки не смог принять подготовленные данные.",
    "UNAUTHORIZED": "Backend не смог авторизоваться в сервисе проверки.",
    "ML_BUSY": "Сервис проверки занят. Автоматические попытки обработки исчерпаны.",
    "MODEL_UNAVAILABLE": "Локальная модель недоступна на ML-сервере.",
    "MODEL_TIMEOUT": "Локальная модель не завершила проверку за отведённое время.",
    "MODEL_OUT_OF_MEMORY": "На ML-сервере недостаточно памяти для обработки документа.",
    "MODEL_INVALID_RESPONSE": "Модель не сформировала корректный результат проверки.",
    "INVALID_RUBRIC": "Критерии оценивания содержат некорректную числовую шкалу.",
    "ML_INTERNAL_ERROR": "В сервисе автоматической проверки произошла техническая ошибка.",
    "INVALID_SNAPSHOT": "Для попытки отсутствует корректный снимок материалов преподавателя.",
    "MATERIAL_NOT_FOUND": "Материал преподавателя, необходимый для проверки, недоступен.",
    "SUBMISSION_NOT_FOUND": "Файл этой попытки недоступен для проверки.",
    "PROCESSING_EXPIRED": "Истёк общий срок автоматической обработки. Работа сохранена.",
    "RETRY_LIMIT_EXCEEDED": "Автоматическая проверка прерывалась; допустимое число повторов исчерпано.",
}


class MLFailure(Exception):
    def __init__(self, code: str, *, retryable: bool = False):
        self.code = code if code in ERROR_MESSAGES else "ML_INTERNAL_ERROR"
        self.message = ERROR_MESSAGES[self.code]
        self.retryable = retryable
        super().__init__(self.code)


@dataclass
class EvaluationInput:
    metadata: EvaluationRequest
    files: list[tuple[str, tuple[str, bytes, str]]]


async def evaluate(payload: EvaluationInput, timeout_seconds: float) -> EvaluationResult:
    if not settings.ml_url:
        raise MLFailure("ML_NOT_CONFIGURED")
    headers = {"X-ML-Token": settings.ml_token} if settings.ml_token else {}
    try:
        async with asyncio.timeout(timeout_seconds):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout_seconds, connect=min(5, timeout_seconds)),
                trust_env=False,
                follow_redirects=False,
            ) as client:
                async with client.stream(
                    "POST", f"{settings.ml_url}/evaluate", headers=headers,
                    data={"metadata": payload.metadata.model_dump_json()}, files=payload.files,
                ) as response:
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > MAX_RESPONSE_BYTES:
                            raise MLFailure("ML_INVALID_RESPONSE")
                    if response.status_code != 200:
                        if response.status_code in {401, 403}:
                            raise MLFailure("ML_AUTH_FAILED")
                        try:
                            error = EvaluationError.model_validate(json.loads(data)["error"])
                        except (ValueError, KeyError, TypeError, ValidationError):
                            raise MLFailure("ML_UNAVAILABLE", retryable=response.status_code >= 500)
                        raise MLFailure(error.code, retryable=error.retryable)
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise MLFailure("ML_TIMEOUT", retryable=True) from exc
    except httpx.RequestError as exc:
        raise MLFailure("ML_UNAVAILABLE", retryable=True) from exc

    try:
        result = EvaluationResult.model_validate_json(data)
        material = payload.metadata.materials.get("grading_criteria")
        # Files are extracted only by ML. Text rubrics can also be compared here.
        if material is None or material.text is not None:
            rubric = parse_rubric(material.text if material else None)
            validate_result_for_rubric(result, rubric)
        return result
    except (ValueError, ValidationError) as exc:
        raise MLFailure("ML_INVALID_RESPONSE") from exc
