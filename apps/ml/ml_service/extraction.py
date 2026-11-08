import asyncio
import json
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from ml_service.config import Settings
from ml_service.errors import EvaluationFailure

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT = "text/plain"
EXTENSIONS = {PDF: ".pdf", DOCX: ".docx", TXT: ".txt"}


@dataclass(frozen=True)
class DocumentInput:
    filename: str
    content_type: str
    data: bytes


def _check_file(document: DocumentInput, settings: Settings) -> None:
    if len(document.data) > settings.max_file_bytes:
        raise EvaluationFailure("FILE_TOO_LARGE", "Документ превышает допустимый размер.", status=413)
    if not document.data:
        raise EvaluationFailure("DOCUMENT_EMPTY", "Загружен пустой файл.")
    extension = PurePath(document.filename.replace("\\", "/")).suffix.lower()
    if EXTENSIONS.get(document.content_type) != extension:
        raise EvaluationFailure("UNSUPPORTED_FILE_TYPE", "Ожидается PDF, DOCX или TXT с корректным MIME-типом.", status=415)
    if document.content_type == PDF and not document.data.startswith(b"%PDF-"):
        raise EvaluationFailure("DOCUMENT_INVALID", "Файл не является корректным PDF.")


def _bounded_text(parts: list[str], settings: Settings) -> str:
    text = "\n".join(parts).replace("\x00", "").strip()
    if len(text) > settings.max_document_chars:
        raise EvaluationFailure("DOCUMENT_TOO_LARGE", "Извлечённый текст превышает допустимый объём.", status=413)
    return text


def _cell_text(cell, depth: int = 0) -> str:
    if depth > 10:
        raise EvaluationFailure("DOCUMENT_INVALID", "Слишком глубокая вложенность таблиц DOCX.")
    parts = []
    for block in cell.iter_inner_content():
        if isinstance(block, Paragraph):
            parts.append(block.text)
        elif isinstance(block, Table):
            parts.append(_table_text(block, depth + 1))
    return " / ".join(parts)


def _table_text(table: Table, depth: int = 0) -> str:
    rows = []
    for row in table.rows:
        cells = []
        previous = None
        for cell in row.cells:
            # Horizontal merged cells repeat the same XML node.
            if cell._tc is not previous:
                cells.append(_cell_text(cell, depth))
            previous = cell._tc
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def extract_document(document: DocumentInput, settings: Settings) -> str:
    """Synchronous parser. Production invokes this in a killable child process."""
    _check_file(document, settings)
    parts: list[str] = []
    has_text = False
    try:
        if document.content_type == TXT:
            parts = [document.data.decode("utf-8-sig")]
            has_text = bool(parts[0].strip())
        elif document.content_type == PDF:
            reader = PdfReader(BytesIO(document.data))
            if reader.is_encrypted:
                raise EvaluationFailure("DOCUMENT_ENCRYPTED", "PDF защищён шифрованием. Загрузите документ без пароля.")
            if len(reader.pages) > settings.max_pages:
                raise EvaluationFailure("DOCUMENT_TOO_LARGE", "В PDF превышено допустимое количество страниц.", status=413)
            for index, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                has_text = has_text or bool(text.strip())
                parts.append(f"[Страница {index}]\n{text}" if text.strip() else f"[Страница {index}: извлекаемого текста нет; изображения не анализировались]")
                _bounded_text(parts, settings)
        else:
            with ZipFile(BytesIO(document.data)) as archive:
                infos = archive.infolist()
                if len(infos) > 2048 or sum(item.file_size for item in infos) > settings.max_docx_uncompressed_bytes:
                    raise EvaluationFailure("DOCUMENT_TOO_LARGE", "Распакованный DOCX превышает допустимый объём.", status=413)
                if "word/document.xml" not in archive.namelist():
                    raise EvaluationFailure("DOCUMENT_INVALID", "DOCX не содержит основного документа.")
                if any(item.flag_bits & 1 for item in infos):
                    raise EvaluationFailure("DOCUMENT_ENCRYPTED", "Зашифрованные DOCX не поддерживаются.")
            document_object = Document(BytesIO(document.data))
            for block in document_object.iter_inner_content():
                text = block.text if isinstance(block, Paragraph) else _table_text(block)
                has_text = has_text or bool(text.strip())
                parts.append(text)
                _bounded_text(parts, settings)
    except EvaluationFailure:
        raise
    except Exception as exc:
        # Do not expose document text or parser internals to users or logs.
        raise EvaluationFailure("DOCUMENT_INVALID", "Документ повреждён или его текст невозможно прочитать.") from exc
    if not has_text:
        raise EvaluationFailure("DOCUMENT_NO_TEXT", "В документе нет доступного текста. Сканы и изображения требуют OCR; загрузите текстовый PDF или DOCX.")
    return _bounded_text(parts, settings)


async def extract_isolated(document: DocumentInput, settings: Settings) -> str:
    _check_file(document, settings)
    limits = {
        "max_file_bytes": settings.max_file_bytes,
        "max_document_chars": settings.max_document_chars,
        "max_pages": settings.max_pages,
        "max_docx_uncompressed_bytes": settings.max_docx_uncompressed_bytes,
    }
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "ml_service.extract_worker",
        document.content_type, document.filename, json.dumps(limits),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(document.data), settings.extraction_timeout_seconds)
    except (TimeoutError, asyncio.CancelledError) as exc:
        if process.returncode is None:
            process.kill()
        await process.wait()
        if isinstance(exc, asyncio.CancelledError):
            raise
        raise EvaluationFailure("EXTRACTION_TIMEOUT", "Превышено время извлечения текста из документа.") from exc
    if process.returncode != 0:
        raise EvaluationFailure("DOCUMENT_INVALID", "Не удалось обработать документ в доступных ресурсах.")
    try:
        result = json.loads(stdout)
    except (ValueError, UnicodeDecodeError) as exc:
        raise EvaluationFailure("DOCUMENT_INVALID", "Не удалось извлечь текст документа.") from exc
    if "error" in result:
        error = result["error"]
        raise EvaluationFailure(error["code"], error["message"], status=error.get("status", 422))
    return result["text"]
