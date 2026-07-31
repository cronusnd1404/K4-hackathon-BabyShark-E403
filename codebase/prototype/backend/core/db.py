"""SQLite schema + CRUD for the slide tutor prototype.

Opens a fresh connection per call instead of pooling — simplest thing
that works for a single-user Streamlit demo, and avoids any
cross-thread sqlite3 connection-sharing issues.
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "store.db")

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

CREATE TABLE IF NOT EXISTS quizzes (
    quiz_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_request TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    created_at TEXT
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


def create_quiz(quiz_id, document_id, session_id, user_request, questions_json):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO quizzes (quiz_id, document_id, session_id, user_request, questions_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (quiz_id, document_id, session_id, user_request, questions_json, _now()),
    )
    conn.commit()
    conn.close()
