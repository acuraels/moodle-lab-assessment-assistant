import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from assessment_contract.schemas import EvaluationRequest
from ml_service.config import Settings
from ml_service.errors import EvaluationFailure
from ml_service.extraction import DOCX, PDF, DocumentInput
from ml_service.pipeline import Evaluator

logger = logging.getLogger(__name__)


class StrictMultipartParser(MultiPartParser):
    completed = False

    def on_end(self) -> None:
        self.completed = True
        super().on_end()


def create_app(settings: Settings | None = None, evaluator: Evaluator | None = None) -> FastAPI:
    settings = settings or Settings()
    evaluator = evaluator or Evaluator(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await evaluator.close()

    application = FastAPI(title="Lab assessment internal ML", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.state.evaluator = evaluator

    def authenticate(request: Request) -> None:
        if settings.ml_token and not hmac.compare_digest(request.headers.get("X-ML-Token", "").encode("utf-8"), settings.ml_token.encode("utf-8")):
            raise EvaluationFailure("UNAUTHORIZED", "Недопустимый ключ доступа к ML-сервису.", status=401)

    @application.exception_handler(EvaluationFailure)
    async def evaluation_error(_: Request, exc: EvaluationFailure):
        return JSONResponse(status_code=exc.status, content=exc.payload())

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    @application.get("/ready")
    async def ready(request: Request):
        authenticate(request)
        if not await evaluator.ready():
            raise EvaluationFailure("MODEL_UNAVAILABLE", "Ollama недоступна или указанная модель не установлена.", retryable=True, status=503)
        return {"status": "ready", "model": settings.ollama_model}

    @application.post("/evaluate")
    async def evaluate(request: Request):
        authenticate(request)
        if not request.headers.get("content-type", "").startswith("multipart/form-data"):
            raise EvaluationFailure("INVALID_REQUEST", "Ожидается multipart/form-data.", status=400)
        try:
            declared_size = int(request.headers.get("content-length", "0"))
        except ValueError as exc:
            raise EvaluationFailure("INVALID_REQUEST", "Некорректный Content-Length.", status=400) from exc
        if declared_size > settings.max_request_bytes:
            raise EvaluationFailure("FILE_TOO_LARGE", "Запрос превышает допустимый размер.", status=413)

        async def bounded_stream():
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings.max_request_bytes:
                    # MultiPartParser closes spooled files on this exception.
                    raise MultiPartException("request_size_limit")
                yield chunk

        parser = StrictMultipartParser(request.headers, bounded_stream(), max_files=5, max_fields=1,
                                       max_part_size=1024 * 1024)
        try:
            try:
                async with asyncio.timeout(settings.upload_timeout_seconds):
                    form = await parser.parse()
                if not parser.completed:
                    raise MultiPartException("incomplete_multipart")
            except BaseException:
                # Starlette only closes these for MultiPartException, not syntax
                # errors, client disconnects or cancellation (tested version pinned).
                for temporary_file in parser._files_to_close_on_error:
                    temporary_file.close()
                raise
        except TimeoutError as exc:
            raise EvaluationFailure("INVALID_REQUEST", "Превышено время получения документов.", status=408) from exc
        except (MultiPartException, MultipartParseError) as exc:
            if str(exc) == "request_size_limit":
                raise EvaluationFailure("FILE_TOO_LARGE", "Запрос превышает допустимый размер.", status=413) from exc
            raise EvaluationFailure("INVALID_REQUEST", "Некорректная multipart-форма или превышены её ограничения.", status=400) from exc
        try:
            if len(form.multi_items()) != len(form):
                raise EvaluationFailure("INVALID_REQUEST", "Повторяющиеся поля запроса недопустимы.", status=400)
            metadata_value = form.get("metadata")
            if not isinstance(metadata_value, str):
                raise EvaluationFailure("INVALID_REQUEST", "Не переданы JSON-метаданные.", status=400)
            try:
                metadata = EvaluationRequest.model_validate_json(metadata_value)
            except ValidationError as exc:
                raise EvaluationFailure("INVALID_REQUEST", "Метаданные проверки не соответствуют контракту.", status=400) from exc
            expected_files = {item.file_key for item in metadata.materials.values() if item.file_key is not None}
            if set(form.keys()) != {"metadata", "submission", *expected_files}:
                raise EvaluationFailure("INVALID_REQUEST", "Файлы запроса не соответствуют указанным материалам.", status=400)
            documents = {}
            for key in {"submission", *expected_files}:
                upload = form.get(key)
                if not isinstance(upload, UploadFile):
                    raise EvaluationFailure("INVALID_REQUEST", "Ожидается файл документа.", status=400)
                data = await upload.read(settings.max_file_bytes + 1)
                if len(data) > settings.max_file_bytes:
                    raise EvaluationFailure("FILE_TOO_LARGE", "Документ превышает допустимый размер.", status=413)
                documents[key] = DocumentInput(upload.filename or "", upload.content_type or "", data)
            submission = documents.pop("submission")
            if submission.content_type not in {PDF, DOCX}:
                raise EvaluationFailure("UNSUPPORTED_FILE_TYPE", "Работа студента должна быть PDF или DOCX.", status=415)
            try:
                result = await evaluator.evaluate(metadata, submission, documents)
            except EvaluationFailure:
                raise
            except Exception:
                logger.error("evaluation_internal_error attempt_id=%r", metadata.attempt_id)
                raise EvaluationFailure("ML_INTERNAL_ERROR", "Внутренняя ошибка автоматической проверки.", status=500)
            return result.model_dump(mode="json")
        finally:
            await form.close()

    return application


app = create_app()
