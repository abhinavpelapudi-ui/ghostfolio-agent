"""Initialize LangSmith and Langfuse tracing."""

import logging
import os
import threading

from langfuse import Langfuse

from app.config import settings

logger = logging.getLogger(__name__)

langfuse_client: Langfuse | None = None
_tracing_lock = threading.Lock()


def init_tracing() -> None:
    global langfuse_client

    # LangSmith: auto-traced by LangChain when env vars are set
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        logger.info("LangSmith tracing enabled (project: %s)", settings.langchain_project)
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info("LangSmith tracing disabled — LANGCHAIN_API_KEY not set")

    # Langfuse: explicit client for callback handler
    if settings.langfuse_secret_key and settings.langfuse_public_key:
        with _tracing_lock:
            langfuse_client = Langfuse(
                secret_key=settings.langfuse_secret_key,
                public_key=settings.langfuse_public_key,
                host=settings.langfuse_host,
            )
        logger.info("Langfuse tracing enabled (host: %s)", settings.langfuse_host)
    else:
        logger.warning("Langfuse tracing disabled — keys not set")


def shutdown_tracing() -> None:
    global langfuse_client
    with _tracing_lock:
        if langfuse_client:
            langfuse_client.flush()
            langfuse_client.shutdown()
            langfuse_client = None


def get_langfuse_handler():
    if not settings.langfuse_secret_key or not settings.langfuse_public_key:
        return None

    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:
            logger.warning("Langfuse callback handler not available")
            return None

    try:
        return CallbackHandler(
            secret_key=settings.langfuse_secret_key,
            public_key=settings.langfuse_public_key,
            host=settings.langfuse_host,
        )
    except TypeError:
        return CallbackHandler()
