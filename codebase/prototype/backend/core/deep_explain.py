"""Prompt builders for deep explanations (mindmap node or highlighted text) and
per-slide practical exercises. These are now independent LLM calls (previously
one combined explanation+exercise prompt in the Streamlit version) -- product
decision: exercises are free-text-request-driven and persisted per-request,
not cached like node/highlight explanations.
"""

import hashlib
import json
import re
import uuid

from core import db
from core.guardrails import (
    MAX_SELECTED_TEXT_CHARS,
    MAX_USER_TEXT_CHARS,
    clean_text,
    filter_related_pages,
    refusal_for_highlight,
    refusal_for_user_text,
    remove_invalid_citations,
    valid_page_numbers,
)
from core.prompts import exercise_prompt, explain_prompt, tutor_system_prompt
from core.tutor_agent import run_tutor_agent


def _system_prompt(background):
    return tutor_system_prompt(background)


def _format_page_index(page_index):
    return "\n".join(f"- Page {p['page_number']}: {p['title']}" for p in page_index)


def build_explain_prompt(background, target_content, page_index, user_question=None):
    """Explanation only -- no exercise. Returns (system_prompt, user_prompt)."""
    return _system_prompt(background), explain_prompt(target_content, page_index, user_question)


def build_exercise_prompt(background, slide_content, user_request):
    """Exercise only -- no explanation. Returns (system_prompt, user_prompt)."""
    return _system_prompt(background), exercise_prompt(slide_content, user_request, "current")


def _parse_explanation_and_related(raw_text):
    marker = "## Related Pages"
    idx = raw_text.find(marker)
    if idx == -1:
        return raw_text.strip(), []
    explanation = raw_text[:idx].strip()
    related_block = raw_text[idx + len(marker):].strip()
    related_pages = []
    for line in related_block.splitlines():
        line = line.strip().lstrip("-").strip()
        if not line:
            continue
        page_part, _, reason = line.partition(":")
        reason = reason.strip()
        # A line can legitimately name more than one page (e.g. "Page 23, 25: ...");
        # extract each number separately rather than joining all digits into one
        # (which previously corrupted "23, 25" into the single bogus page 2325).
        for num in re.findall(r"\d+", page_part):
            related_pages.append({"page_number": int(num), "reason": reason})
    return explanation, related_pages


def build_page_index(document_id):
    """Compact (page_number, short title) index of every page -- lets the model
    name cross-page references. No per-page title exists anywhere in the schema,
    so the short title is always a ~10-word truncation of content_text."""
    pages = db.get_pages(document_id)
    index = []
    for page_number, content_text in pages:
        words = content_text.split()
        short = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
        index.append({"page_number": page_number, "title": short})
    return index


def _collect_descendant_page_refs(node):
    refs = list(node.get("page_refs", []))
    for child in node.get("children") or []:
        refs.extend(_collect_descendant_page_refs(child))
    seen = set()
    ordered = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def explain_node(document_id, node, session_id, background, user_question=None):
    """A parent node's page_refs are the union of all its descendant leaves'
    page_refs, so the resulting explanation synthesizes across the whole branch
    rather than just describing that it has children."""
    question = clean_text(
        user_question,
        max_chars=MAX_USER_TEXT_CHARS,
        field_name="user_question",
        allow_empty=True,
    )
    refusal = refusal_for_user_text(question)
    if refusal:
        return refusal, []
    question_hash = hashlib.sha256((question or "").encode("utf-8")).hexdigest()[:10]
    cache_node_id = f"{node['id']}:{question_hash}"
    cached = db.get_explanation(document_id, cache_node_id, session_id)
    if cached:
        explanation, related_json = cached
        return explanation, json.loads(related_json) if related_json else []

    page_refs = _collect_descendant_page_refs(node)
    pages = db.get_pages(document_id)
    all_pages = dict(pages)
    target_content = "\n\n".join(f"--- Page {p} ---\n{all_pages.get(p, '')}" for p in page_refs)
    page_index = build_page_index(document_id)

    system, user = build_explain_prompt(background, target_content, page_index, question)
    raw = run_tutor_agent(document_id, system, user, max_tokens=2048)
    explanation, related_pages = _parse_explanation_and_related(raw)
    allowed_pages = valid_page_numbers(pages)
    explanation = remove_invalid_citations(explanation, allowed_pages)
    related_pages = filter_related_pages(related_pages, allowed_pages, page_refs)
    db.save_explanation(
        document_id,
        cache_node_id,
        session_id,
        explanation,
        json.dumps(related_pages),
    )
    return explanation, related_pages


def explain_highlight(document_id, page_number, selected_text, session_id, background, user_question=None):
    selected_text = clean_text(
        selected_text,
        max_chars=MAX_SELECTED_TEXT_CHARS,
        field_name="selected_text",
    )
    question = clean_text(
        user_question,
        max_chars=MAX_USER_TEXT_CHARS,
        field_name="user_question",
        allow_empty=True,
    )
    pages = db.get_pages(document_id)
    all_pages = dict(pages)
    if page_number not in all_pages:
        raise ValueError("Page does not exist in current document")
    page_content = all_pages[page_number]
    refusal = refusal_for_highlight(selected_text, page_content, question)
    if refusal:
        return refusal, []
    cache_material = f"{selected_text}\n{question or ''}"
    text_hash = hashlib.sha256(cache_material.encode("utf-8")).hexdigest()[:16]
    cached = db.get_highlight_explanation(document_id, page_number, text_hash, session_id)
    if cached:
        explanation, related_json = cached
        return explanation, json.loads(related_json) if related_json else []

    target_content = f'Highlighted text: "{selected_text}"\n\nFull page {page_number} content for context:\n{page_content}'
    page_index = build_page_index(document_id)

    system, user = build_explain_prompt(background, target_content, page_index, question)
    raw = run_tutor_agent(document_id, system, user, max_tokens=2048)
    explanation, related_pages = _parse_explanation_and_related(raw)
    allowed_pages = valid_page_numbers(pages)
    explanation = remove_invalid_citations(explanation, allowed_pages)
    related_pages = filter_related_pages(related_pages, allowed_pages, [page_number])
    db.save_highlight_explanation(
        document_id, page_number, text_hash, session_id, selected_text, explanation, json.dumps(related_pages)
    )
    return explanation, related_pages


def generate_exercise(document_id, page_number, session_id, user_request, background):
    """Always generates fresh -- no cache check, since user_request is free-form."""
    request = clean_text(
        user_request,
        max_chars=MAX_USER_TEXT_CHARS,
        field_name="user_request",
    )
    pages = db.get_pages(document_id)
    all_pages = dict(pages)
    if page_number not in all_pages:
        raise ValueError("Page does not exist in current document")
    slide_content = all_pages[page_number]
    refusal = refusal_for_user_text(request)
    if refusal:
        exercise_text = refusal
    else:
        system = _system_prompt(background)
        user = exercise_prompt(slide_content, request, page_number)
        exercise_text = run_tutor_agent(document_id, system, user, max_tokens=1024)
        exercise_text = remove_invalid_citations(exercise_text, valid_page_numbers(pages))
    exercise_id = str(uuid.uuid4())
    db.create_exercise(exercise_id, document_id, page_number, session_id, request, exercise_text)
    return exercise_id, exercise_text
