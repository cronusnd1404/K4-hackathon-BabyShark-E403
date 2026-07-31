# VLearn Tutor+ backend

FastAPI backend for PDF ingest, grounded summary trees, personalized explanations,
cross-page links, and exercises.

## Agent design

The tutor uses a bounded tool-calling loop. The model can make at most three tool
rounds before it must return an answer. Every tool is read-only and bound to the
`document_id` selected by server code, so model-generated arguments cannot switch
to another document.

Available tools:

- `get_page`: reads one existing page.
- `search_document`: ranks up to five pages by query-term matches.
- `get_document_index`: returns page numbers and short previews.

Main modules:

- `core/prompts.py`: versioned system and task prompts.
- `core/agent_tools.py`: tool schemas and deterministic executors.
- `core/tutor_agent.py`: document-scoped runtime agent.
- `core/llm_client.py`: Anthropic calls and bounded tool loop.
- `core/guardrails.py`: input screening, limits, citation filtering, and tree validation.

## Guardrails

- User text and PDF text are delimited as untrusted data in every prompt.
- Prompt-injection, credential, private-data, and obvious out-of-scope requests are
  refused before an LLM call.
- Highlighted injection examples remain explainable when the exact text exists in
  the current page; the same text pasted from outside the page is refused.
- Document and page existence is checked before model calls.
- Related pages, citations, and summary nodes are filtered against pages stored for
  the current document.
- PDF ingest accepts a filename only, never an arbitrary filesystem path.
- Request sizes, fields, CORS origins, tool rounds, and tool result sizes are bounded.

These controls reduce risk; they do not prove model output is factually correct.
Keep page citations visible so learners can verify important claims.

## Run

From this directory:

```powershell
Copy-Item .env.example .env
# Add ANTHROPIC_API_KEY to .env
uvicorn main:app --port 8020
```

Run offline tests:

```powershell
python -m unittest discover -s tests -v
```
