"""Chainlit chat UI for the Ghostfolio Finance AI Agent."""

import logging

import chainlit as cl
from chainlit.input_widget import Select
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.agent import get_agent
from app.agent.models import DEFAULT_MODEL_ID, SUPPORTED_MODELS, get_model_spec
from app.clients.ghostfolio import (
    GhostfolioClient,
    _default_client,
    create_anonymous_user,
    use_client,
)
from app.config import settings
from app.tracing.cost_tracker import cost_tracker
from app.tracing.setup import get_langfuse_handler, init_tracing
from app.verification.disclaimer_injection import inject_disclaimer
from app.verification.hallucination_detection import check_hallucination
from app.verification.numerical_consistency import check_numerical_consistency

logger = logging.getLogger(__name__)

# Initialize tracing on module load
init_tracing()

TOOL_ICONS = {
    "portfolio_summary": "📊",
    "portfolio_performance": "📈",
    "holding_detail": "🔍",
    "transactions": "💸",
    "dividend_history": "💰",
    "symbol_search": "🔎",
    "market_sentiment": "⚖️",
    "add_trade": "➕",
}


def _available_models() -> list[dict]:
    """Return models that have their API key configured."""
    available = []
    for spec in SUPPORTED_MODELS.values():
        has_key = False
        if spec.provider == "groq" and settings.groq_api_key:
            has_key = True
        elif spec.provider == "openai" and settings.openai_api_key:
            has_key = True
        elif spec.provider == "anthropic" and settings.anthropic_api_key:
            has_key = True
        available.append({
            "id": spec.model_id,
            "label": (
                f"{spec.display_name}"
                f"{' ✓' if has_key else ' (no key)'}"
            ),
            "has_key": has_key,
        })
    return available


@cl.on_chat_start
async def on_start():
    """Initialize session — auto-create a new Ghostfolio user per session."""
    cl.user_session.set("message_history", [])
    cl.user_session.set("model_id", DEFAULT_MODEL_ID)

    # Create a new Ghostfolio user for this session
    token = None
    try:
        result = await create_anonymous_user()
        token = result["access_token"]
        user_client = GhostfolioClient(access_token=token)
        cl.user_session.set("ghostfolio_client", user_client)
        logger.info("Created new Ghostfolio user for session")
    except Exception as e:
        logger.warning("Could not create Ghostfolio user: %s. Using default.", e)

    # Model selector
    models = _available_models()
    model_choices = {m["label"]: m["id"] for m in models}
    cl.user_session.set("model_choices", model_choices)

    default_label = next(
        (m["label"] for m in models if m["id"] == DEFAULT_MODEL_ID),
        models[0]["label"],
    )
    chat_settings = cl.ChatSettings([
        Select(
            id="model",
            label="LLM Model",
            values=list(model_choices.keys()),
            initial_value=default_label,
        ),
    ])
    await chat_settings.send()

    spec = get_model_spec(DEFAULT_MODEL_ID)

    if token:
        await cl.Message(
            content=(
                "**Welcome to Ghostfolio AI Agent!** 🎉\n\n"
                "A new portfolio has been created for you.\n\n"
                "Try:\n"
                '- *"I bought 10 shares of AAPL at $230"*\n'
                '- *"Show me my portfolio summary"*\n'
                '- *"How has my portfolio performed?"*\n'
                '- *"Search for Apple stock"*\n\n'
                f"Model: **{spec.display_name}** — "
                "change it in Settings"
            )
        ).send()
    else:
        await cl.Message(
            content=(
                "**Welcome to Ghostfolio AI Agent!** 🏦\n\n"
                "Using shared portfolio.\n\n"
                "Try asking:\n"
                '- *"Show me my portfolio summary"*\n'
                '- *"How has my portfolio performed?"*\n'
                '- *"I bought 10 shares of AAPL at $230"*\n\n'
                f"Model: **{spec.display_name}** — "
                "change it in Settings"
            )
        ).send()


@cl.on_settings_update
async def on_settings_update(settings_update):
    """Handle model selection change."""
    if "model" in settings_update:
        selected_label = settings_update["model"]
        model_choices = cl.user_session.get("model_choices", {})
        model_id = model_choices.get(selected_label, DEFAULT_MODEL_ID)
        cl.user_session.set("model_id", model_id)

        spec = get_model_spec(model_id)
        await cl.Message(
            content=f"Switched to **{spec.display_name}**"
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming chat messages with per-user Ghostfolio client."""
    model_id = cl.user_session.get("model_id", DEFAULT_MODEL_ID)
    history = cl.user_session.get("message_history", [])

    history.append(HumanMessage(content=message.content))

    # Keep sliding window of last 20 messages
    if len(history) > 20:
        history = history[-20:]

    agent = get_agent(model_id)

    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    config = {"recursion_limit": settings.max_agent_iterations}
    if callbacks:
        config["callbacks"] = callbacks

    thinking_msg = cl.Message(content="")
    await thinking_msg.send()

    tool_outputs = []
    tools_called = []

    # Use per-user client if available, otherwise default
    user_client = cl.user_session.get("ghostfolio_client", _default_client)

    with use_client(user_client):
        try:
            result = await agent.ainvoke(
                {"messages": history},
                config=config,
            )

            messages = result.get("messages", [])
            final_message = ""
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
            check_numerical_consistency(final_message, tool_outputs)
            check_hallucination(final_message, tool_outputs)
            final_message = inject_disclaimer(final_message)

            # Track cost
            spec = get_model_spec(model_id)
            cost_tracker.record(
                model=spec.api_model_name,
                input_tokens=total_input,
                output_tokens=total_output,
                trace_id="chainlit",
                operation="chat",
            )

            # Show tool calls as expandable steps
            if tools_called:
                for i, tool_name in enumerate(tools_called):
                    icon = TOOL_ICONS.get(tool_name, "🔧")
                    tool_data = tool_outputs[i] if i < len(tool_outputs) else ""
                    async with cl.Step(name=f"{icon} {tool_name}", type="tool") as step:
                        step.output = tool_data[:500] if tool_data else "OK"

            thinking_msg.content = final_message
            await thinking_msg.update()

            history.append(AIMessage(content=final_message))
            cl.user_session.set("message_history", history)

        except Exception as e:
            thinking_msg.content = (
                f"Sorry, I encountered an error: {str(e)}\n\n"
                "Please check that an LLM API key is configured."
            )
            await thinking_msg.update()


@cl.on_chat_end
async def on_end():
    """Clean up per-user Ghostfolio client on session end."""
    client = cl.user_session.get("ghostfolio_client")
    if client and client is not _default_client:
        await client.close()
