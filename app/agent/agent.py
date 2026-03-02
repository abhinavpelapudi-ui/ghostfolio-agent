"""LangGraph ReAct agent for Ghostfolio finance queries."""

import logging
import uuid
from contextvars import ContextVar

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.agent.models import DEFAULT_MODEL_ID, ModelSpec, get_model_spec
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.skills import Skill, classify_intent
from app.agent.tools import ALL_TOOLS
from app.clients.ghostfolio import GhostfolioClient, RateLimitError, _default_client, use_client
from app.config import settings
from app.memory.memory_store import memory_store
from app.tracing.cost_tracker import cost_tracker
from app.tracing.setup import get_langfuse_handler
from app.verification.disclaimer_injection import inject_disclaimer
from app.verification.hallucination_detection import check_hallucination
from app.verification.numerical_consistency import check_numerical_consistency
from app.verification.risk_threshold import check_risk_thresholds

logger = logging.getLogger(__name__)

# ── Per-request context for dynamic prompt ──────────────────────────
_current_skill: ContextVar[Skill | None] = ContextVar("current_skill", default=None)
_current_memory_context: ContextVar[str] = ContextVar("memory_context", default="")


def _build_dynamic_prompt(state: dict) -> list:
    """Build system prompt dynamically based on active skill and memory context."""
    parts = [SYSTEM_PROMPT]

    skill = _current_skill.get()
    if skill:
        parts.append(
            f"\n\nCURRENT TASK CONTEXT ({skill.display_name}):\n"
            f"{skill.prompt_addon}\n"
            f"Most relevant tools for this request: {', '.join(skill.relevant_tools)}. "
            "You may use other tools if needed, but prefer the ones listed above."
        )

    memory_ctx = _current_memory_context.get()
    if memory_ctx:
        parts.append(f"\n\nUSER CONTEXT:\n{memory_ctx}")

    return [SystemMessage(content="\n".join(parts))] + state["messages"]


def _create_llm(spec: ModelSpec) -> BaseChatModel:
    if spec.provider == "groq":
        return ChatGroq(model=spec.api_model_name, temperature=spec.temperature, api_key=settings.groq_api_key)
    elif spec.provider == "openai":
        return ChatOpenAI(model=spec.api_model_name, temperature=spec.temperature, api_key=settings.openai_api_key)
    elif spec.provider == "anthropic":
        return ChatAnthropic(
            model=spec.api_model_name, temperature=spec.temperature, api_key=settings.anthropic_api_key
        )
    raise ValueError(f"Unknown provider: {spec.provider}")


_agent_cache: dict[str, object] = {}


def get_agent(model_id: str = DEFAULT_MODEL_ID):
    if model_id in _agent_cache:
        return _agent_cache[model_id]
    spec = get_model_spec(model_id)
    llm = _create_llm(spec)
    agent = create_react_agent(llm, ALL_TOOLS, prompt=_build_dynamic_prompt)
    _agent_cache[model_id] = agent
    return agent


async def run_agent(
    command: str,
    model_id: str = DEFAULT_MODEL_ID,
    ghostfolio_client: GhostfolioClient | None = None,
    history: list | None = None,
    user_token: str = "",
) -> dict:
    trace_id = str(uuid.uuid4())
    spec = get_model_spec(model_id)
    agent = get_agent(model_id)

    # Skill classification
    skill = classify_intent(command)

    # Memory context
    memory_ctx = memory_store.build_context(user_token, command) if user_token else ""

    # Set per-request context
    skill_tok = _current_skill.set(skill)
    memory_tok = _current_memory_context.set(memory_ctx)

    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    config = {"recursion_limit": settings.max_agent_iterations}
    if callbacks:
        config["callbacks"] = callbacks

    client_to_use = ghostfolio_client or _default_client
    try:
        with use_client(client_to_use):
            try:
                result = await agent.ainvoke(
                    {"messages": (history or []) + [HumanMessage(content=command)]},
                    config=config,
                )
            except RateLimitError as e:
                logger.warning("Rate limited by Ghostfolio API: %s", e)
                return {
                    "response": (
                        f"The portfolio service is temporarily rate-limited. "
                        f"Please wait {e.retry_after} seconds and try again."
                    ),
                    "trace_id": trace_id,
                    "tools_called": [],
                    "cost_usd": 0,
                    "model": spec.api_model_name,
                    "skill_used": skill.name,
                    "error": "rate_limited",
                    "retry_after": e.retry_after,
                    "verification": {},
                }
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 401:
                    logger.warning("Authentication failed during agent execution")
                    return {
                        "response": "Your session has expired. Please log in again.",
                        "trace_id": trace_id,
                        "tools_called": [],
                        "cost_usd": 0,
                        "model": spec.api_model_name,
                        "skill_used": skill.name,
                        "error": "auth_expired",
                        "verification": {},
                    }
                logger.error("HTTP error during agent execution: %s", e)
                return {
                    "response": f"A service error occurred (HTTP {status}). Please try again.",
                    "trace_id": trace_id,
                    "tools_called": [],
                    "cost_usd": 0,
                    "model": spec.api_model_name,
                    "skill_used": skill.name,
                    "error": str(e),
                    "verification": {},
                }
            except Exception as e:
                logger.error("Agent execution failed: %s", e)
                return {
                    "response": "Sorry, I encountered an error processing your request. Please try again.",
                    "trace_id": trace_id,
                    "tools_called": [],
                    "cost_usd": 0,
                    "model": spec.api_model_name,
                    "skill_used": skill.name,
                    "error": str(e),
                    "verification": {},
                }
    finally:
        _current_skill.reset(skill_tok)
        _current_memory_context.reset(memory_tok)

    messages = result.get("messages", [])
    final_message = ""
    tools_called = []
    tool_outputs = []
    total_input = 0
    total_output = 0

    for msg in messages:
        if hasattr(msg, "type") and msg.type == "tool":
            tools_called.append(msg.name)
            tool_outputs.append(msg.content)
        if hasattr(msg, "type") and msg.type == "ai" and isinstance(msg.content, str) and msg.content:
            final_message = msg.content
        if hasattr(msg, "response_metadata"):
            usage = msg.response_metadata.get("usage", {})
            total_input += usage.get("input_tokens", usage.get("prompt_tokens", 0))
            total_output += usage.get("output_tokens", usage.get("completion_tokens", 0))

    # Verification pipeline
    consistency_result = check_numerical_consistency(final_message, tool_outputs)
    hallucination_result = check_hallucination(final_message, tool_outputs)
    risk_warnings = check_risk_thresholds(tool_outputs)
    if risk_warnings:
        final_message += "\n\n" + "\n".join(f"Warning: {w}" for w in risk_warnings)
    final_message = inject_disclaimer(final_message)

    cost = cost_tracker.record(
        model=spec.api_model_name,
        input_tokens=total_input,
        output_tokens=total_output,
        trace_id=trace_id,
        operation="finance_query",
    )

    # Memory: extract preferences and cache facts
    if user_token:
        memory_store.extract_preferences(user_token, command, tools_called)
        for i, tool_name in enumerate(tools_called):
            if i < len(tool_outputs):
                memory_store.cache_fact(user_token, tool_name, tool_outputs[i])

    return {
        "response": final_message,
        "trace_id": trace_id,
        "tools_called": tools_called,
        "cost_usd": round(cost, 6),
        "model": spec.api_model_name,
        "skill_used": skill.name,
        "verification": {
            "numerical_consistent": consistency_result.get("consistent", True),
            "hallucination_detected": hallucination_result.get("detected", False),
            "risk_warnings": risk_warnings,
            "disclaimer_injected": True,
        },
    }
