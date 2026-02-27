"""Chat UI API routes — per-user Ghostfolio token auth."""

import logging

from fastapi import APIRouter, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.agent import run_agent
from app.agent.models import DEFAULT_MODEL_ID, SUPPORTED_MODELS
from app.clients.ghostfolio import GhostfolioClient, create_anonymous_user
from app.config import settings
from app.memory.memory_store import memory_store
from app.models.schemas import (
    ChatFeedbackRequest,
    ChatLoginRequest,
    ChatLoginResponse,
    ChatSendRequest,
    ChatSendResponse,
    ChatSignupRequest,
    ChatSignupResponse,
    PreferenceRequest,
)
from app.tracing.feedback_store import feedback_store

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_authenticated_client(token: str) -> GhostfolioClient:
    """Create and authenticate a GhostfolioClient from a user token."""
    client = GhostfolioClient(access_token=token)
    try:
        await client._authenticate()
    except Exception as e:
        await client.close()
        raise HTTPException(status_code=401, detail="Invalid Ghostfolio token") from e
    return client


@router.post("/login", response_model=ChatLoginResponse)
async def chat_login(request: ChatLoginRequest):
    """Validate a Ghostfolio access token."""
    client = await _get_authenticated_client(request.token)
    await client.close()
    return ChatLoginResponse(success=True, email=request.email)


@router.post("/signup", response_model=ChatSignupResponse)
async def chat_signup(request: ChatSignupRequest):
    """Create a new anonymous Ghostfolio user."""
    try:
        result = await create_anonymous_user()
    except Exception as e:
        logger.error("Signup failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    return ChatSignupResponse(access_token=result["access_token"])


@router.post("/send", response_model=ChatSendResponse)
async def chat_send(
    request: ChatSendRequest,
    x_ghostfolio_token: str = Header(..., alias="X-Ghostfolio-Token"),
):
    """Send a message to the AI agent."""
    client = await _get_authenticated_client(x_ghostfolio_token)

    # Build LangChain message history
    lc_history = []
    for msg in request.history[-18:]:
        if msg.role == "user":
            lc_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_history.append(AIMessage(content=msg.content))

    try:
        result = await run_agent(
            command=request.message,
            model_id=request.model_id or DEFAULT_MODEL_ID,
            ghostfolio_client=client,
            history=lc_history,
            user_token=x_ghostfolio_token,
        )
    finally:
        await client.close()

    return ChatSendResponse(
        response=result["response"],
        tools_called=result.get("tools_called", []),
        cost_usd=result.get("cost_usd", 0),
        model=result.get("model", ""),
        trace_id=result.get("trace_id", ""),
        skill_used=result.get("skill_used", ""),
    )


@router.post("/feedback")
async def chat_feedback(
    request: ChatFeedbackRequest,
    x_ghostfolio_token: str = Header(..., alias="X-Ghostfolio-Token"),
):
    """Record thumbs up/down feedback for a response."""
    feedback_store.record(trace_id=request.trace_id, rating=request.rating)

    # Close the feedback loop: store lesson on thumbs-down
    if request.rating == "down" and request.query:
        memory_store.add_lesson(
            user_token=x_ghostfolio_token,
            query_pattern=request.query,
            lesson=(
                f"A similar query ('{request.query[:80]}') received negative feedback. "
                "Take extra care with accuracy and completeness."
            ),
        )

    return {"success": True}


@router.get("/feedback/summary")
async def chat_feedback_summary():
    """Get feedback summary for observability."""
    return feedback_store.get_summary()


@router.get("/preferences")
async def get_preferences(
    x_ghostfolio_token: str = Header(..., alias="X-Ghostfolio-Token"),
):
    """Get stored user preferences."""
    return memory_store.get_preferences(x_ghostfolio_token)


@router.put("/preferences")
async def set_preference(
    request: PreferenceRequest,
    x_ghostfolio_token: str = Header(..., alias="X-Ghostfolio-Token"),
):
    """Set a user preference explicitly."""
    memory_store.set_preference(x_ghostfolio_token, request.key, request.value)
    return {"success": True}


@router.get("/models")
async def chat_models():
    """List available LLM models."""
    models = []
    for spec in SUPPORTED_MODELS.values():
        available = True
        if spec.provider == "groq" and not settings.groq_api_key:
            available = False
        elif spec.provider == "openai" and not settings.openai_api_key:
            available = False
        elif spec.provider == "anthropic" and not settings.anthropic_api_key:
            available = False
        models.append({
            "model_id": spec.model_id,
            "display_name": spec.display_name,
            "provider": spec.provider,
            "is_free": spec.is_free,
            "available": available,
        })
    return {"models": models, "default": DEFAULT_MODEL_ID}
