#!/usr/bin/env python3
"""Export the grading report's Markdown subset to a self-contained Russian PDF.

Requires ReportLab and DejaVu fonts only; no network or model calls are made.
The Markdown remains the single source of report text and measurements.
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, TableStyle


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/ml-grading-evaluation.md"
OUTPUT = ROOT / "docs/reports/ml-grading-evaluation-2026-11-08.pdf"
GITHUB = "https://github.com/acuraels/moodle-lab-assessment-assistant/blob/main/"
NAVY = colors.HexColor("#17334b")
BLUE = colors.HexColor("#225f91")
MUTED = colors.HexColor("#526476")
INLINE = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)")


def register_fonts(directory: Path) -> None:
    for name, filename in (
        ("ReportSans", "DejaVuSans.ttf"),
        ("ReportSansBold", "DejaVuSans-Bold.ttf"),
        ("ReportMono", "DejaVuSansMono.ttf"),
    ):
        pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
    pdfmetrics.registerFontFamily("ReportSans", normal="ReportSans", bold="ReportSansBold")


def inline(text: str, source: Path, *, code_size: float = 8.4) -> str:
    parts, end = [], 0
    for match in INLINE.finditer(text):
        parts.append(escape(text[end:match.start()]))
        code, bold, label, target = match.groups()
        if code is not None:
            parts.append(f'<font name="ReportMono" size="{code_size}">{escape(code)}</font>')
        elif bold is not None:
            parts.append(f"<b>{escape(bold)}</b>")
        else:
            parsed = urlsplit(target)
            if parsed.scheme not in ("http", "https"):
                relative = (source.parent / parsed.path).resolve().relative_to(ROOT)
                target = GITHUB + quote(relative.as_posix(), safe="/")
                if parsed.fragment:
                    target += "#" + quote(parsed.fragment)
            parts.append(f'<a href="{escape(target, quote=True)}" color="#225f91">{escape(label)}</a>')
        end = match.end()
    parts.append(escape(text[end:]))
    return "".join(parts)


class ReportDocument(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "Section":
            title = flowable.getPlainText()
            bookmark = "section-" + str(self.seq.nextf("section"))
            self.canv.bookmarkPage(bookmark)
            self.canv.addOutlineEntry(title, bookmark, level=0)


def styles() -> dict[str, ParagraphStyle]:
    body = ParagraphStyle(
        "Body", fontName="ReportSans", fontSize=9.4, leading=14,
        textColor=NAVY, spaceAfter=9, splitLongWords=True,
        allowWidows=0, allowOrphans=0,
    )
    return {
        "body": body,
        "title": ParagraphStyle("Title", parent=body, fontName="ReportSansBold", fontSize=22,
                                leading=28, spaceAfter=18, keepWithNext=True),
        "section": ParagraphStyle("Section", parent=body, fontName="ReportSansBold", fontSize=14,
                                  leading=19, spaceBefore=14, spaceAfter=9, keepWithNext=True),
        "cell": ParagraphStyle("Cell", parent=body, fontSize=8.1, leading=11.3, spaceAfter=0),
        "head": ParagraphStyle("HeaderCell", parent=body, fontName="ReportSansBold", fontSize=8.0,
                               leading=11, spaceAfter=0, textColor=colors.white),
    }


def table(lines: list[str], source: Path, style: dict, width: float) -> LongTable:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    header, separator, *body = rows
    if len(header) != len(separator) or any(not re.fullmatch(r":?-+:?", cell) for cell in separator):
        raise ValueError("Malformed Markdown table")
    if any(len(row) != len(header) for row in body):
        raise ValueError("Inconsistent Markdown table column count")
    if len(header) == 6:
        fractions = [0.35, 0.155, 0.14, 0.12, 0.115, 0.12]
    elif header[0] == "Модель Ollama":
        fractions = [0.29, 0.20, 0.51]
    elif header[0] == "Документ":
        fractions = [0.26, 0.19, 0.33, 0.22]
    elif len(header) == 4:
        fractions = [0.43, 0.19, 0.19, 0.19]
    else:
        fractions = [1 / len(header)] * len(header)
    data = [[Paragraph(inline(value, source, code_size=7.1), style["head" if index == 0 else "cell"])
             for value in row] for index, row in enumerate([header, *body])]
    result = LongTable(data, colWidths=[width * fraction for fraction in fractions], repeatRows=1,
                       hAlign="LEFT", spaceBefore=3, spaceAfter=13)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f5f9"), colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, BLUE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#dce5ec")),
    ]))
    return result


def build(source: Path, output: Path, font_directory: Path) -> None:
    register_fonts(font_directory)
    content = source.read_text(encoding="utf-8")
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    if title_match is None:
        raise ValueError("Report needs a Markdown title")
    title = title_match.group(1)
    style = styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = ReportDocument(
        str(output), pagesize=A4, leftMargin=42, rightMargin=42, invariant=1,
        topMargin=48, bottomMargin=44, title=title,
        author="Moodle Lab Assessment Assistant", subject="Результаты и ограничения проверки оценивания",
        creator="scripts/export_grading_report.py / ReportLab",
    )
    story, lines, index = [], content.splitlines(), 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("# ") or line.startswith("## "):
            level = "title" if line.startswith("# ") else "section"
            story.append(Paragraph(inline(line.lstrip("# "), source), style[level]))
            index += 1
        elif line.startswith("|"):
            start = index
            while index < len(lines) and lines[index].strip().startswith("|"):
                index += 1
            story.append(table(lines[start:index], source, style, document.width))
        else:
            paragraph = []
            while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "|")):
                paragraph.append(lines[index].strip())
                index += 1
            if not paragraph:
                raise ValueError(f"Unsupported Markdown block at line {index + 1}")
            story.append(Paragraph(inline(" ".join(paragraph), source), style["body"]))

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dce5ec"))
        canvas.line(doc.leftMargin, 31, A4[0] - doc.rightMargin, 31)
        canvas.setFont("ReportSans", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, A4[1] - 28, "ML · Проверка лабораторных работ")
        canvas.drawString(doc.leftMargin, 19, "moodle-lab-assessment-assistant")
        canvas.drawRightString(A4[0] - doc.rightMargin, 19, f"Страница {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(f"PDF: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--font-directory", type=Path, default=Path("/usr/share/fonts/truetype/dejavu"))
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve(), args.font_directory)


if __name__ == "__main__":
    main()
