"""Multi-format document parsing: PDF, DOCX, PPTX, CSV/Excel, images, and
BPMN/Visio-exported XML. Every parser normalizes its output to plain text
(+ any tables found) so the LLM-based step extractor can work off one shape.
Formats without a dedicated parser here are rejected outright rather than
routed through a generic fallback - see UnsupportedFormatError.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pdfplumber
import pymupdf  # PyMuPDF, imported as `fitz` upstream but pymupdf works directly
from docx import Document as DocxDocument
from pptx import Presentation

from app.extraction.ocr import ocr_image, ocr_pil_image
from app.utils.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg",
    ".csv", ".xlsx", ".xls", ".bpmn", ".xml", ".txt",
}


class UnsupportedFormatError(Exception):
    """Raised for a file extension we don't have a parser for. Legacy
    .doc/.ppt/.vsdx are deliberately NOT supported: they were previously
    routed through unstructured.io's auto-partitioner, which shells out to
    LibreOffice to convert them and, when that's unavailable (as on a plain
    Python venv), doesn't raise a catchable Python exception - it hard-crashes
    the whole worker process (confirmed: exit code 0xC0000409, a native
    abort). That's a bigger risk than just not supporting the format, so
    there is no fallback parser here at all - anything without a dedicated
    parser below is rejected before it can be parsed.
    """


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Dependency-free stand-in for DataFrame.to_markdown() (which needs the
    optional `tabulate` package - not installed here, and pulling it in just
    for this was more than the task warranted).
    """
    if df.empty:
        return ""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        cells = ["" if pd.isna(v) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


@dataclass
class ExtractedDocument:
    filename: str
    file_type: str
    raw_text: str = ""
    tables: list[pd.DataFrame] = field(default_factory=list)
    table_labels: list[str] = field(default_factory=list)
    used_ocr: bool = False
    # Human-readable per-page/sheet/slide breakdown of what was found and
    # whether it was used - surfaced to the frontend so a user can see
    # *which* sheet/page/slide their steps came from (or why one was skipped).
    sources: list[str] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        parts = [self.raw_text]
        for i, table in enumerate(self.tables):
            label = self.table_labels[i] if i < len(self.table_labels) else f"Table {i + 1}"
            markdown = _dataframe_to_markdown(table)
            if markdown:
                parts.append(f"\n[{label}]\n{markdown}")
        return "\n".join(p for p in parts if p).strip()


def parse_pdf(path: Path) -> ExtractedDocument:
    """Extract text with PyMuPDF (fast, handles most native PDFs) and tables
    with pdfplumber. If a page yields near-zero text, treat it as a scanned
    image and fall back to OCR via PyMuPDF's page render.
    """
    text_chunks: list[str] = []
    sources: list[str] = []
    used_ocr = False

    with pymupdf.open(path) as doc:
        for page_num, page in enumerate(doc):
            page_text = page.get_text().strip()
            page_used_ocr = False
            if len(page_text) < 20:
                # Likely a scanned/image-only page -> OCR it.
                pix = page.get_pixmap(dpi=200)
                import io

                from PIL import Image

                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = ocr_pil_image(img)
                if ocr_text:
                    used_ocr = True
                    page_used_ocr = True
                    page_text = ocr_text
            text_chunks.append(f"[Page {page_num + 1}]\n{page_text}")
            if page_text:
                sources.append(f"Page {page_num + 1}" + (" (OCR)" if page_used_ocr else "") + " - used")
            else:
                sources.append(f"Page {page_num + 1} - skipped (no text found)")

    tables: list[pd.DataFrame] = []
    table_labels: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                for table in page.extract_tables():
                    if table and len(table) > 1:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        tables.append(df)
                        table_labels.append(f"Table on page {page_num}")
    except Exception as exc:  # pragma: no cover
        logger.warning(f"pdfplumber table extraction failed for {path.name}: {exc}")

    return ExtractedDocument(
        filename=path.name, file_type="pdf", raw_text="\n\n".join(text_chunks),
        tables=tables, table_labels=table_labels, used_ocr=used_ocr, sources=sources,
    )


def parse_docx(path: Path) -> ExtractedDocument:
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    tables: list[pd.DataFrame] = []
    table_labels: list[str] = []
    for i, table in enumerate(doc.tables, start=1):
        rows = [[cell.text for cell in row.cells] for row in table.rows]
        if rows and len(rows) > 1:
            tables.append(pd.DataFrame(rows[1:], columns=rows[0]))
            table_labels.append(f"Table {i}")
    sources = [f"{len(paragraphs)} paragraph(s) of body text - used"]
    sources.extend(f"{label} - used" for label in table_labels)
    return ExtractedDocument(
        filename=path.name, file_type="docx", raw_text="\n".join(paragraphs),
        tables=tables, table_labels=table_labels, sources=sources,
    )


def parse_pptx(path: Path) -> ExtractedDocument:
    prs = Presentation(str(path))
    chunks: list[str] = []
    sources: list[str] = []
    for i, slide in enumerate(prs.slides, start=1):
        slide_lines = [f"[Slide {i}]"]
        had_content = False
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                slide_lines.append(shape.text_frame.text.strip())
                had_content = True
            if shape.has_table:
                rows = [[cell.text for cell in row.cells] for row in shape.table.rows]
                slide_lines.append("\n".join(" | ".join(r) for r in rows))
                had_content = True
        chunks.append("\n".join(slide_lines))
        sources.append(f"Slide {i} - used" if had_content else f"Slide {i} - skipped (no text found)")
    return ExtractedDocument(filename=path.name, file_type="pptx", raw_text="\n\n".join(chunks), sources=sources)


def parse_image(path: Path) -> ExtractedDocument:
    text = ocr_image(path)
    sources = ["Image (OCR) - used" if text else "Image (OCR) - skipped (no text recognized)"]
    return ExtractedDocument(filename=path.name, file_type="image", raw_text=text, used_ocr=True, sources=sources)


def _resolve_sheet_hint(hint: str | None, sheet_names: list[str]) -> str | None:
    """Best-effort match of a free-form user instruction (typed in the same
    text box used for manual step entry, e.g. "Extract sheet 3 of the
    attached file" or "use the Process Steps tab") to one of the workbook's
    actual sheet names. Returns None - meaning "use every sheet" - if the
    hint is empty or doesn't resolve to anything; this instruction is
    always optional, never required.
    """
    if not hint or not hint.strip():
        return None
    hint = hint.strip()

    for name in sheet_names:
        if name.lower() == hint.lower():
            return name
    for name in sheet_names:
        if name.lower() in hint.lower():
            return name

    match = re.search(r"sheet\s*#?\s*(\d+)", hint, re.IGNORECASE) or \
        re.search(r"\b(\d+)(?:st|nd|rd|th)?\s*sheet\b", hint, re.IGNORECASE)
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(sheet_names):
            return sheet_names[idx]
    return None


def parse_spreadsheet(path: Path, sheet_hint: str | None = None) -> ExtractedDocument:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        tables = [df] if not df.dropna(how="all").empty else []
        labels = ["CSV data"] if tables else []
        sources = [f"CSV data ({len(df)} row(s)) - used"] if tables else ["CSV data - skipped (empty)"]
        return ExtractedDocument(
            filename=path.name, file_type="spreadsheet", tables=tables, table_labels=labels, sources=sources,
        )

    sheets = pd.read_excel(path, sheet_name=None)
    resolved = _resolve_sheet_hint(sheet_hint, list(sheets.keys()))

    tables: list[pd.DataFrame] = []
    labels: list[str] = []
    sources: list[str] = []
    for name, df in sheets.items():
        if resolved and name != resolved:
            sources.append(f"Sheet '{name}' - skipped (using '{resolved}' per your instruction)")
            continue
        if df.dropna(how="all").empty:
            sources.append(f"Sheet '{name}' - skipped (empty)")
            continue
        tables.append(df)
        labels.append(f"Sheet: {name}")
        sources.append(f"Sheet '{name}' ({len(df)} row(s)) - used")

    return ExtractedDocument(
        filename=path.name, file_type="spreadsheet", tables=tables, table_labels=labels, sources=sources,
    )


def parse_bpmn_or_xml(path: Path) -> ExtractedDocument:
    """BPMN files (and Visio's flat XML export) are XML with human-readable
    labels on <bpmn:task name="..."> / <bpmn:sequenceFlow> style elements.
    We don't attempt full BPMN schema parsing - we extract every `name`
    attribute in document order, which reliably captures step labels for
    both BPMN 2.0 XML and Visio XML exports.
    """
    raw = path.read_text(encoding="utf-8", errors="ignore")
    names = re.findall(r'name="([^"]+)"', raw)
    text = "\n".join(f"- {n}" for n in names if n.strip())
    sources = [f"{len(names)} named element(s) - used" if names else "No named elements found - skipped"]
    return ExtractedDocument(filename=path.name, file_type="bpmn", raw_text=text, sources=sources)


def parse_txt(path: Path) -> ExtractedDocument:
    text = path.read_text(encoding="utf-8", errors="ignore")
    sources = ["Full text content - used" if text.strip() else "File is empty - skipped"]
    return ExtractedDocument(filename=path.name, file_type="txt", raw_text=text, sources=sources)


_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
    ".png": parse_image,
    ".jpg": parse_image,
    ".jpeg": parse_image,
    ".csv": parse_spreadsheet,
    ".xlsx": parse_spreadsheet,
    ".xls": parse_spreadsheet,
    ".bpmn": parse_bpmn_or_xml,
    ".xml": parse_bpmn_or_xml,
    ".txt": parse_txt,
}


def parse_document(path: str | Path, sheet_hint: str | None = None) -> ExtractedDocument:
    path = Path(path)
    ext = path.suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise UnsupportedFormatError(
            f"'{ext or path.name}' files aren't supported. Please save as .pdf / .docx / .pptx / "
            ".xlsx / .csv / .png / .jpg and re-upload."
        )
    logger.info(f"Parsing '{path.name}' with {parser.__name__}")
    if parser is parse_spreadsheet:
        return parser(path, sheet_hint=sheet_hint)
    return parser(path)
