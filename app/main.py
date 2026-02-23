"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.ghostfolio import ghostfolio_client
from app.routes.agent_routes import router as agent_router
from app.routes.health import router as health_router
from app.tracing.setup import init_tracing, shutdown_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing()
    yield
    shutdown_tracing()
    await ghostfolio_client.close()


app = FastAPI(
    title="Ghostfolio Finance AI Agent",
    version="0.1.0",
    description="AI agent for portfolio analysis powered by Ghostfolio",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(agent_router, prefix="/agent")
