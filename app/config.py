from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Ghostfolio
    ghostfolio_url: str = "http://localhost:3333"
    ghostfolio_access_token: str = ""

    # LLM Providers
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"
    langchain_project: str = "ghostfolio-agent"

    # Langfuse
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://us.cloud.langfuse.com"

    # Agent
    default_llm_provider: str = "groq"
    max_agent_iterations: int = Field(default=10, ge=1, le=50)
    log_level: str = "INFO"
    agent_api_key: str = ""  # If empty, falls back to ghostfolio_access_token


settings = Settings()
