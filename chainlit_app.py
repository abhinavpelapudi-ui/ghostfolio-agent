"""Chainlit chat UI for the Ghostfolio Finance AI Agent."""

import httpx
import chainlit as cl
from chainlit.input_widget import Select
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.agent import get_agent
from app.agent.models import DEFAULT_MODEL_ID, SUPPORTED_MODELS, get_model_spec
from app.config import settings
from app.tracing.cost_tracker import cost_tracker
from app.tracing.setup import get_langfuse_handler, init_tracing
from app.verification.disclaimer_injection import inject_disclaimer
from app.verification.hallucination_detection import check_hallucination
from app.verification.numerical_consistency import check_numerical_consistency

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
        # Authenticate with Ghostfolio
        resp = await client.post(
            f"{base_url}/api/v1/auth/anonymous",
            json={"accessToken": access_token},
        )
        if resp.status_code != 200:
            return None

        auth_token = resp.json().get("authToken")
        if not auth_token:
            return None

        # Fetch user info
        user_resp = await client.get(
            f"{base_url}/api/v1/user",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        if user_resp.status_code != 200:
            return None

        user_data = user_resp.json()
        return {
            "id": user_data.get("id", "unknown"),
            "role": "admin" if "accessAdminControl" in user_data.get("permissions", []) else "user",
            "accounts": [a.get("name", "") for a in user_data.get("accounts", [])],
            "currency": user_data.get("settings", {}).get("baseCurrency", "USD"),
        }


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """Authenticate user with their Ghostfolio access token.

    Username: any display name
    Password: Ghostfolio access token (Security Token)
    """
    user_info = await _validate_ghostfolio_token(password)
    if user_info:
        return cl.User(
            identifier=username or f"user-{user_info['id'][:8]}",
            metadata={
                "ghostfolio_user_id": user_info["id"],
                "role": user_info["role"],
                "currency": user_info["currency"],
                "accounts": user_info["accounts"],
            },
        )
    return None


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
            "label": f"{spec.display_name}{' ✓' if has_key else ' (no key)'}",
            "has_key": has_key,
        })
    return available


@cl.on_chat_start
async def on_start():
    """Initialize the chat session with model selector."""
    cl.user_session.set("message_history", [])
    cl.user_session.set("model_id", DEFAULT_MODEL_ID)

    # Get authenticated user info
    user = cl.user_session.get("user")
    user_name = user.identifier if user else "User"
    user_currency = user.metadata.get("currency", "USD") if user else "USD"
    user_accounts = user.metadata.get("accounts", []) if user else []

    # Build model selector options
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

    # Personalized welcome
    accounts_str = ", ".join(user_accounts) if user_accounts else "No accounts"
    spec = get_model_spec(DEFAULT_MODEL_ID)
    await cl.Message(
        content=(
            f"**Welcome, {user_name}!** 🏦\n\n"
            f"Connected to Ghostfolio | Currency: **{user_currency}** | Accounts: **{accounts_str}**\n\n"
            "I can help you analyze your portfolio. Try asking:\n"
            "- *\"Show me my portfolio summary\"*\n"
            "- *\"How has my portfolio performed this year?\"*\n"
            "- *\"Tell me about my AAPL holding\"*\n"
            "- *\"What are my recent transactions?\"*\n"
            "- *\"Show my dividend history for VOO\"*\n"
            "- *\"Search for Tesla stock\"*\n"
            "- *\"Analyze my portfolio risk\"*\n"
            "- *\"I bought 10 shares of AAPL at $230\"*\n"
            "- *\"Add a purchase: 5 VOO at $520\"*\n\n"
            f"Model: **{spec.display_name}** — change it in ⚙️ Settings"
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
    """Handle incoming chat messages."""
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
        thinking_msg.content = f"Sorry, I encountered an error: {str(e)}\n\nPlease check that an LLM API key is configured."
        await thinking_msg.update()
