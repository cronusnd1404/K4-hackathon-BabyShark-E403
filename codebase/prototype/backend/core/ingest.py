"""PDF -> per-page content, mapped to real page numbers."""

import os
import re

import fitz

from core import db
from core.llm_client import describe_page_with_vision_model


def make_document_id(pdf_path):
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    return re.sub(r"[^A-Za-z0-9_-]", "_", stem)


def inspect_pdf(pdf_path):
    with fitz.open(pdf_path) as doc:
        if doc.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported")
        return len(doc)


def ingest_document(pdf_path, document_id=None, progress_callback=None):
    """Ingest all pages and continue with warnings when vision extraction fails."""
    document_id = document_id or make_document_id(pdf_path)
    warnings = []
    with fitz.open(pdf_path) as doc:
        if doc.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported")
        total_pages = len(doc)
        db.upsert_document(document_id, os.path.abspath(pdf_path), total_pages)
        db.remove_pages_after(document_id, total_pages)

        for i, page in enumerate(doc):
            page_number = i + 1
            native_text = page.get_text().strip()
            if len(native_text) >= 50:
                content_text = native_text
            else:
                try:
                    pix = page.get_pixmap(dpi=150)
                    content_text = describe_page_with_vision_model(pix.tobytes("png")).strip()
                    if not content_text:
                        raise ValueError("vision model returned empty text")
                except Exception as exc:
                    content_text = native_text or (
                        f"[Không thể trích xuất nội dung chữ từ trang {page_number}. "
                        "Vẫn có thể xem trang này trong PDF.]"
                    )
                    warnings.append(f"Trang {page_number}: {exc}")
            db.upsert_page(document_id, page_number, content_text)
            if progress_callback:
                progress_callback(page_number, total_pages, warnings)

    validated = db.count_pages(document_id) == total_pages
    db.set_validated(document_id, validated)
    if not validated:
        raise RuntimeError("Ingested page count does not match PDF page count")
    return document_id, warnings
