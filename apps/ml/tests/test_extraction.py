import unittest
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from ml_service.config import Settings
from ml_service.errors import EvaluationFailure
from ml_service.extraction import DOCX, PDF, TXT, DocumentInput, extract_document, extract_isolated


def docx_bytes(*paragraphs: str, table: bool = False) -> bytes:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    if table:
        row = document.add_table(rows=1, cols=2).rows[0]
        row.cells[0].text = "Критерий"
        row.cells[1].text = "Результат"
        document.add_paragraph("После таблицы")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def pdf_bytes(*texts: str) -> bytes:
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=400, height=400)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 10 380 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(_env_file=None)

    def test_pdf_all_pages_and_markers(self):
        text = extract_document(DocumentInput("lab.pdf", PDF, pdf_bytes("First page", "Second page")), self.settings)
        self.assertIn("First page", text)
        self.assertIn("Second page", text)
        self.assertIn("[Страница 2]", text)

    def test_docx_cyrillic_and_table_in_document_order(self):
        text = extract_document(DocumentInput("lab.docx", DOCX, docx_bytes("До таблицы", table=True)), self.settings)
        self.assertLess(text.index("До таблицы"), text.index("Критерий | Результат"))
        self.assertLess(text.index("Результат"), text.index("После таблицы"))

    def test_utf8_teacher_file(self):
        text = extract_document(DocumentInput("guide.txt", TXT, "\ufeffМетодичка\nPython: x = 1".encode()), self.settings)
        self.assertEqual(text, "Методичка\nPython: x = 1")

    def test_empty_text_and_scans(self):
        for document in (DocumentInput("empty.pdf", PDF, pdf_bytes("")), DocumentInput("empty.docx", DOCX, docx_bytes("  "))):
            with self.subTest(document.filename), self.assertRaises(EvaluationFailure) as caught:
                extract_document(document, self.settings)
            self.assertEqual(caught.exception.code, "DOCUMENT_NO_TEXT")

    def test_corrupt_and_wrong_extension(self):
        for document, code in ((DocumentInput("bad.pdf", PDF, b"%PDF-corrupt"), "DOCUMENT_INVALID"), (DocumentInput("bad.exe", DOCX, b"x"), "UNSUPPORTED_FILE_TYPE")):
            with self.subTest(code), self.assertRaises(EvaluationFailure) as caught:
                extract_document(document, self.settings)
            self.assertEqual(caught.exception.code, code)

    def test_compressed_docx_bound(self):
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"x" * 10_000)
        with self.assertRaises(EvaluationFailure) as caught:
            extract_document(DocumentInput("bomb.docx", DOCX, buffer.getvalue()), Settings(_env_file=None, max_docx_uncompressed_bytes=100))
        self.assertEqual(caught.exception.code, "DOCUMENT_TOO_LARGE")

    def test_page_and_text_bounds(self):
        with self.assertRaises(EvaluationFailure):
            extract_document(DocumentInput("lab.pdf", PDF, pdf_bytes("A", "B")), Settings(_env_file=None, max_pages=1))
        with self.assertRaises(EvaluationFailure):
            extract_document(DocumentInput("guide.txt", TXT, b"a" * 100), Settings(_env_file=None, max_document_chars=10))


class IsolatedExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_child_process_round_trip(self):
        text = await extract_isolated(DocumentInput("lab.docx", DOCX, docx_bytes("Кириллица в дочернем процессе")), Settings(_env_file=None))
        self.assertIn("Кириллица", text)
