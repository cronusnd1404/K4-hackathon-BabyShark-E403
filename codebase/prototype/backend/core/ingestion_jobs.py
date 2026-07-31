"""Single-worker ingestion queue persisted in SQLite."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor

from core import db
from core.ingest import ingest_document, inspect_pdf, make_document_id


READY_STATUSES = {"ready", "ready_with_warnings"}
ACTIVE_STATUSES = {"queued", "processing"}

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pdf-ingest")
_submitted = set()
_submitted_lock = threading.Lock()


def _public_result(document_id, status, total_pages, job_id=None, warnings=None, error=None):
    return {
        "document_id": document_id,
        "status": status,
        "job_id": job_id,
        "processed_pages": total_pages if status in READY_STATUSES else 0,
        "total_pages": total_pages,
        "warnings": warnings or [],
        "error": error,
    }


def queue_document(pdf_path):
    """Repair document path and enqueue extraction only when cache is incomplete."""
    pdf_path = os.path.abspath(pdf_path)
    document_id = make_document_id(pdf_path)
    total_pages = inspect_pdf(pdf_path)
    db.upsert_document(document_id, pdf_path, total_pages)

    if db.is_ingested(document_id) and db.count_pages(document_id) == total_pages:
        latest = db.get_latest_ingestion_job(document_id)
        warnings = latest["warnings"] if latest and latest["status"] in READY_STATUSES else []
        status = "ready_with_warnings" if warnings else "ready"
        return _public_result(document_id, status, total_pages, warnings=warnings)

    latest = db.get_latest_ingestion_job(document_id)
    if latest and latest["status"] in ACTIVE_STATUSES:
        submit_job(latest["job_id"], pdf_path)
        return latest

    db.reset_document_validation(document_id)
    job_id = db.create_ingestion_job(document_id, total_pages)
    submit_job(job_id, pdf_path)
    return db.get_ingestion_job(job_id)


def submit_job(job_id, pdf_path):
    with _submitted_lock:
        if job_id in _submitted:
            return
        _submitted.add(job_id)
    _executor.submit(_run_job, job_id, os.path.abspath(pdf_path))


def _run_job(job_id, pdf_path):
    warnings = []
    try:
        job = db.get_ingestion_job(job_id)
        if job is None:
            return
        db.update_ingestion_job(job_id, status="processing", processed_pages=0, warnings=[])

        def report(processed_pages, _total_pages, current_warnings):
            warnings[:] = current_warnings
            db.update_ingestion_job(
                job_id,
                processed_pages=processed_pages,
                warnings=warnings,
            )

        ingest_document(
            pdf_path,
            document_id=job["document_id"],
            progress_callback=report,
        )
        status = "ready_with_warnings" if warnings else "ready"
        db.update_ingestion_job(
            job_id,
            status=status,
            processed_pages=job["total_pages"],
            warnings=warnings,
        )
    except Exception as exc:
        db.update_ingestion_job(job_id, status="failed", warnings=warnings, error=str(exc))
    finally:
        with _submitted_lock:
            _submitted.discard(job_id)


def resume_pending_jobs():
    for job_id, pdf_path in db.list_recoverable_ingestion_jobs():
        if os.path.isfile(pdf_path):
            db.update_ingestion_job(job_id, status="queued")
            submit_job(job_id, pdf_path)
        else:
            db.update_ingestion_job(
                job_id,
                status="failed",
                error="Source PDF no longer exists",
            )


def document_readiness(document_id):
    document = db.get_document(document_id)
    if document is None:
        return None
    if document["validated"]:
        latest = db.get_latest_ingestion_job(document_id)
        warnings = latest["warnings"] if latest and latest["status"] in READY_STATUSES else []
        status = "ready_with_warnings" if warnings else "ready"
        return _public_result(
            document_id,
            status,
            document["total_pages"],
            warnings=warnings,
        )
    latest = db.get_latest_ingestion_job(document_id)
    if latest:
        return latest
    return _public_result(document_id, "not_started", document["total_pages"])
