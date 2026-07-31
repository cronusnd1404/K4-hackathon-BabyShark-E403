"""Deterministic input and output guardrails for the tutor agent."""

import re


MAX_SELECTED_TEXT_CHARS = 6_000
MAX_USER_TEXT_CHARS = 1_000
MAX_PAGE_CONTENT_CHARS = 20_000

SAFE_REFUSAL = (
    "Yêu cầu này nằm ngoài phạm vi trợ giảng nội dung khóa học. "
    "Hãy hỏi về khái niệm, ví dụ hoặc bài tập dựa trên slide đang xem."
)

_INJECTION_PATTERNS = (
    r"\bignore (all |any )?(previous|prior|system)\b",
    r"\b(reveal|show|print|repeat)\b.{0,40}\b(system prompt|api key|password|secret)\b",
    r"\bdeveloper message\b",
    r"\bjailbreak\b",
    r"\bdo anything now\b",
    r"\bbỏ qua\b.{0,30}\b(chỉ dẫn|hướng dẫn|prompt|quy tắc)\b",
    r"\b(tiết lộ|hiển thị|in ra)\b.{0,40}\b(api key|mật khẩu|system prompt|khóa bí mật)\b",
)

_OUT_OF_SCOPE_PATTERNS = (
    r"\b(api key|admin password|mật khẩu quản trị|thông tin cá nhân)\b",
    r"\b(tôi|t|mình)\b.{0,20}\b(đẹp trai|đẹp gái|xinh|giàu)\b",
    r"\b(find|download|tìm|tải)\b.{0,30}\b(pdf gốc|original pdf|private file|file riêng)\b",
)


def clean_text(value, *, max_chars, field_name, allow_empty=False):
    if value is None:
        if allow_empty:
            return None
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    cleaned = value.replace("\x00", "").strip()
    if not cleaned and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    return cleaned[:max_chars]


def refusal_for_user_text(value):
    """Return a safe response for prompt injection or clearly out-of-scope requests."""
    if not value:
        return None
    normalized = " ".join(value.casefold().split())
    patterns = _INJECTION_PATTERNS + _OUT_OF_SCOPE_PATTERNS
    if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns):
        return SAFE_REFUSAL
    return None


def refusal_for_highlight(selected_text, page_content, user_question=None):
    """Screen user-authored text without treating authentic slide text as commands."""
    refusal = refusal_for_user_text(user_question)
    if refusal:
        return refusal
    if selected_text.casefold() not in page_content.casefold():
        return refusal_for_user_text(selected_text)
    return None


def valid_page_numbers(pages):
    return {int(page_number) for page_number, _ in pages}


def filter_related_pages(related_pages, allowed_pages, excluded_pages=()):
    allowed = set(allowed_pages)
    excluded = set(excluded_pages)
    filtered = []
    seen = set()
    for item in related_pages:
        try:
            page_number = int(item["page_number"])
        except (KeyError, TypeError, ValueError):
            continue
        reason = str(item.get("reason", "")).strip()[:500]
        if page_number not in allowed or page_number in excluded or page_number in seen or not reason:
            continue
        seen.add(page_number)
        filtered.append({"page_number": page_number, "reason": reason})
    return filtered


def remove_invalid_citations(text, allowed_pages):
    """Remove model-generated page citations which cannot be verified."""
    allowed = set(allowed_pages)

    def replace(match):
        return match.group(0) if int(match.group(1)) in allowed else "[Nguồn trang không hợp lệ đã bị loại]"

    return re.sub(r"\[(?:Page|Trang)\s+(\d+)\]", replace, text, flags=re.IGNORECASE)


def validate_tree(nodes, allowed_pages, *, depth=1, max_depth=3, allow_empty=False):
    if not isinstance(nodes, list) or not nodes:
        if allow_empty:
            return []
        raise ValueError("Model returned an empty or invalid summary tree")
    allowed = set(allowed_pages)
    validated = []
    for raw in nodes[:12]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title", "")).strip()[:160]
        one_liner = str(raw.get("one_liner", "")).strip()[:500]
        if not title:
            continue
        refs = []
        for ref in raw.get("page_refs", []):
            try:
                page_number = int(ref)
            except (TypeError, ValueError):
                continue
            if page_number in allowed and page_number not in refs:
                refs.append(page_number)
        children = []
        if depth < max_depth and raw.get("children"):
            children = validate_tree(
                raw["children"],
                allowed,
                depth=depth + 1,
                max_depth=max_depth,
                allow_empty=True,
            )
        if not refs and children:
            refs = sorted({ref for child in children for ref in child["page_refs"]})
        if not refs:
            continue
        validated.append(
            {
                "id": "",
                "title": title,
                "one_liner": one_liner,
                "page_refs": refs,
                "children": children,
            }
        )
    if not validated:
        if allow_empty:
            return []
        raise ValueError("Summary tree contains no grounded nodes")
    return validated
