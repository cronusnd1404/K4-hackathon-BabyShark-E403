"""Thin wrapper around the Anthropic API. Single provider, no HTTP layer.

LLM_MODE controls model selection (set in .env, default "dev"). Model IDs can be
overridden without code changes through ANTHROPIC_*_MODEL variables.
"""

import base64
import json
import os

import anthropic
from dotenv import load_dotenv

from core import db
from core.prompts import VISION_PROMPT

load_dotenv()

LLM_MODE = os.environ.get("LLM_MODE", "dev").strip().lower()
if LLM_MODE not in {"dev", "demo"}:
    raise RuntimeError("LLM_MODE must be 'dev' or 'demo'")

DEV_MODEL = os.environ.get("ANTHROPIC_DEV_MODEL", "claude-haiku-4-5-20251001")
PRIMARY_MODEL = os.environ.get("ANTHROPIC_PRIMARY_MODEL", DEV_MODEL)
FALLBACK_MODEL = os.environ.get("ANTHROPIC_FALLBACK_MODEL", DEV_MODEL)

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _log_usage(resp):
    usage = getattr(resp, "usage", None)
    if usage is None:
        return
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    print(f"[llm_client] model={resp.model} input_tokens={input_tokens} output_tokens={output_tokens}")
    db.log_api_call(resp.model, input_tokens, output_tokens)


def _create_message(kwargs):
    client = get_client()
    primary = DEV_MODEL if LLM_MODE == "dev" else PRIMARY_MODEL
    fallback = None if LLM_MODE == "dev" else FALLBACK_MODEL
    kwargs = dict(kwargs, model=primary)
    try:
        resp = client.messages.create(**kwargs)
    except Exception:
        # Primary model unavailable/invalid for this account -> retry once with fallback.
        if fallback is None or fallback == primary:
            raise
        kwargs["model"] = fallback
        resp = client.messages.create(**kwargs)
    _log_usage(resp)
    return resp


def _call(messages, system=None, max_tokens=4096):
    kwargs = {"max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    resp = _create_message(kwargs)
    return "".join(block.text for block in resp.content if block.type == "text")


def call_text(system, user_text, max_tokens=4096):
    return _call([{"role": "user", "content": user_text}], system=system, max_tokens=max_tokens)


def call_llm(system_prompt, user_prompt, max_tokens=4096):
    """Generic alias of call_text, for callers that think in system/user prompt terms."""
    return call_text(system=system_prompt, user_text=user_prompt, max_tokens=max_tokens)


def call_tool_agent(
    system_prompt,
    user_prompt,
    tools,
    execute_tool,
    *,
    max_tokens=2048,
    max_turns=3,
):
    """Run a bounded Anthropic tool-use loop and return the final text."""
    messages = [{"role": "user", "content": user_prompt}]
    for _ in range(max_turns):
        resp = _create_message(
            {
                "max_tokens": max_tokens,
                "messages": messages,
                "system": system_prompt,
                "tools": tools,
            }
        )
        tool_blocks = [block for block in resp.content if block.type == "tool_use"]
        if not tool_blocks:
            return "".join(block.text for block in resp.content if block.type == "text")

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in tool_blocks:
            try:
                output = execute_tool(block.name, block.input)
                content = json.dumps(output, ensure_ascii=False)
                is_error = False
            except (KeyError, TypeError, ValueError) as exc:
                content = str(exc)
                is_error = True
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": results})

    messages.append(
        {
            "role": "user",
            "content": "Tool budget reached. Return the final grounded answer now; do not call more tools.",
        }
    )
    resp = _create_message(
        {
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system_prompt,
        }
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def call_chat(system, messages, max_tokens=4096):
    """Like call_text, but takes a real multi-turn message list (alternating
    user/assistant, ending in "user") so prior chat turns are passed as actual
    conversation instead of being flattened into one text blob."""
    return _call(messages, system=system, max_tokens=max_tokens)



def describe_page_with_vision_model(png_bytes):
    b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b64},
                },
                {
                    "type": "text",
                    "text": VISION_PROMPT,
                },
            ],
        }
    ]
    return _call(messages, max_tokens=2048)
