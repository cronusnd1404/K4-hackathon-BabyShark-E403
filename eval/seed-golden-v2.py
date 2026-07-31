"""Seed an isolated SQLite database for the v2 golden-set runner."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: seed-golden-v2.py FIXTURE.json", file=sys.stderr)
        return 2
    if not os.environ.get("VLEARN_DB_PATH"):
        print("VLEARN_DB_PATH is required; refusing to seed the default database", file=sys.stderr)
        return 2

    fixture_path = Path(sys.argv[1]).resolve()
    backend_dir = Path(__file__).resolve().parents[1] / "codebase" / "prototype" / "backend"
    sys.path.insert(0, str(backend_dir))

    from core import db

    fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
    db.init_db()
    for document in fixture["documents"]:
        db.upsert_document(
            document["document_id"],
            document["source_pdf_path"],
            document["total_pages"],
        )
        for page in document.get("pages", []):
            db.upsert_page(
                document["document_id"],
                page["page_number"],
                page["content_text"],
            )
        db.set_validated(document["document_id"], document.get("validated", True))

    print(f"Seeded {len(fixture['documents'])} documents into {db.DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
