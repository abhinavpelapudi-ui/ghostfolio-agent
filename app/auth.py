"""Bearer token authentication for the agent API."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer()


def _get_api_key() -> str:
    return settings.agent_api_key or settings.ghostfolio_access_token


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    expected = _get_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No API key configured. Set AGENT_API_KEY or GHOSTFOLIO_ACCESS_TOKEN.",
        )
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    return token
