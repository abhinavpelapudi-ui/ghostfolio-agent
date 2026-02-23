"""Request/Response Pydantic models."""

from pydantic import BaseModel, Field


class AgentCommandRequest(BaseModel):
    command: str = Field(..., max_length=10_000, description="Natural language finance query")
    model: str = Field(default="", max_length=50, description="LLM model ID override")


class AgentCommandResponse(BaseModel):
    success: bool
    response: str
    trace_id: str = ""
    tools_called: list[str] = []
    cost_usd: float = 0.0
    model: str = ""
    verification: dict = {}


class HealthResponse(BaseModel):
    status: str
    service: str
    ghostfolio_connected: bool
    llm_providers: dict[str, bool]
