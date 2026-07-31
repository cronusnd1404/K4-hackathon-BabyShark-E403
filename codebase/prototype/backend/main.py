import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core import db
from core.deep_explain import explain_highlight, explain_node, generate_exercise
from core.ingest import ingest_document
from core.tree_summary import find_node, get_or_create_tree

RAW_PDF_DIR = os.path.join(os.path.dirname(__file__), "data", "raw_pdfs")

app = FastAPI()
db.init_db()

# Demo-only: the frontend (Vite dev server, a different port) needs to call this
# API from the browser, which the browser blocks by default without CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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


class SessionRequest(BaseModel):
    role: str
    goal: str
    level_ai_agent: str
    level_product_ai: str
    level_llm: str
    level_transformer: str
    level_ai_production: str
    level_production_eval: str


@app.post("/session")
def create_session(payload: SessionRequest):
    background = BACKGROUND_TEMPLATE.format(**payload.model_dump())
    session_id = db.create_session(background)
    return {"session_id": session_id}


# --- Ingest ------------------------------------------------------------------

class IngestRequest(BaseModel):
    pdf_filename: str


@app.post("/ingest")
def ingest(payload: IngestRequest):
    pdf_path = os.path.join(RAW_PDF_DIR, payload.pdf_filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")
    document_id, validated = ingest_document(pdf_path)
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
def get_summary(document_id: str):
    tree = get_or_create_tree(document_id)
    return {"tree": tree}


# --- Explain (node or highlight) --------------------------------------------

class ExplainRequest(BaseModel):
    document_id: str
    session_id: str
    mode: str
    node_id: Optional[str] = None
    page_number: Optional[int] = None
    selected_text: Optional[str] = None
    user_question: Optional[str] = None


@app.post("/explain")
def explain(payload: ExplainRequest):
    background = db.get_session_background(payload.session_id)
    if background is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

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
    else:
        raise HTTPException(status_code=400, detail="mode must be 'node' or 'highlight'")

    return {"explanation": explanation, "related_pages": related_pages}


# --- Exercises ---------------------------------------------------------------

class ExerciseRequest(BaseModel):
    document_id: str
    session_id: str
    page_number: int
    user_request: str


@app.post("/exercise")
def create_exercise_endpoint(payload: ExerciseRequest):
    background = db.get_session_background(payload.session_id)
    if background is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    exercise_id, exercise_text = generate_exercise(
        payload.document_id, payload.page_number, payload.session_id, payload.user_request, background
    )
    return {"exercise_id": exercise_id, "exercise_text": exercise_text}


@app.get("/exercises/{document_id}/{page_number}")
def list_exercises_endpoint(document_id: str, page_number: int, session_id: str):
    rows = db.list_exercises(document_id, page_number, session_id)
    return [
        {"exercise_id": r[0], "user_request": r[1], "exercise_text": r[2], "created_at": r[3]}
        for r in rows
    ]
