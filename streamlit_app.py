"""Streamlit chat UI for the Ghostfolio Finance AI Agent."""

import asyncio
import logging

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.agent import run_agent
from app.agent.models import DEFAULT_MODEL_ID, SUPPORTED_MODELS, get_model_spec
from app.clients.ghostfolio import GhostfolioClient, create_anonymous_user
from app.config import settings
from app.tracing.setup import init_tracing

logger = logging.getLogger(__name__)

# Initialize tracing once
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

# ── Session state defaults ───────────────────────────────────────────
DEFAULTS = {
    "authenticated": False,
    "access_token": None,
    "ghostfolio_client": None,
    "chat_history": [],
    "model_id": DEFAULT_MODEL_ID,
    "signup_token": None,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


def run_async(coro):
    """Run an async coroutine from Streamlit's sync context."""
    return asyncio.run(coro)


def available_models() -> list[dict]:
    """Return models with availability info."""
    models = []
    for spec in SUPPORTED_MODELS.values():
        has_key = False
        if spec.provider == "groq" and settings.groq_api_key:
            has_key = True
        elif spec.provider == "openai" and settings.openai_api_key:
            has_key = True
        elif spec.provider == "anthropic" and settings.anthropic_api_key:
            has_key = True
        models.append({
            "id": spec.model_id,
            "label": f"{spec.display_name}{' ✓' if has_key else ' (no key)'}",
            "has_key": has_key,
        })
    return models


def build_langchain_history() -> list:
    """Convert chat history to LangChain messages for multi-turn conversation."""
    lc_messages = []
    for msg in st.session_state["chat_history"][-18:]:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
    return lc_messages


# ── Auth Page ────────────────────────────────────────────────────────
def render_auth_page():
    st.set_page_config(page_title="Ghostfolio AI Agent", page_icon="🏦", layout="centered")
    st.title("🏦 Ghostfolio AI Agent")
    st.markdown("Manage your investment portfolio with AI")

    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        st.markdown("Enter your Ghostfolio security token to access your portfolio.")
        token_input = st.text_input(
            "Security Token",
            type="password",
            placeholder="Paste your token here",
            key="login_token",
        )
        if st.button("Login", key="login_btn", use_container_width=True):
            if not token_input.strip():
                st.error("Please enter your security token.")
            else:
                with st.spinner("Validating token..."):
                    try:
                        client = GhostfolioClient(access_token=token_input.strip())
                        run_async(client._authenticate())
                        st.session_state["authenticated"] = True
                        st.session_state["access_token"] = token_input.strip()
                        st.session_state["ghostfolio_client"] = client
                        st.rerun()
                    except Exception:
                        st.error("Invalid token. Please check and try again.")

    with tab_signup:
        # If we already created a token, show it before entering chat
        if st.session_state["signup_token"]:
            st.success("Account created successfully!")
            st.warning(
                "⚠️ **IMPORTANT:** Save your security token below. "
                "You will need it to log in again. It is only shown once."
            )
            st.code(st.session_state["signup_token"], language=None)
            if st.button("Continue to Chat →", key="continue_btn", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["signup_token"] = None
                st.rerun()
            return

        st.markdown("Create a new portfolio account.")
        st.markdown(
            "**Terms and Conditions**\n\n"
            "This AI agent provides financial data from your Ghostfolio portfolio. "
            "It does not provide financial advice. "
            "All investment decisions are your own responsibility."
        )
        agree = st.checkbox(
            "I understand that if I lose my security token, "
            "I cannot recover my account.",
            key="agree_terms",
        )
        if st.button(
            "Create Account",
            key="signup_btn",
            disabled=not agree,
            use_container_width=True,
        ):
            with st.spinner("Creating your account..."):
                try:
                    result = run_async(create_anonymous_user())
                    new_token = result["access_token"]

                    # Prepare client but don't authenticate yet
                    client = GhostfolioClient(access_token=new_token)
                    run_async(client._authenticate())
                    st.session_state["access_token"] = new_token
                    st.session_state["ghostfolio_client"] = client
                    # Stay on auth page to show token first
                    st.session_state["signup_token"] = new_token
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create account: {e}")


# ── Chat Page ────────────────────────────────────────────────────────
def render_chat_page():
    st.set_page_config(page_title="Ghostfolio AI Agent", page_icon="🏦", layout="wide")

    # Sidebar
    with st.sidebar:
        st.title("⚙️ Settings")

        models = available_models()
        model_options = {m["label"]: m["id"] for m in models}
        current_idx = 0
        for i, m in enumerate(models):
            if m["id"] == st.session_state["model_id"]:
                current_idx = i
                break

        selected_label = st.selectbox(
            "Model",
            options=list(model_options.keys()),
            index=current_idx,
        )
        st.session_state["model_id"] = model_options[selected_label]

        st.divider()
        token = st.session_state.get("access_token", "")
        if token:
            st.caption(f"Token: ...{token[-8:]}")

        if st.button("Logout", use_container_width=True):
            client = st.session_state.get("ghostfolio_client")
            if client:
                try:
                    run_async(client.close())
                except Exception:
                    pass
            for key in DEFAULTS:
                st.session_state[key] = DEFAULTS[key]
            st.rerun()

    # Main chat area
    st.title("🏦 Ghostfolio AI Agent")

    # Welcome message if no history
    if not st.session_state["chat_history"]:
        spec = get_model_spec(st.session_state["model_id"])
        with st.chat_message("assistant"):
            st.markdown(
                "**Welcome!** Your portfolio is ready.\n\n"
                "Try asking:\n"
                '- "I bought 10 shares of AAPL at $230"\n'
                '- "Show me my portfolio summary"\n'
                '- "How has my portfolio performed?"\n'
                '- "Search for Apple stock"\n\n'
                f"Model: **{spec.display_name}** — change it in the sidebar"
            )

    # Render chat history
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tools"):
                with st.expander(f"🔧 Tools: {', '.join(msg['tools'])}"):
                    for tool_name in msg["tools"]:
                        icon = TOOL_ICONS.get(tool_name, "🔧")
                        st.markdown(f"- {icon} `{tool_name}`")
            if msg.get("cost") and msg["cost"] > 0:
                st.caption(f"Cost: ${msg['cost']:.6f}")

    # Chat input
    if prompt := st.chat_input("Ask about your portfolio..."):
        # Show user message
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Run agent
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                history = build_langchain_history()
                result = run_async(
                    run_agent(
                        command=prompt,
                        model_id=st.session_state["model_id"],
                        ghostfolio_client=st.session_state["ghostfolio_client"],
                        history=history,
                    )
                )

            response_text = result["response"]
            tools_called = result.get("tools_called", [])
            cost = result.get("cost_usd", 0)

            st.markdown(response_text)

            if tools_called:
                with st.expander(f"🔧 Tools: {', '.join(tools_called)}"):
                    for tool_name in tools_called:
                        icon = TOOL_ICONS.get(tool_name, "🔧")
                        st.markdown(f"- {icon} `{tool_name}`")

            if cost > 0:
                st.caption(f"Cost: ${cost:.6f}")

        # Save to history
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": response_text,
            "tools": tools_called,
            "cost": cost,
        })


# ── Main ─────────────────────────────────────────────────────────────
if st.session_state["authenticated"]:
    render_chat_page()
else:
    render_auth_page()
