import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from fastapi.testclient import TestClient

from core import db

main = None


def make_pdf(path, text=None):
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


class PdfIngestionTests(unittest.TestCase):
    def setUp(self):
        global main
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.raw_dir = self.root / "raw_pdfs"
        self.slide_dir = self.root / "slides"
        self.raw_dir.mkdir()
        self.slide_dir.mkdir()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(self.root / "test.db")
        if main is None:
            main = importlib.import_module("main")
        from core.ingestion_jobs import _run_job, resume_pending_jobs

        self.run_job = _run_job
        self.resume_pending_jobs = resume_pending_jobs
        self.old_raw_dir = main.RAW_PDF_DIR
        self.old_slide_dir = main.COURSE_SLIDE_DIR
        main.RAW_PDF_DIR = self.raw_dir
        main.COURSE_SLIDE_DIR = self.slide_dir
        db.init_db()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        db.DB_PATH = self.old_db_path
        main.RAW_PDF_DIR = self.old_raw_dir
        main.COURSE_SLIDE_DIR = self.old_slide_dir
        self.temp_dir.cleanup()

    def test_ingest_repairs_stale_path_and_pdf_endpoint_serves_file(self):
        pdf_path = self.raw_dir / "lesson.pdf"
        make_pdf(pdf_path, "Enough native text for a valid cached page in this regression test.")
        db.upsert_document("lesson", r"D:\old-machine\lesson.pdf", 1)
        db.upsert_page("lesson", 1, "Cached page content")
        db.set_validated("lesson", True)

        response = self.client.post("/ingest", json={"pdf_filename": "lesson.pdf"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(Path(db.get_source_pdf_path("lesson")), pdf_path.resolve())
        pdf_response = self.client.get("/pdf/lesson")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF-"))

    def test_pdf_endpoint_rejects_database_path_outside_repo_directory(self):
        outside_pdf = self.root / "outside.pdf"
        make_pdf(outside_pdf, "This file must never be served by the endpoint.")
        db.upsert_document("outside", str(outside_pdf), 1)

        response = self.client.get("/pdf/outside")

        self.assertEqual(response.status_code, 404)

    def test_documents_include_repository_course_slides(self):
        slide_path = self.slide_dir / "day-one.pdf"
        make_pdf(slide_path, "Course slide available in the repository.")

        response = self.client.get("/documents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["pdf_filename"], "day-one.pdf")
        self.assertEqual(response.json()[0]["source"], "slides")

    def test_upload_endpoint_does_not_exist(self):
        response = self.client.post("/upload")

        self.assertEqual(response.status_code, 404)

    def test_ingest_rejects_path_instead_of_repository_filename(self):
        response = self.client.post("/ingest", json={"pdf_filename": "../outside.pdf"})

        self.assertEqual(response.status_code, 422)

    def test_summary_returns_conflict_before_ingestion_is_ready(self):
        pdf_path = self.raw_dir / "pending.pdf"
        make_pdf(pdf_path, "Pending document")
        db.upsert_document("pending", str(pdf_path), 1)

        response = self.client.get("/summary/pending")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["ingestion"]["status"], "not_started")

    def test_vision_failure_finishes_job_with_warning(self):
        pdf_path = self.raw_dir / "image-only.pdf"
        make_pdf(pdf_path)
        db.upsert_document("image-only", str(pdf_path), 1)
        job_id = db.create_ingestion_job("image-only", 1)

        with patch(
            "core.ingest.describe_page_with_vision_model",
            side_effect=RuntimeError("vision unavailable"),
        ):
            self.run_job(job_id, str(pdf_path))

        job = db.get_ingestion_job(job_id)
        self.assertEqual(job["status"], "ready_with_warnings")
        self.assertEqual(job["processed_pages"], 1)
        self.assertIn("vision unavailable", job["warnings"][0])
        self.assertTrue(db.is_ingested("image-only"))

    def test_resume_pending_job_uses_persisted_source_path(self):
        pdf_path = self.raw_dir / "resume.pdf"
        make_pdf(pdf_path, "Resume this document after a backend restart.")
        db.upsert_document("resume", str(pdf_path), 1)
        job_id = db.create_ingestion_job("resume", 1)

        with patch("core.ingestion_jobs.submit_job") as submit:
            self.resume_pending_jobs()

        submit.assert_called_once_with(job_id, os.path.abspath(pdf_path))


if __name__ == "__main__":
    unittest.main()
