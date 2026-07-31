"""Thin wrapper around the Anthropic API. Single provider, no HTTP layer.

LLM_MODE controls which model every call uses (set in .env, default "dev"):
  - "dev"  -> always claude-haiku-4-5-20251001 (cheap, for iterating on the demo)
  - "demo" -> claude-opus-4-8, falling back to claude-sonnet-5 on any API error
"""

import base64
import os

import anthropic
from dotenv import load_dotenv

from core import db

load_dotenv()

LLM_MODE = os.environ.get("LLM_MODE", "dev").strip().lower()

DEV_MODEL = "claude-haiku-4-5-20251001"
PRIMARY_MODEL = "claude-haiku-4-5-20251001"
FALLBACK_MODEL = "claude-haiku-4-5-20251001"

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


def _call(messages, system=None, max_tokens=4096):
    client = get_client()
    primary = DEV_MODEL if LLM_MODE == "dev" else PRIMARY_MODEL
    fallback = None if LLM_MODE == "dev" else FALLBACK_MODEL

    kwargs = {"model": primary, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    try:
        resp = client.messages.create(**kwargs)
    except Exception:
        # Primary model unavailable/invalid for this account -> retry once with fallback.
        if fallback is None:
            raise
        kwargs["model"] = fallback
        resp = client.messages.create(**kwargs)

    _log_usage(resp)
    return "".join(block.text for block in resp.content if block.type == "text")


def call_text(system, user_text, max_tokens=4096):
    return _call([{"role": "user", "content": user_text}], system=system, max_tokens=max_tokens)


def call_llm(system_prompt, user_prompt, max_tokens=4096):
    """Generic alias of call_text, for callers that think in system/user prompt terms."""
    return call_text(system=system_prompt, user_text=user_prompt, max_tokens=max_tokens)


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
                    "text": (
                        "Transcribe and describe this slide fully: all visible text "
                        "verbatim, plus a description of any diagrams, charts, or images. "
                        "This will be used as the page's text content for an AI tutor, so "
                        "be thorough and objective."
                    ),
                },
            ],
        }
    ]
    return _call(messages, max_tokens=2048)
