"""Agent command endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from app.agent.agent import run_agent
from app.agent.models import DEFAULT_MODEL_ID, SUPPORTED_MODELS
from app.auth import require_auth
from app.config import settings
from app.models.schemas import AgentCommandRequest, AgentCommandResponse

router = APIRouter()


@router.post("/command", response_model=AgentCommandResponse)
async def handle_command(request: AgentCommandRequest, _token: str = Depends(require_auth)):
    if not request.command.strip():
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    result = await run_agent(
        command=request.command,
        model_id=request.model or DEFAULT_MODEL_ID,
    )

    return AgentCommandResponse(
        success="error" not in result,
        response=result["response"],
        trace_id=result["trace_id"],
        tools_called=result["tools_called"],
        cost_usd=result["cost_usd"],
        model=result.get("model", ""),
        verification=result.get("verification", {}),
    )


@router.get("/models")
async def list_models():
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
