"""Prompt builders for deep explanations (mindmap node or highlighted text) and
whole-document multiple-choice quizzes. These are independent LLM calls
(previously one combined explanation+exercise prompt in the Streamlit version)
-- product decision: quizzes are free-text-request-driven and persisted
per-request, not cached like node/highlight explanations.
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
from core.llm_client import call_chat, call_llm

JARGON_INSTRUCTION = (
    "Any term or concept that would likely be unfamiliar given the learner's "
    "stated background must be annotated inline the moment it is used (e.g. a "
    "short inline gloss in parentheses) -- do not assume familiarity beyond what "
    "their background indicates. This applies uniformly, not just to hard concepts."
)

from core.prompts import exercise_prompt, explain_prompt, tutor_system_prompt
from core.tutor_agent import run_tutor_agent

# The app is Vietnamese-audience throughout (onboarding, UI copy, background
# template), but the lecture PDFs mix in a lot of English technical
# vocabulary -- without this, the model tends to drift into English on
# outputs like mindmap node titles that have little other language signal to
# anchor on. Proper nouns/terms (Transformer, overfitting, ...) staying in
# English is fine and expected; the surrounding prose must not.
LANGUAGE_INSTRUCTION = (
    "Respond in Vietnamese (tiếng Việt), regardless of what language the source "
    "material or the learner's own question is written in. Keep established "
    "English technical terms/proper nouns as-is (e.g. Transformer, overfitting) "
    "rather than forcing an awkward translation, but all surrounding prose -- "
    "explanations, titles, summaries -- must be in Vietnamese."
)


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


QUIZ_SYSTEM_TEMPLATE = """You are an AI tutor writing a multiple-choice quiz. The learner's background:
{background}

{language}

You produce ONLY valid JSON, no prose before or after, no markdown code fences."""


def build_quiz_prompt(background, full_content, user_request, num_questions):
    """Whole-document quiz -- returns (system_prompt, user_prompt). Unlike the
    other builders here this deliberately skips _system_prompt/JARGON_INSTRUCTION:
    quiz options must stay short and unambiguous, so inline jargon glosses (which
    make sense inline in an explanation) would just bloat/confuse the options."""
    system = QUIZ_SYSTEM_TEMPLATE.format(background=background, language=LANGUAGE_INSTRUCTION)
    user = f"""The learner asked for practice questions covering this lecture, with this specific focus: "{user_request or 'toàn bộ nội dung bài giảng'}"

Full lecture content (all slides):
{full_content}

Write exactly {num_questions} multiple-choice questions testing understanding of this material, addressing their focus. Spread the questions across DIFFERENT parts/pages of the material rather than clustering on one slide. Each question needs exactly 4 options, exactly one correct. The 3 wrong options must be plausible distractors (common misconceptions or near-misses), not obviously wrong.

Return ONLY a JSON array (no other text) of exactly {num_questions} objects, each shaped exactly like:
{{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0, "explanation": "...", "page_number": 12}}

- "question": in Vietnamese.
- "options": exactly 4 strings, in Vietnamese.
- "correct_index": 0-based index (0-3) of the correct option in "options".
- "explanation": 2-4 sentences in Vietnamese, covering why the correct option is right AND briefly why each wrong option is wrong.
- "page_number": the page this question is drawn from.
"""
    return system, user


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
            # highlight_term is always None here -- the model free-wrote "reason"
            # itself rather than us matching a specific keyword, so there's no
            # single term to point the frontend at for on-page highlighting.
            related_pages.append({"page_number": int(num), "reason": reason, "highlight_term": None})
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


# --- Cheap cross-page search (no LLM call) for the chat/question flow -------
#
# Stuffing every other page's full text into the prompt just in case a
# question mentions a term defined elsewhere would be expensive and mostly
# wasted. Instead: plain-Python keyword search over the already-OCR'd/cached
# page text (core/ingest.py already stored it), returning only a handful of
# short, bolded snippets from the pages that actually matched -- costs zero
# LLM tokens to compute, and only a few hundred tokens to include.

_STOPWORDS = {
    # Vietnamese function words commonly found in questions
    "là", "gì", "có", "không", "được", "này", "đó", "nào", "sao", "thế", "và",
    "của", "cho", "với", "trong", "một", "các", "những", "để", "khi", "như",
    "về", "hãy", "cái", "làm", "sẽ", "đã", "đang", "tôi", "bạn", "mình",
    "chúng", "ta", "nó", "ai", "bao", "nhiêu", "vì", "nên", "nếu", "thì", "mà",
    "rồi", "đây", "kia", "trên", "dưới", "ra", "vào", "lên", "xuống", "sau",
    "trước", "còn", "cũng", "hay", "nữa", "phải", "bị", "vậy", "giải", "thích",
    # Vietnamese meta/connector syllables -- these show up in phrases asking
    # ABOUT the material ("có liên quan gì đến bài giảng không", "nội dung
    # này...") rather than naming a term to look up. Left unfiltered, a lone
    # syllable like "quan" (from "liên quan") matches unrelated words like
    # "quan sát" elsewhere in the doc and drowns out the real keyword.
    "liên", "quan", "nội", "dung", "bài", "giảng", "nhắc", "tới", "đề", "cập",
    # English, in case the question is typed in English
    "the", "is", "a", "an", "of", "to", "in", "on", "for", "and", "or", "what",
    "how", "why", "does", "do", "this", "that", "are", "was", "were", "be",
}


def _extract_keywords(text):
    words = re.findall(r"[^\W\d_]+", text.lower(), flags=re.UNICODE)
    seen = []
    for w in words:
        if len(w) >= 3 and w not in _STOPWORDS and w not in seen:
            seen.append(w)
    return seen


def find_related_snippets(document_id, query, exclude_page, max_pages=3, radius=80):
    """Rank other pages by keyword-hit count, return a short snippet (matched
    term bolded) per top page, plus the matched term itself in its original
    casing -- the frontend uses that to find and highlight the exact spot on
    the page once the learner clicks through, instead of just landing on the
    page and making them hunt for it. Empty list if the query has no real
    keywords or nothing else in the document matches -- callers should treat
    that as "no cross-references available", not an error."""
    keywords = _extract_keywords(query)
    if not keywords:
        return []

    hits = []
    for page_number, content_text in db.get_pages(document_id):
        if page_number == exclude_page:
            continue
        lower_content = content_text.lower()
        count = sum(lower_content.count(k) for k in keywords)
        if count == 0:
            continue
        first_kw = next(k for k in keywords if k in lower_content)
        pos = lower_content.find(first_kw)
        start = max(0, pos - radius)
        end = min(len(content_text), pos + len(first_kw) + radius)
        matched_term = content_text[pos:pos + len(first_kw)]
        snippet = (
            content_text[start:pos] + f"**{matched_term}**" + content_text[pos + len(first_kw):end]
        ).strip()
        hits.append((count, page_number, snippet, matched_term))

    hits.sort(key=lambda h: h[0], reverse=True)
    return [{"page_number": p, "snippet": s, "term": t} for _, p, s, t in hits[:max_pages]]


def _extract_inline_page_citations(raw_text, document_id, snippets=()):
    """Chat/question-mode replies aren't forced into a '## Related Pages'
    section -- instead the model is told to cite [Page X] inline only when
    relevant, and we recover the page chips for the UI from those citations.
    Only pages the model actually cited make it into the result -- a page
    merely being in `snippets` (shown to the model as a candidate) doesn't
    mean it was relevant, and the model was told to ignore irrelevant ones.

    When a cited page matches one of the pre-computed keyword-search
    `snippets` (see find_related_snippets), its exact matched term is carried
    through as `highlight_term` -- the frontend uses that to jump straight to
    and highlight that spot on the page, instead of just landing on the page
    and making the learner hunt for it. Cited pages we have no snippet for
    (the model knew about them some other way) fall back to a generic
    10-word excerpt and no highlight_term."""
    page_numbers = sorted({int(n) for n in re.findall(r"\[Page (\d+)\]", raw_text)})
    if not page_numbers:
        return []
    snippet_by_page = {s["page_number"]: s for s in snippets}
    all_pages = dict(db.get_pages(document_id))
    related = []
    for p in page_numbers:
        snippet = snippet_by_page.get(p)
        if snippet:
            related.append({"page_number": p, "reason": snippet["snippet"], "highlight_term": snippet["term"]})
            continue
        words = all_pages.get(p, "").split()
        short = " ".join(words[:10]) + ("..." if len(words) > 10 else "")
        related.append({"page_number": p, "reason": short, "highlight_term": None})
    return related


RESOURCES_INSTRUCTION = """If the learner asks for further materials to study this topic, or for a learning
roadmap/path to understand it:
- First point to this document's OWN other pages if they already cover the prerequisite or
  next-step content, citing [Page X] -- prefer this over anything external, since it's
  content you can actually verify exists.
- For external resources, name a SPECIFIC well-known book/course/instructor/documentation by
  title (e.g. "Andrew Ng's Machine Learning course on Coursera", "scikit-learn's
  documentation") -- never invent a specific article/page URL or claim a specific chapter
  number, since you cannot reliably know the exact path or contents.
- Any link you give MUST be a stable SEARCH url on a well-known site (never a guessed direct
  content URL, which is exactly the part you cannot know is correct), formatted as a proper
  markdown link with a readable label -- e.g. [Wikipedia: overfitting](https://vi.wikipedia.org/wiki/Special:Search?search=overfitting):
  - https://vi.wikipedia.org/wiki/Special:Search?search=<topic> (or en.wikipedia.org for English)
  - https://www.google.com/search?q=<topic>
  - https://scholar.google.com/scholar?q=<topic>
  - https://www.youtube.com/results?search_query=<topic>"""


CHAT_SYSTEM_TEMPLATE = """You are an AI tutor answering a student's question in a chat. The learner's background:
{background}

Rules for this chat:
- Answer ONLY using the lecture content given to you below (the current page, plus any excerpts from other pages). Do not pull in outside knowledge beyond what's needed to explain a term that already appears in this material -- EXCEPT when the learner explicitly asks for further study materials or a learning roadmap (see below).
- If the question is not related to this lecture's content, reply with exactly one short sentence saying it isn't covered in this material -- do not answer it anyway, and do not apologize at length.
- Be direct and concise: answer exactly what was asked. Do not describe or summarize the whole page unless that IS the question.
- Only cite other pages with [Page X] when the learner is asking about a specific term/concept that appears in the excerpts below. Otherwise, do not mention any page numbers at all.
- Do not use section headers (no "## Explanation", no "## Related Pages") -- answer in plain prose.

{resources}

{language}

{jargon}"""


def build_chat_prompt(background, page_content, page_number, other_snippets, user_question):
    """Free-form chat question -- returns (system_prompt, user_prompt) for the
    CURRENT turn only. Prior turns are passed separately as real conversation
    messages (see explain_question) so they stay cheap and this injection
    doesn't get repeated for every turn."""
    system = CHAT_SYSTEM_TEMPLATE.format(
        background=background,
        jargon=JARGON_INSTRUCTION,
        resources=RESOURCES_INSTRUCTION,
        language=LANGUAGE_INSTRUCTION,
    )

    snippet_block = ""
    if other_snippets:
        lines = "\n\n".join(f"[Page {s['page_number']}]: ...{s['snippet']}..." for s in other_snippets)
        snippet_block = (
            "\n\nPossibly relevant excerpts from OTHER pages "
            f"(only cite these if the question is about a term/concept they define):\n{lines}\n"
        )

    user = f"""Current page {page_number} content:
{page_content}
{snippet_block}
The learner's question: "{user_question}\""""
    return system, user


HIGHLIGHT_QUESTION_SYSTEM_TEMPLATE = """You are an AI tutor. The learner's background:
{background}

The learner highlighted a piece of text while asking a question. Their QUESTION is what you must answer -- treat the highlighted text and the page it's on as supporting context only, not the thing to explain end-to-end.
- Answer directly and concisely.
- You may cite other pages with [Page X] if genuinely relevant to the question.
- Do not use section headers (no "## Explanation", no "## Related Pages") -- plain prose.

{resources}

{language}

{jargon}"""


def build_highlight_question_prompt(
    background, selected_text, page_content, page_number, other_snippets, user_question
):
    """Highlight + question -- the question is primary, the highlight is
    context. Contrast with build_explain_prompt, used when there's no
    question and the highlighted content itself is what's being explained."""
    system = HIGHLIGHT_QUESTION_SYSTEM_TEMPLATE.format(
        background=background,
        jargon=JARGON_INSTRUCTION,
        resources=RESOURCES_INSTRUCTION,
        language=LANGUAGE_INSTRUCTION,
    )

    snippet_block = ""
    if other_snippets:
        lines = "\n\n".join(f"[Page {s['page_number']}]: ...{s['snippet']}..." for s in other_snippets)
        snippet_block = (
            "\n\nPossibly relevant excerpts from OTHER pages "
            f"(only cite these if the question is about a term/concept they define):\n{lines}\n"
        )

    user = f"""The learner's question: "{user_question}"

They highlighted this text on page {page_number} (context only, not necessarily what they're asking about):
"{selected_text}"

Full page {page_number} content (context only):
{page_content}
{snippet_block}"""
    return system, user


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

    if question:
        snippets = find_related_snippets(document_id, question, exclude_page=page_number)
        system, user = build_highlight_question_prompt(
            background, selected_text, page_content, page_number, snippets, question
        )
        raw = call_llm(system, user, max_tokens=1024)
        explanation = raw.strip()
        related_pages = _extract_inline_page_citations(explanation, document_id, snippets)
        return explanation, related_pages

    text_hash = hashlib.sha256(selected_text.encode("utf-8")).hexdigest()[:16]
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


def explain_question(document_id, page_number, background, user_question, chat_history=None):
    """Free-form chat question about the page currently in view -- no
    highlight required. Always fresh, never cached.
    """
    all_pages = dict(db.get_pages(document_id))
    page_content = all_pages.get(page_number, "")
    snippets = find_related_snippets(document_id, user_question, exclude_page=page_number)

    system, user = build_chat_prompt(background, page_content, page_number, snippets, user_question)

    messages = []
    for turn in (chat_history or [])[-3:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})
    messages.append({"role": "user", "content": user})

    raw = call_chat(system, messages, max_tokens=1024)
    explanation = raw.strip()
    related_pages = _extract_inline_page_citations(explanation, document_id, snippets)
    return explanation, related_pages


def _parse_quiz_json(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    questions = json.loads(text[start:end + 1])
    for q in questions:
        if len(q.get("options", [])) != 4 or not isinstance(q.get("correct_index"), int):
            raise ValueError(f"Malformed quiz question from model: {q!r}")
    return questions


def generate_quiz(document_id, session_id, user_request, background, num_questions=5):
    """Whole-document multiple-choice quiz -- always generates fresh (no cache,
    same rationale as the old per-page exercise: the request text is free-form).
    Persisted to the quizzes table for later eval/reference, but nothing reads
    it back today -- grading happens client-side since correct_index +
    explanation are already in the response."""
    pages = db.get_pages(document_id)
    full_content = "\n\n".join(f"--- Page {p} ---\n{c}" for p, c in pages)

    system, user = build_quiz_prompt(background, full_content, user_request, num_questions)
    raw = call_llm(system, user, max_tokens=4096)
    questions = _parse_quiz_json(raw)

    quiz_id = str(uuid.uuid4())
    db.create_quiz(quiz_id, document_id, session_id, user_request, json.dumps(questions))
    return quiz_id, questions

