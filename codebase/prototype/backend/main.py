import os
from pathlib import Path
from typing import Literal
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core import db
from core.deep_explain import explain_highlight, explain_node, explain_question, generate_quiz
from core.guardrails import MAX_SELECTED_TEXT_CHARS, MAX_USER_TEXT_CHARS, refusal_for_user_text
from core.ingest import ingest_document
from core.tree_summary import find_node, get_or_create_tree

RAW_PDF_DIR = Path(__file__).resolve().parent / "data" / "raw_pdfs"
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app = FastAPI()
db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/healthz")
def read_root():
    # Not "/" -- that path must fall through to the StaticFiles mount at the
    # bottom of this file so it serves the built frontend's index.html.
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
    def reject_profile_injection(cls, value):
        if refusal_for_user_text(value):
            raise ValueError("profile answer contains disallowed instructions or sensitive-data requests")
        return value


@app.post("/session")
def create_session(payload: SessionRequest):
    background = BACKGROUND_TEMPLATE.format(**payload.model_dump())
    session_id = db.create_session(background)
    return {"session_id": session_id}


# --- PDF list (for the sidebar) -----------------------------------------------

@app.get("/pdfs")
def list_pdfs():
    filenames = sorted(f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith(".pdf"))
    return [{"filename": f, "label": os.path.splitext(f)[0]} for f in filenames]


# --- Ingest ------------------------------------------------------------------

class IngestRequest(StrictRequest):
    pdf_filename: str = Field(min_length=5, max_length=255, pattern=r"^[^/\\]+\.pdf$")


@app.post("/ingest")
def ingest(payload: IngestRequest):
    pdf_path = (RAW_PDF_DIR / payload.pdf_filename).resolve()
    if pdf_path.parent != RAW_PDF_DIR.resolve():
        raise HTTPException(status_code=400, detail="pdf_filename must be a file in raw_pdfs")
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")
    document_id, validated = ingest_document(str(pdf_path))
    total_pages = db.count_pages(document_id)
    return {"document_id": document_id, "total_pages": total_pages, "validated": validated}


# --- Raw PDF (for the frontend viewer) ---------------------------------------

@app.get("/pdf/{document_id}")
def get_pdf(document_id: str):
    pdf_path = db.get_source_pdf_path(document_id)
    if pdf_path is None or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found for this document_id")
    return FileResponse(pdf_path, media_type="application/pdf")


# --- Summary tree --------------------------------------------------------------

@app.get("/summary/{document_id}")
def get_summary(document_id: str, refresh: bool = False):
    if not db.get_pages(document_id):
        raise HTTPException(status_code=404, detail="Unknown document_id")
    try:
        tree = get_or_create_tree(document_id, force_refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"tree": tree}


# --- Explain (node, highlight, or question) --------------------------------------------

class ExplainRequest(StrictRequest):
    document_id: str = Field(min_length=1, max_length=255)
    session_id: str = Field(min_length=1, max_length=64)
    mode: Literal["node", "highlight", "question"]
    node_id: Optional[str] = Field(default=None, max_length=255)
    page_number: Optional[int] = Field(default=None, ge=1)
    selected_text: Optional[str] = Field(default=None, max_length=MAX_SELECTED_TEXT_CHARS)
    user_question: Optional[str] = Field(default=None, max_length=MAX_USER_TEXT_CHARS)
    chat_history: Optional[list[dict]] = None


@app.post("/explain")
def explain(payload: ExplainRequest):
    background = db.get_session_background(payload.session_id)
    if background is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    if not db.get_pages(payload.document_id):
        raise HTTPException(status_code=404, detail="Unknown document_id")

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
        elif payload.mode == "highlight":
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
        elif payload.mode == "question":
            if payload.page_number is None or not payload.user_question:
                raise HTTPException(
                    status_code=400, detail="page_number and user_question required for mode=question"
                )
            explanation, related_pages = explain_question(
                payload.document_id, payload.page_number, background, payload.user_question, payload.chat_history
            )
        else:
            raise HTTPException(status_code=400, detail="mode must be 'node', 'highlight', or 'question'")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"explanation": explanation, "related_pages": related_pages}


# --- Quiz (whole-document multiple choice) ------------------------------------

class QuizRequest(StrictRequest):
    document_id: str = Field(min_length=1, max_length=255)
    session_id: str = Field(min_length=1, max_length=64)
    user_request: str = Field(default="", max_length=MAX_USER_TEXT_CHARS)
    num_questions: int = Field(default=5, ge=1, le=20)


@app.post("/quiz")
def create_quiz_endpoint(payload: QuizRequest):
    background = db.get_session_background(payload.session_id)
    if background is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    if not db.get_pages(payload.document_id):
        raise HTTPException(status_code=404, detail="Unknown document_id")
    try:
        quiz_id, questions = generate_quiz(
            payload.document_id, payload.session_id, payload.user_request, background, payload.num_questions
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"quiz_id": quiz_id, "questions": questions}


# --- Frontend (production build only) -----------------------------------------
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

