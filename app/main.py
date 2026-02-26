"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.clients.ghostfolio import ghostfolio_client
from app.routes.agent_routes import router as agent_router
from app.routes.chat_routes import router as chat_router
from app.routes.health import router as health_router
from app.tracing.setup import init_tracing, shutdown_tracing

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


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
app.include_router(chat_router, prefix="/chat")


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


# Mount static files last so API routes take priority
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
