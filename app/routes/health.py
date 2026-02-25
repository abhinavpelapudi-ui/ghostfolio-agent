"""Health check and cost metrics endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.auth import require_auth
from app.clients.ghostfolio import ghostfolio_client
from app.config import settings
from app.tracing.cost_tracker import cost_tracker

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    gf_connected = False
    try:
        await ghostfolio_client.get_accounts()
        gf_connected = True
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "ghostfolio-agent",
        "ghostfolio_connected": gf_connected,
        "llm_providers": {
            "groq": bool(settings.groq_api_key),
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
        },
    }


@router.get("/agent/costs")
async def get_costs(_token: str = Depends(require_auth)):
    return cost_tracker.get_summary()
