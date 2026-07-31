"""PDF -> per-page content, mapped to real page numbers."""

import os
import re

import fitz

from core import db
from core.llm_client import describe_page_with_vision_model


def make_document_id(pdf_path):
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    return re.sub(r"[^A-Za-z0-9_-]", "_", stem)


def ingest_document(pdf_path):
    """Returns (document_id, validated). Skips re-ingesting if already cached."""
    document_id = make_document_id(pdf_path)

    if db.is_ingested(document_id):
        return document_id, True

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    db.upsert_document(document_id, pdf_path, total_pages)

    for i, page in enumerate(doc):
        page_number = i + 1
        native_text = page.get_text().strip()
        if len(native_text) > 50:
            content_text = native_text
        else:
            pix = page.get_pixmap(dpi=150)
            content_text = describe_page_with_vision_model(pix.tobytes("png"))
        db.upsert_page(document_id, page_number, content_text)

    validated = db.count_pages(document_id) == total_pages
    db.set_validated(document_id, validated)
    return document_id, validated
