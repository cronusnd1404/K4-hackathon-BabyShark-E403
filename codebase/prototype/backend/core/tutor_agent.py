"""Scoped runtime agent for grounded tutor tasks."""

from core.agent_tools import TOOL_DEFINITIONS, execute_tool
from core.llm_client import call_tool_agent


def run_tutor_agent(document_id, system_prompt, user_prompt, *, max_tokens=2048):
    """Bind read-only tools to one server-selected document."""
    return call_tool_agent(
        system_prompt,
        user_prompt,
        TOOL_DEFINITIONS,
        lambda name, payload: execute_tool(document_id, name, payload),
        max_tokens=max_tokens,
        max_turns=3,
    )
