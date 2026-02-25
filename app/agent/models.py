"""Multi-provider LLM model registry."""

from dataclasses import dataclass
from typing import Literal

Provider = Literal["groq", "openai", "anthropic"]


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    provider: Provider
    display_name: str
    api_model_name: str
    temperature: float = 0.1
    is_free: bool = False


SUPPORTED_MODELS: dict[str, ModelSpec] = {
    "llama-3.3-70b-versatile": ModelSpec(
        model_id="llama-3.3-70b-versatile",
        provider="groq",
        display_name="Llama 3.3 70B (Groq, free)",
        api_model_name="llama-3.3-70b-versatile",
        is_free=True,
    ),
    "gpt-4o-mini": ModelSpec(
        model_id="gpt-4o-mini",
        provider="openai",
        display_name="GPT-4o Mini (OpenAI)",
        api_model_name="gpt-4o-mini",
    ),
    "gpt-4o": ModelSpec(
        model_id="gpt-4o",
        provider="openai",
        display_name="GPT-4o (OpenAI)",
        api_model_name="gpt-4o",
    ),
    "claude-sonnet-4-6": ModelSpec(
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        display_name="Claude Sonnet 4.6 (Anthropic)",
        api_model_name="claude-sonnet-4-6",
    ),
    "claude-haiku-4-5": ModelSpec(
        model_id="claude-haiku-4-5",
        provider="anthropic",
        display_name="Claude Haiku 4.5 (Anthropic)",
        api_model_name="claude-haiku-4-5-20251001",
    ),
}

DEFAULT_MODEL_ID = "llama-3.3-70b-versatile"


def get_model_spec(model_id: str) -> ModelSpec:
    return SUPPORTED_MODELS.get(model_id, SUPPORTED_MODELS[DEFAULT_MODEL_ID])
