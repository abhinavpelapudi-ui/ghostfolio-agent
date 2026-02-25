"""Chainlit chat UI for the Ghostfolio Finance AI Agent."""

import logging

import chainlit as cl
import httpx
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


async def _validate_ghostfolio_token(access_token: str) -> dict | None:
    """Validate a Ghostfolio access token and return user info."""
    base_url = settings.ghostfolio_url.rstrip("/")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{base_url}/api/v1/auth/anonymous",
            json={"accessToken": access_token},
        )
        if resp.status_code != 200:
            return None

        auth_token = resp.json().get("authToken")
        if not auth_token:
            return None

        user_resp = await client.get(
            f"{base_url}/api/v1/user",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        if user_resp.status_code != 200:
            return None

        user_data = user_resp.json()
        return {
            "id": user_data.get("id", "unknown"),
            "role": (
                "admin"
                if "accessAdminControl"
                in user_data.get("permissions", [])
                else "user"
            ),
            "accounts": [
                a.get("name", "")
                for a in user_data.get("accounts", [])
            ],
            "currency": (
                user_data.get("settings", {}).get("baseCurrency", "USD")
            ),
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
    """Two-step token auth, then initialize the chat session."""
    cl.user_session.set("message_history", [])
    cl.user_session.set("model_id", DEFAULT_MODEL_ID)
    cl.user_session.set("authenticated", False)

    # ── Step 1: Ask for email ────────────────────────────────────
    await cl.Message(
        content=(
            "**Welcome to Ghostfolio AI Agent** 🏦\n\n"
            "Enter your **email address** to get started."
        )
    ).send()

    email_res = await cl.AskUserMessage(
        content="Your email:", timeout=300
    ).send()
    if not email_res:
        return

    email = email_res["output"].strip()
    if not email:
        await cl.Message(content="Email cannot be empty.").send()
        return

    # ── Step 2: Generate token & ask user to paste it ────────────
    # Generate a fresh Ghostfolio account token
    new_token = None
    try:
        result = await create_anonymous_user()
        new_token = result["access_token"]
    except Exception as e:
        logger.error("Failed to create Ghostfolio user: %s", e)

    if new_token:
        await cl.Message(
            content=(
                f"**Hi {email}!** A new token has been generated "
                "for you:\n\n"
                f"```\n{new_token}\n```\n\n"
                "**Save this token** — you'll need it to access "
                "this portfolio again.\n\n"
                "Now **paste a token below** to login:\n"
                "- Paste the token above if you're a **new user**\n"
                "- Or paste your **existing saved token** to load "
                "your portfolio"
            )
        ).send()
    else:
        await cl.Message(
            content=(
                f"**Hi {email}!** Paste your existing "
                "Ghostfolio token below to login:"
            )
        ).send()

    token_res = await cl.AskUserMessage(
        content="Paste your token:", timeout=300
    ).send()
    if not token_res:
        return

    token = token_res["output"].strip()
    if not token:
        await cl.Message(
            content="No token provided. Please refresh to try again."
        ).send()
        return

    # ── Validate the token ───────────────────────────────────────
    user_info = await _validate_ghostfolio_token(token)
    if not user_info:
        await cl.Message(
            content=(
                "**Invalid token.** Please refresh the page "
                "and try again."
            )
        ).send()
        return

    # ── Create per-user Ghostfolio client ────────────────────────
    user_client = GhostfolioClient(access_token=token)
    cl.user_session.set("ghostfolio_client", user_client)
    cl.user_session.set("authenticated", True)
    cl.user_session.set("user_email", email)

    # ── Model selector ───────────────────────────────────────────
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

    # ── Welcome message ──────────────────────────────────────────
    spec = get_model_spec(DEFAULT_MODEL_ID)
    is_new = token == new_token
    accounts_str = (
        ", ".join(user_info["accounts"])
        if user_info["accounts"]
        else "None yet"
    )

    if is_new:
        await cl.Message(
            content=(
                "**You're all set!** 🎉 "
                "Your portfolio is empty — let's fix that.\n\n"
                "Add your first trade:\n"
                '- *"I bought 10 shares of AAPL at $230"*\n'
                '- *"Add a purchase: 5 VOO at $520"*\n\n'
                f"Model: **{spec.display_name}** — "
                "change it in Settings"
            )
        ).send()
    else:
        await cl.Message(
            content=(
                f"**Logged in!** 🏦 "
                f"Currency: **{user_info['currency']}** | "
                f"Accounts: **{accounts_str}**\n\n"
                "Try asking:\n"
                "- *\"Show me my portfolio summary\"*\n"
                "- *\"How has my portfolio performed?\"*\n"
                "- *\"I bought 10 shares of AAPL at $230\"*\n\n"
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
    if not cl.user_session.get("authenticated"):
        return  # ignore messages until token auth is done

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

    # Use per-user Ghostfolio client (falls back to default if none)
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
