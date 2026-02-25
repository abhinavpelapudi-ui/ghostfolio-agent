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


# ── Chat UI schemas ──────────────────────────────────────────────────
class ChatLoginRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Ghostfolio access token")
    email: str = Field(default="", description="User email (stored client-side only)")


class ChatLoginResponse(BaseModel):
    success: bool
    email: str = ""


class ChatSignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=200)


class ChatSignupResponse(BaseModel):
    access_token: str


class ChatMessageItem(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatSendRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)
    model_id: str = Field(default="", max_length=50)
    history: list[ChatMessageItem] = Field(default_factory=list)


class ChatSendResponse(BaseModel):
    response: str
    tools_called: list[str] = []
    cost_usd: float = 0.0
    model: str = ""
