from io import BytesIO
from pathlib import PurePath
from zipfile import BadZipFile, ZipFile

from docx import Document
from fastapi import UploadFile
from pypdf import PdfReader

from app.config import settings

ALLOWED_SETTING_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_ATTEMPT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def read_upload(file: UploadFile, allowed_types: set[str]) -> bytes:
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise ValueError("FILE_TOO_LARGE")
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise ValueError("UNSUPPORTED_FILE_TYPE")
    _validate_file_signature(file.filename or "", content_type, content)
    return content


def _validate_file_signature(filename: str, content_type: str, data: bytes) -> None:
    extension = PurePath(filename).suffix.lower()
    expected_extensions = {
        "application/pdf": {".pdf"},
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
        "text/plain": {".txt"},
    }
    if extension not in expected_extensions[content_type]:
        raise ValueError("UNSUPPORTED_FILE_TYPE")
    if content_type == "application/pdf" and not data.startswith(b"%PDF-"):
        raise ValueError("UNSUPPORTED_FILE_TYPE")
    if content_type == "text/plain":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("UNSUPPORTED_FILE_TYPE") from exc
    if content_type.endswith("wordprocessingml.document"):
        try:
            with ZipFile(BytesIO(data)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("UNSUPPORTED_FILE_TYPE")
        except BadZipFile as exc:
            raise ValueError("UNSUPPORTED_FILE_TYPE") from exc


def extract_text(data: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        document = Document(BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return data.decode("utf-8", errors="replace")
