"""LangGraph ReAct agent for Ghostfolio finance queries."""

import logging
import uuid

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.agent.models import DEFAULT_MODEL_ID, ModelSpec, get_model_spec
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import ALL_TOOLS
from app.config import settings
from app.tracing.cost_tracker import cost_tracker
from app.tracing.setup import get_langfuse_handler
from app.verification.disclaimer_injection import inject_disclaimer
from app.verification.hallucination_detection import check_hallucination
from app.verification.numerical_consistency import check_numerical_consistency

logger = logging.getLogger(__name__)


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
    agent = create_react_agent(llm, ALL_TOOLS, prompt=SYSTEM_PROMPT)
    _agent_cache[model_id] = agent
    return agent


async def run_agent(command: str, model_id: str = DEFAULT_MODEL_ID) -> dict:
    trace_id = str(uuid.uuid4())
    spec = get_model_spec(model_id)
    agent = get_agent(model_id)

    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    config = {"recursion_limit": settings.max_agent_iterations}
    if callbacks:
        config["callbacks"] = callbacks

    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=command)]},
            config=config,
        )
    except Exception as e:
        logger.error("Agent execution failed: %s", e)
        return {
            "response": "Sorry, I encountered an error processing your request. Please try again.",
            "trace_id": trace_id,
            "tools_called": [],
            "cost_usd": 0,
            "model": spec.api_model_name,
            "error": str(e),
            "verification": {},
        }

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
    final_message = inject_disclaimer(final_message)

    cost = cost_tracker.record(
        model=spec.api_model_name,
        input_tokens=total_input,
        output_tokens=total_output,
        trace_id=trace_id,
        operation="finance_query",
    )

    return {
        "response": final_message,
        "trace_id": trace_id,
        "tools_called": tools_called,
        "cost_usd": round(cost, 6),
        "model": spec.api_model_name,
        "verification": {
            "numerical_consistent": consistency_result.get("consistent", True),
            "hallucination_detected": hallucination_result.get("detected", False),
            "disclaimer_injected": True,
        },
    }
