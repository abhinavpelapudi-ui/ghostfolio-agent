# AI Cost Analysis — Ghostfolio Agent

## Model Pricing Table

| Model | Provider | Input (per 1M tokens) | Output (per 1M tokens) | Free Tier |
|-------|----------|-----------------------|------------------------|-----------|
| Llama 3.3 70B Versatile | Groq | $0.59 | $0.79 | Yes |
| GPT-4o-mini | OpenAI | $0.15 | $0.60 | No |
| GPT-4o | OpenAI | $2.50 | $10.00 | No |
| Claude Haiku 4.5 | Anthropic | $0.80 | $4.00 | No |

## Per-Query Token Usage

Based on observed usage patterns:

| Metric | Typical Value |
|--------|---------------|
| System prompt tokens | ~500 |
| User query tokens | ~50 |
| Tool call overhead | ~200 per tool |
| Average tools per query | 1.5 |
| Response tokens | ~400 |
| **Total input tokens** | **~1,000** |
| **Total output tokens** | **~500** |

## Per-Query Cost by Model

| Model | Input Cost | Output Cost | **Total per Query** |
|-------|-----------|-------------|---------------------|
| Llama 3.3 70B (Groq) | $0.000590 | $0.000395 | **$0.000985** |
| GPT-4o-mini | $0.000150 | $0.000300 | **$0.000450** |
| GPT-4o | $0.002500 | $0.005000 | **$0.007500** |
| Claude Haiku 4.5 | $0.000800 | $0.002000 | **$0.002800** |

Target: **<$0.01 per query** — all models meet this target.

## Development & Testing Spend

| Category | Cost |
|----------|------|
| Development queries (Groq free tier) | $0.00 |
| Eval suite runs (~55 test cases × ~5 runs) | $0.00 (mocked) |
| LLM Judge evals (Groq) | ~$0.27 |
| Manual testing (~100 queries) | ~$0.10 |
| **Total development cost** | **~$0.37** |

## Production Cost Projections

Assumptions:
- **5 queries per user per day**
- **30 days per month**
- **150 queries per user per month**
- Using Groq (Llama 3.3 70B) as default model

### Groq (Free Tier — Default)

| Monthly Users | Queries/Month | Cost/Month |
|---------------|---------------|------------|
| 100 | 15,000 | $14.78 |
| 1,000 | 150,000 | $147.75 |
| 10,000 | 1,500,000 | $1,477.50 |
| 100,000 | 15,000,000 | $14,775.00 |

Note: Groq free tier has rate limits (30 RPM, 14,400 RPD). At 100+ users, a paid plan is needed.

### GPT-4o-mini (Budget Paid Option)

| Monthly Users | Queries/Month | Cost/Month |
|---------------|---------------|------------|
| 100 | 15,000 | $6.75 |
| 1,000 | 150,000 | $67.50 |
| 10,000 | 1,500,000 | $675.00 |
| 100,000 | 15,000,000 | $6,750.00 |

### GPT-4o (Premium)

| Monthly Users | Queries/Month | Cost/Month |
|---------------|---------------|------------|
| 100 | 15,000 | $112.50 |
| 1,000 | 150,000 | $1,125.00 |
| 10,000 | 1,500,000 | $11,250.00 |
| 100,000 | 15,000,000 | $112,500.00 |

## Cost Optimization Strategies

1. **Default to Groq free tier** — $0 for low-volume usage
2. **Prompt engineering** — Keep system prompt concise (~500 tokens)
3. **Tool result truncation** — Cap tool outputs to essential fields
4. **Conversation window** — Sliding window of 18 messages prevents context bloat
5. **Model switching** — Let users pick cheaper models for simple queries
6. **Caching** — Frequently asked queries (e.g., portfolio summary) could be cached for 5 minutes

## Assumptions

- Token counts based on observed averages from development testing
- Pricing as of February 2026 from provider websites
- No caching or response deduplication in current implementation
- Groq free tier rate limits: 30 requests/minute, 14,400 requests/day
- Multi-tool queries (2-3 tools) approximately double the token usage
