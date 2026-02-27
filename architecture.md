# Agent Architecture Document

**Project:** Ghostfolio Finance AI Agent
**Author:** Abhinav Pelapudi
**Date:** February 2026

---

## 1. Domain & Use Cases

**Domain:** Personal Wealth Management & Portfolio Tracking

The agent connects to [Ghostfolio](https://ghostfol.io), an open-source portfolio tracker, and provides conversational AI access to six core use cases:

1. **Portfolio Analysis** — total value, allocations, top holdings, cash position
2. **Risk Assessment** — concentration warnings, sector overweight, diversification scoring
3. **Transaction Insights** — trade history, dividend income, fee analysis
4. **Asset Research** — symbol lookup, current prices, holding details
5. **Allocation Optimization** — data-driven observations on portfolio composition
6. **Performance Comparison** — time-range returns (1d to max), gross/net performance

---

## 2. Agent Architecture

### Framework: LangGraph (ReAct Pattern)

The agent uses `langgraph.prebuilt.create_react_agent` — a single-agent ReAct loop that reasons about which tool to call, executes it, and iterates until it has enough information to respond.

**Why LangGraph over alternatives:**
- Built-in tool-use loop with configurable recursion limits
- First-class LangChain integration (models, callbacks, tracing)
- Deterministic graph execution (no multi-agent coordination overhead)
- Single-agent is sufficient — all tools query the same Ghostfolio API

### LLM Selection

| Model | Provider | Role | Cost |
|-------|----------|------|------|
| Llama 3.3 70B | Groq | Default (free tier) | ~$0.00 |
| GPT-4o-mini | OpenAI | Budget fallback | ~$0.0005/query |
| GPT-4o | OpenAI | Premium | ~$0.008/query |
| Claude Sonnet 4.6 | Anthropic | Premium | ~$0.003/query |
| Claude Haiku 4.5 | Anthropic | Fast fallback | ~$0.003/query |

Users select models from the UI. Temperature is fixed at 0.1 for deterministic financial responses.

### Tool Design (8 Tools)

**Portfolio Tools:**
- `portfolio_summary` — Total value, allocations by asset class, top 5 holdings
- `portfolio_performance` — Gross/net returns for configurable time ranges
- `holding_detail` — Deep dive on a single holding (cost basis, P&L, sectors, countries)

**Transaction Tools:**
- `transactions` — Order history with optional symbol/type filters
- `dividend_history` — Dividend payments for a specific holding

**Market Tools:**
- `symbol_search` — Ticker/name lookup across exchanges
- `market_sentiment` — Portfolio risk metrics, concentration flags, diversification score

**Action Tools:**
- `add_trade` — Execute BUY/SELL orders (auto-creates default account if needed)

### Request Flow

```
User Message
    |
    v
FastAPI (/chat/send) — authenticates per-user Ghostfolio token
    |
    v
LangGraph ReAct Agent — up to 10 iterations
    |-- Tool calls --> Ghostfolio REST API (per-user auth context)
    |-- LLM calls  --> Groq / OpenAI / Anthropic
    v
Verification Pipeline
    |-- Numerical consistency (cross-check $ and % vs tool data)
    |-- Hallucination detection (flag unknown tickers)
    |-- Risk threshold enforcement (>25% single holding, >60% top 3)
    |-- Disclaimer injection (auto-append on financial topics)
    v
Response + trace_id + tools_called + cost_usd
```

Conversation history: sliding window of last 18 messages, sent by the client and sliced on the backend.

---

## 3. Verification Strategy

Four automated checks run on every response:

| Check | What It Does | Why |
|-------|-------------|-----|
| **Numerical Consistency** | Extracts $ amounts and % from response, cross-checks against tool output data | Catches rounding errors or fabricated numbers |
| **Hallucination Detection** | Extracts ticker symbols from response, flags any not present in tool outputs | Prevents the agent from inventing holdings |
| **Risk Threshold Enforcement** | Flags single holding >25%, top 3 >60%, drawdown >20% | Domain requirement — users must be warned of concentration risk |
| **Disclaimer Injection** | Auto-appends financial disclaimer when response contains trigger words (return, risk, allocation, etc.) | Regulatory/liability requirement for financial content |

Results are returned in the `verification` field of every response and logged to traces.

---

## 4. Eval Results

**Framework:** 4-stage evaluation pipeline

| Stage | Test Cases | Method | Cost |
|-------|-----------|--------|------|
| Golden Sets | 15 | Deterministic (must_contain / must_not_contain) | $0 (mocked) |
| Labeled Scenarios | 40 | Category-tagged coverage mapping | $0 (mocked) |
| LLM Judge | Per-case | Groundedness scoring (claim-by-claim) | ~$0.005/case |
| Rubric Scoring | Per-case | Weighted 4-dimension rubric (relevance, accuracy, completeness, clarity) | ~$0.005/case |

**Coverage:** 55 total test cases — 21 happy path, 12 edge cases, 11 adversarial, 6 ambiguous, 5 multi-tool

**Key pass rates (from golden set + scenario runs):**
- Tool selection accuracy: >95%
- Content validation: >90%
- Adversarial refusal rate: 100% (all 10 adversarial cases correctly refused)
- Hallucination detection: 100% (gs-015 anti-hallucination case passes)

---

## 5. Observability Setup

**Dual tracing:** LangSmith (primary) + Langfuse (secondary)

| What's Tracked | Where |
|---------------|-------|
| Full request → reasoning → tool calls → response | LangSmith traces |
| Per-request token usage (input/output) | Cost tracker (in-memory + `/agent/costs` endpoint) |
| Per-request cost in USD | Returned in every response (`cost_usd` field) |
| User feedback (thumbs up/down) | Feedback store + `/chat/feedback/summary` endpoint |
| Verification results | Returned in every response (`verification` field) |
| Error rates | Structured logging (Python `logging` module) |

**Cost tracking:** Model pricing table with per-token costs for all 5 supported models. Each response includes `cost_usd`. Aggregate stats available at `GET /agent/costs`.

---

## 6. Open Source Contribution

- **Repository:** [github.com/abhinavpelapudi-ui/ghostfolio-agent](https://github.com/abhinavpelapudi-ui/ghostfolio-agent) (MIT License)
- **What's released:**
  - Full agent implementation with 8 tools, verification pipeline, and eval framework
  - 55-case evaluation dataset (YAML-driven golden sets + labeled scenarios + rubrics)
  - LLM Judge implementation for groundedness and rubric scoring
  - Docker Compose stack for self-hosted Ghostfolio + AI agent
  - Cost analysis with production projections
- **PyPI package:** Configured in `pyproject.toml` as `ghostfolio-agent` v0.1.0
