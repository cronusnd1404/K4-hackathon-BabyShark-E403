"""SQLite schema + CRUD for the slide tutor prototype.

Opens a fresh connection per call instead of pooling — simplest thing
that works for a single-user Streamlit demo, and avoids any
cross-thread sqlite3 connection-sharing issues.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "VLEARN_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "store.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    source_pdf_path TEXT NOT NULL,
    total_pages_pdf INTEGER,
    total_pages_ingested INTEGER DEFAULT 0,
    validated BOOLEAN DEFAULT 0,
    ingested_at TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    document_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    content_text TEXT NOT NULL,
    PRIMARY KEY (document_id, page_number)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    background TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS summary_trees (
    document_id TEXT PRIMARY KEY,
    tree_json TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS node_explanations (
    document_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    explanation_text TEXT NOT NULL,
    exercise_text TEXT NOT NULL,
    created_at TEXT,
    PRIMARY KEY (document_id, node_id, session_id)
);

CREATE TABLE IF NOT EXISTS api_calls_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    called_at TEXT
);

CREATE TABLE IF NOT EXISTS highlight_explanations (
    document_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    selected_text_hash TEXT NOT NULL,
    session_id TEXT NOT NULL,
    selected_text TEXT NOT NULL,
    explanation_text TEXT NOT NULL,
    related_pages_json TEXT NOT NULL,
    created_at TEXT,
    PRIMARY KEY (document_id, page_number, selected_text_hash, session_id)
);

CREATE TABLE IF NOT EXISTS exercises (
    exercise_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    user_request TEXT NOT NULL,
    exercise_text TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    status TEXT NOT NULL,
    processed_pages INTEGER DEFAULT 0,
    total_pages INTEGER NOT NULL,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def upsert_document(document_id, pdf_path, total_pages):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO documents (document_id, source_pdf_path, total_pages_pdf, ingested_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            source_pdf_path = excluded.source_pdf_path,
            total_pages_pdf = excluded.total_pages_pdf
        """,
        (document_id, pdf_path, total_pages, _now()),
    )
    conn.commit()
    conn.close()


def get_document(document_id):
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT document_id, source_pdf_path, total_pages_pdf,
               total_pages_ingested, validated
        FROM documents WHERE document_id = ?
        """,
        (document_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "document_id": row[0],
        "source_pdf_path": row[1],
        "total_pages": row[2] or 0,
        "ingested_pages": row[3] or 0,
        "validated": bool(row[4]),
    }


def upsert_page(document_id, page_number, content_text):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO pages (document_id, page_number, content_text)
        VALUES (?, ?, ?)
        ON CONFLICT(document_id, page_number) DO UPDATE SET
            content_text = excluded.content_text
        """,
        (document_id, page_number, content_text),
    )
    conn.commit()
    conn.close()


def count_pages(document_id):
    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM pages WHERE document_id = ?", (document_id,))
    n = cur.fetchone()[0]
    conn.close()
    return n


def set_validated(document_id, validated):
    conn = get_conn()
    conn.execute(
        "UPDATE documents SET validated = ?, total_pages_ingested = ? WHERE document_id = ?",
        (1 if validated else 0, count_pages(document_id), document_id),
    )
    conn.commit()
    conn.close()


def reset_document_validation(document_id):
    conn = get_conn()
    conn.execute(
        "UPDATE documents SET validated = 0, total_pages_ingested = ? WHERE document_id = ?",
        (count_pages(document_id), document_id),
    )
    conn.commit()
    conn.close()


def remove_pages_after(document_id, total_pages):
    conn = get_conn()
    conn.execute(
        "DELETE FROM pages WHERE document_id = ? AND page_number > ?",
        (document_id, total_pages),
    )
    conn.commit()
    conn.close()


def get_source_pdf_path(document_id):
    conn = get_conn()
    cur = conn.execute("SELECT source_pdf_path FROM documents WHERE document_id = ?", (document_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def is_ingested(document_id):
    conn = get_conn()
    cur = conn.execute("SELECT validated FROM documents WHERE document_id = ?", (document_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0])


def get_pages(document_id):
    conn = get_conn()
    cur = conn.execute(
        "SELECT page_number, content_text FROM pages WHERE document_id = ? ORDER BY page_number",
        (document_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def create_ingestion_job(document_id, total_pages):
    job_id = str(uuid.uuid4())
    now = _now()
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO ingestion_jobs
            (job_id, document_id, status, processed_pages, total_pages,
             warnings_json, error, created_at, updated_at)
        VALUES (?, ?, 'queued', 0, ?, '[]', NULL, ?, ?)
        """,
        (job_id, document_id, total_pages, now, now),
    )
    conn.commit()
    conn.close()
    return job_id


def update_ingestion_job(
    job_id,
    *,
    status=None,
    processed_pages=None,
    warnings=None,
    error=None,
):
    updates = ["updated_at = ?"]
    values = [_now()]
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if processed_pages is not None:
        updates.append("processed_pages = ?")
        values.append(processed_pages)
    if warnings is not None:
        updates.append("warnings_json = ?")
        values.append(json.dumps(warnings, ensure_ascii=False))
    if error is not None:
        updates.append("error = ?")
        values.append(error)
    values.append(job_id)
    conn = get_conn()
    conn.execute(
        f"UPDATE ingestion_jobs SET {', '.join(updates)} WHERE job_id = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_ingestion_job(job_id):
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT job_id, document_id, status, processed_pages, total_pages,
               warnings_json, error, created_at, updated_at
        FROM ingestion_jobs WHERE job_id = ?
        """,
        (job_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "job_id": row[0],
        "document_id": row[1],
        "status": row[2],
        "processed_pages": row[3],
        "total_pages": row[4],
        "warnings": json.loads(row[5] or "[]"),
        "error": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }


def get_latest_ingestion_job(document_id):
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT job_id FROM ingestion_jobs
        WHERE document_id = ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (document_id,),
    )
    row = cur.fetchone()
    conn.close()
    return get_ingestion_job(row[0]) if row else None


def list_recoverable_ingestion_jobs():
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT j.job_id, d.source_pdf_path
        FROM ingestion_jobs AS j
        JOIN documents AS d ON d.document_id = j.document_id
        WHERE j.status IN ('queued', 'processing')
        ORDER BY j.created_at
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def create_session(background):
    session_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (session_id, background, created_at) VALUES (?, ?, ?)",
        (session_id, background, _now()),
    )
    conn.commit()
    conn.close()
    return session_id


def get_session_background(session_id):
    conn = get_conn()
    cur = conn.execute("SELECT background FROM sessions WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_first_document_id():
    """document_id of the oldest cached summary tree -- used by the tree-export tool."""
    conn = get_conn()
    cur = conn.execute("SELECT document_id FROM summary_trees ORDER BY created_at LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_tree(document_id):
    conn = get_conn()
    cur = conn.execute("SELECT tree_json FROM summary_trees WHERE document_id = ?", (document_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def save_tree(document_id, tree_json):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO summary_trees (document_id, tree_json, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            tree_json = excluded.tree_json,
            created_at = excluded.created_at
        """,
        (document_id, tree_json, _now()),
    )
    conn.commit()
    conn.close()


def get_explanation(document_id, node_id, session_id):
    # NOTE: the "exercise_text" column is repurposed to hold related_pages_json for
    # node explanations (see PHASE2_NOTES.md) -- exercises are no longer tied to this
    # table at all, and the schema/column can't change (existing table), so the
    # already-unused-for-its-original-purpose column is reused instead of adding one.
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT explanation_text, exercise_text FROM node_explanations
        WHERE document_id = ? AND node_id = ? AND session_id = ?
        """,
        (document_id, node_id, session_id),
    )
    row = cur.fetchone()
    conn.close()
    return row


def save_explanation(document_id, node_id, session_id, explanation_text, exercise_text):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO node_explanations
            (document_id, node_id, session_id, explanation_text, exercise_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id, node_id, session_id) DO UPDATE SET
            explanation_text = excluded.explanation_text,
            exercise_text = excluded.exercise_text
        """,
        (document_id, node_id, session_id, explanation_text, exercise_text, _now()),
    )
    conn.commit()
    conn.close()


def log_api_call(model, input_tokens, output_tokens):
    conn = get_conn()
    conn.execute(
        "INSERT INTO api_calls_log (model, input_tokens, output_tokens, called_at) VALUES (?, ?, ?, ?)",
        (model, input_tokens, output_tokens, _now()),
    )
    conn.commit()
    conn.close()


def get_usage_totals():
    """All-time totals across process restarts -- lets the sidebar show spend even after a fresh session_state."""
    conn = get_conn()
    cur = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0) FROM api_calls_log"
    )
    calls, input_tokens, output_tokens = cur.fetchone()
    conn.close()
    return {"calls": calls, "input_tokens": input_tokens, "output_tokens": output_tokens}


def get_highlight_explanation(document_id, page_number, selected_text_hash, session_id):
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT explanation_text, related_pages_json FROM highlight_explanations
        WHERE document_id = ? AND page_number = ? AND selected_text_hash = ? AND session_id = ?
        """,
        (document_id, page_number, selected_text_hash, session_id),
    )
    row = cur.fetchone()
    conn.close()
    return row


def save_highlight_explanation(
    document_id, page_number, selected_text_hash, session_id, selected_text, explanation_text, related_pages_json
):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO highlight_explanations
            (document_id, page_number, selected_text_hash, session_id, selected_text,
             explanation_text, related_pages_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id, page_number, selected_text_hash, session_id) DO UPDATE SET
            explanation_text = excluded.explanation_text,
            related_pages_json = excluded.related_pages_json
        """,
        (document_id, page_number, selected_text_hash, session_id, selected_text,
         explanation_text, related_pages_json, _now()),
    )
    conn.commit()
    conn.close()


def create_exercise(exercise_id, document_id, page_number, session_id, user_request, exercise_text):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO exercises
            (exercise_id, document_id, page_number, session_id, user_request, exercise_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (exercise_id, document_id, page_number, session_id, user_request, exercise_text, _now()),
    )
    conn.commit()
    conn.close()


def list_exercises(document_id, page_number, session_id):
    conn = get_conn()
    cur = conn.execute(
        """
        SELECT exercise_id, user_request, exercise_text, created_at FROM exercises
        WHERE document_id = ? AND page_number = ? AND session_id = ?
        ORDER BY created_at
        """,
        (document_id, page_number, session_id),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
