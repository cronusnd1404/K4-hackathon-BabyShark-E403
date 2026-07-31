import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from core import db
from core.deep_explain import explain_highlight, explain_node, generate_exercise
from core.guardrails import MAX_SELECTED_TEXT_CHARS, MAX_USER_TEXT_CHARS, refusal_for_user_text
from core.ingest import inspect_pdf, make_document_id
from core.ingestion_jobs import (
    READY_STATUSES,
    document_readiness,
    queue_document,
    resume_pending_jobs,
)
from core.onboarding import PROFILE_OPTIONS
from core.tree_summary import find_node, get_or_create_tree

RAW_PDF_DIR = Path(__file__).resolve().parent / "data" / "raw_pdfs"
COURSE_SLIDE_DIR = Path(__file__).resolve().parents[3] / "data" / "vlearn-pack" / "slides"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

db.init_db()


@asynccontextmanager
async def lifespan(_app):
    resume_pending_jobs()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def read_root():
    return {"status": "ok"}


# --- Session (onboarding survey -> background string) ----------------------

BACKGROUND_TEMPLATE = """Vai trò: {role}.
Mục tiêu học: {goal}.
Mức độ hiểu biết theo chủ đề:
- AI Agent: {level_ai_agent}.
- Product AI: {level_product_ai}.
- LLM: {level_llm}.
- Transformer: {level_transformer}.
- AI Production: {level_ai_production}.
- Production Evaluation: {level_production_eval}."""


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionRequest(StrictRequest):
    role: str = Field(min_length=1, max_length=300)
    goal: str = Field(min_length=1, max_length=300)
    level_ai_agent: str = Field(min_length=1, max_length=500)
    level_product_ai: str = Field(min_length=1, max_length=500)
    level_llm: str = Field(min_length=1, max_length=500)
    level_transformer: str = Field(min_length=1, max_length=500)
    level_ai_production: str = Field(min_length=1, max_length=500)
    level_production_eval: str = Field(min_length=1, max_length=500)

    @field_validator("*")
    @classmethod
    def reject_profile_injection(cls, value, info: ValidationInfo):
        if refusal_for_user_text(value):
            raise ValueError("profile answer contains disallowed instructions or sensitive-data requests")
        if value not in PROFILE_OPTIONS[info.field_name]:
            raise ValueError("profile answer is not one of the allowed survey options")
        return value


@app.post("/session")
def create_session(payload: SessionRequest):
    background = BACKGROUND_TEMPLATE.format(**payload.model_dump())
    session_id = db.create_session(background)
    return {"session_id": session_id}


# --- Ingest ------------------------------------------------------------------

class IngestRequest(StrictRequest):
    pdf_filename: str = Field(min_length=5, max_length=255, pattern=r"^[^/\\]+\.pdf$")


@app.post("/ingest")
def ingest(payload: IngestRequest):
    pdf_path = _find_pdf_by_filename(payload.pdf_filename)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail="PDF not found in repository document folders")
    try:
        return queue_document(str(pdf_path))
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/documents")
def list_documents():
    documents = []
    seen = set()
    pdf_paths = [
        pdf_path
        for source_dir in _pdf_source_dirs()
        if source_dir.is_dir()
        for pdf_path in source_dir.glob("*.pdf")
    ]
    for pdf_path in sorted(pdf_paths, key=lambda path: path.name.casefold()):
        document_id = make_document_id(str(pdf_path))
        if document_id in seen:
            continue
        seen.add(document_id)
        readiness = document_readiness(document_id)
        documents.append(
            {
                "document_id": document_id,
                "pdf_filename": pdf_path.name,
                "title": pdf_path.stem,
                "source": pdf_path.parent.name,
                "status": readiness["status"] if readiness else "not_started",
                "total_pages": readiness["total_pages"] if readiness else None,
            }
        )
    return documents


@app.get("/ingest/status/{job_id}")
def get_ingest_status(job_id: str):
    job = db.get_ingestion_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown ingestion job")
    return job


# --- Raw PDF (for the frontend viewer) ---------------------------------------

@app.get("/pdf/{document_id}")
def get_pdf(document_id: str):
    pdf_path = db.get_source_pdf_path(document_id)
    resolved = _allowed_pdf_path(pdf_path)
    if resolved is None:
        resolved = _find_pdf_by_document_id(document_id)
        if resolved is not None:
            try:
                db.upsert_document(document_id, str(resolved), inspect_pdf(str(resolved)))
            except (RuntimeError, ValueError):
                resolved = None
    if resolved is None:
        raise HTTPException(status_code=404, detail="PDF not found for this document_id")
    return FileResponse(
        resolved,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{resolved.name}"'},
    )


def _allowed_pdf_path(pdf_path):
    if not pdf_path:
        return None
    try:
        resolved = Path(pdf_path).resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if resolved.suffix.casefold() != ".pdf" or not resolved.is_file():
        return None
    return resolved if any(resolved.is_relative_to(root.resolve()) for root in _pdf_source_dirs()) else None


def _pdf_source_dirs():
    return (RAW_PDF_DIR, COURSE_SLIDE_DIR)


def _find_pdf_by_filename(pdf_filename):
    for source_dir in _pdf_source_dirs():
        candidate = (source_dir / pdf_filename).resolve()
        if candidate.parent == source_dir.resolve() and candidate.is_file():
            return candidate
    return None


def _find_pdf_by_document_id(document_id):
    for source_dir in _pdf_source_dirs():
        if not source_dir.is_dir():
            continue
        for candidate in source_dir.glob("*.pdf"):
            if make_document_id(str(candidate)) == document_id:
                return candidate.resolve()
    return None


def _require_ready(document_id):
    readiness = document_readiness(document_id)
    if readiness is None:
        raise HTTPException(status_code=404, detail="Unknown document_id")
    if readiness["status"] not in READY_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Document ingestion is not ready",
                "ingestion": readiness,
            },
        )
    return readiness


# --- Summary tree --------------------------------------------------------------

@app.get("/summary/{document_id}")
def get_summary(document_id: str):
    _require_ready(document_id)
    try:
        tree = get_or_create_tree(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"tree": tree}


# --- Explain (node or highlight) --------------------------------------------

class ExplainRequest(StrictRequest):
    document_id: str = Field(min_length=1, max_length=255)
    session_id: str = Field(min_length=1, max_length=64)
    mode: Literal["node", "highlight"]
    node_id: Optional[str] = Field(default=None, max_length=255)
    page_number: Optional[int] = Field(default=None, ge=1)
    selected_text: Optional[str] = Field(default=None, max_length=MAX_SELECTED_TEXT_CHARS)
    user_question: Optional[str] = Field(default=None, max_length=MAX_USER_TEXT_CHARS)


@app.post("/explain")
def explain(payload: ExplainRequest):
    background = db.get_session_background(payload.session_id)
    if background is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    _require_ready(payload.document_id)

    try:
        if payload.mode == "node":
            if not payload.node_id:
                raise HTTPException(status_code=400, detail="node_id required for mode=node")
            tree = get_or_create_tree(payload.document_id)
            node = find_node(tree, payload.node_id)
            if node is None:
                raise HTTPException(status_code=404, detail="node_id not found in tree")
            explanation, related_pages = explain_node(
                payload.document_id, node, payload.session_id, background, payload.user_question
            )
        else:
            if payload.page_number is None or not payload.selected_text:
                raise HTTPException(
                    status_code=400, detail="page_number and selected_text required for mode=highlight"
                )
            explanation, related_pages = explain_highlight(
                payload.document_id,
                payload.page_number,
                payload.selected_text,
                payload.session_id,
                background,
                payload.user_question,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"explanation": explanation, "related_pages": related_pages}


# --- Exercises ---------------------------------------------------------------

class ExerciseRequest(StrictRequest):
    document_id: str = Field(min_length=1, max_length=255)
    session_id: str = Field(min_length=1, max_length=64)
    page_number: int = Field(ge=1)
    user_request: str = Field(min_length=1, max_length=MAX_USER_TEXT_CHARS)


@app.post("/exercise")
def create_exercise_endpoint(payload: ExerciseRequest):
    background = db.get_session_background(payload.session_id)
    if background is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    _require_ready(payload.document_id)
    try:
        exercise_id, exercise_text = generate_exercise(
            payload.document_id,
            payload.page_number,
            payload.session_id,
            payload.user_request,
            background,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"exercise_id": exercise_id, "exercise_text": exercise_text}


@app.get("/exercises/{document_id}/{page_number}")
def list_exercises_endpoint(document_id: str, page_number: int, session_id: str):
    _require_ready(document_id)
    rows = db.list_exercises(document_id, page_number, session_id)
    return [
        {"exercise_id": r[0], "user_request": r[1], "exercise_text": r[2], "created_at": r[3]}
        for r in rows
    ]
