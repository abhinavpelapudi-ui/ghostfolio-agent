# Ghostfolio AI Agent

AI-powered finance agent for portfolio analysis, built on [Ghostfolio](https://ghostfol.io) — an open-source wealth management platform.

## Features

- **8 Portfolio Tools**: Summary, performance, holding details, transactions, dividends, symbol search, market sentiment, trade entry
- **Multi-Model Support**: Groq (free), OpenAI, Anthropic — switchable from the UI
- **Verification Layer**: Numerical consistency checks, hallucination detection, risk threshold enforcement, automatic disclaimers
- **4-Stage Eval Framework**: Golden sets (15), labeled scenarios (40), LLM judge (groundedness), rubric scoring — 55+ test cases
- **Dual Observability**: LangSmith + Langfuse tracing with per-request cost tracking
- **User Feedback**: Thumbs up/down on every response, tied to trace IDs
- **Chat Persistence**: Conversation history survives page refreshes and new tabs

## Architecture

```
Browser (HTML/JS/CSS)
    │
    ▼
FastAPI (Python 3.11)
    ├── /chat/*     ← Chat UI routes (login, send, feedback, models)
    ├── /agent/*    ← Direct agent API
    ├── /health     ← Health check + provider status
    │
    ▼
LangGraph ReAct Agent
    ├── 8 Tools ──► Ghostfolio REST API
    ├── Verification Pipeline (numerical, hallucination, risk, disclaimer)
    └── Callbacks ──► LangSmith / Langfuse
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
# Clone
git clone https://github.com/abhinavpelapudi-ui/ghostfolio-agent.git
cd ghostfolio-agent

# Configure
cp .env.example .env
# Edit .env — set at minimum: GROQ_API_KEY

# Run
docker compose up -d

# Visit http://localhost:8080
```

### Local Development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for tests

# Start Ghostfolio (postgres + redis + ghostfolio)
docker compose up -d gf-postgres gf-redis ghostfolio

# Run the agent
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## Environment Variables

See [.env.example](.env.example) for all options. Required:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key (free tier) |
| `GHOSTFOLIO_URL` | Ghostfolio instance URL (default: `http://localhost:3333`) |

Optional: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGCHAIN_API_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`

## Evaluation

```bash
# Unit tests
pytest tests/ --ignore=tests/evals -v

# Golden sets (deterministic, no LLM cost)
pytest tests/evals/test_golden_sets.py -v

# Labeled scenarios
pytest tests/evals/test_scenarios.py -v

# LLM judge (requires GROQ_API_KEY)
pytest tests/evals/test_llm_judge.py -v

# Full suite with coverage
pytest tests/ --ignore=tests/evals -v --cov=app --cov-report=xml
```

## Deployment (Railway)

The project includes a `railway.toml` and `Dockerfile` for one-click Railway deployment:

1. Connect your GitHub repo to Railway
2. Set environment variables in Railway dashboard (same as `.env.example`)
3. Railway auto-detects the Dockerfile and deploys

The app listens on the `PORT` env variable (Railway sets this automatically).

## Tech Stack

- **Runtime**: Python 3.11, FastAPI, Uvicorn
- **Agent**: LangGraph (ReAct pattern), LangChain
- **LLM Providers**: Groq (Llama 3.3 70B), OpenAI (GPT-4o-mini, GPT-4o), Anthropic (Claude Haiku)
- **Observability**: LangSmith, Langfuse, custom cost tracker
- **Frontend**: Vanilla HTML/JS/CSS (no build step)
- **Testing**: pytest, respx (HTTP mocking), ruff (linting)

## Project Structure

```
app/
├── agent/          # LangGraph agent, tools, prompts, model registry
├── clients/        # Ghostfolio API client
├── models/         # Pydantic request/response schemas
├── routes/         # FastAPI routers (agent, chat, health)
├── tracing/        # LangSmith/Langfuse setup, cost tracker, feedback store
└── verification/   # Numerical consistency, hallucination, risk, disclaimer
static/             # Frontend HTML/JS/CSS
tests/
├── evals/          # Golden sets, scenarios, LLM judge, rubrics
├── test_tools.py   # Tool unit tests
└── test_ghostfolio_client.py  # API client tests
docs/               # Architecture docs, pre-search analysis
```

## License

MIT
