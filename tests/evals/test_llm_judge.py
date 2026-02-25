"""Stage 3+4: LLM Judge Evals — groundedness and rubric scoring.

These require API keys and cost tokens. Run before shipping, not every commit.

Usage:
    # Requires GROQ_API_KEY in environment
    pytest tests/evals/test_llm_judge.py -v --timeout=120

    # Skip if no API key
    pytest tests/evals/test_llm_judge.py -v  # auto-skips via conftest
"""

import os

import pytest

# Skip entire module if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping LLM judge evals",
)


@pytest.mark.asyncio
async def test_groundedness_pass():
    """Agent response grounded in tool output should score high."""
    from tests.evals.llm_judge import judge_groundedness

    tool_output = [
        '{"total_value": 125000.50, "holdings_count": 4, "top_holdings": [{"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "value": 50000}]}'
    ]
    response = "Your portfolio is worth $125,000.50 with 4 holdings. Your top holding is VOO (Vanguard S&P 500 ETF) valued at $50,000."

    result = await judge_groundedness(response, tool_output)
    assert result.groundedness_score >= 0.8
    assert result.overall_grounded is True


@pytest.mark.asyncio
async def test_groundedness_fail():
    """Agent response with fabricated numbers should be flagged."""
    from tests.evals.llm_judge import judge_groundedness

    tool_output = [
        '{"total_value": 125000.50, "holdings_count": 4}'
    ]
    response = "Your portfolio is worth $500,000 with 15 holdings. You're doing great!"

    result = await judge_groundedness(response, tool_output)
    assert result.overall_grounded is False


@pytest.mark.asyncio
async def test_rubric_high_quality():
    """High-quality response should score well on rubric."""
    from tests.evals.llm_judge import judge_rubric

    query = "Show me my portfolio summary"
    tool_output = [
        '{"total_value": 125000.50, "holdings_count": 4, "top_holdings": [{"symbol": "VOO", "value": 50000, "weight_pct": 40.0}], "net_performance_pct": 25.0}'
    ]
    response = """Here's your portfolio summary:

- **Total Value**: $125,000.50
- **Holdings**: 4 positions
- **Net Performance**: +25.00%

**Top Holding**: VOO (Vanguard S&P 500 ETF) at 40.0% ($50,000)

---
*Disclaimer: This information is for educational purposes only and does not constitute financial advice.*"""

    result = await judge_rubric(query, response, tool_output)
    assert result.weighted_score >= 3.5
    assert result.quality_level in ("excellent", "good")


@pytest.mark.asyncio
async def test_rubric_low_quality():
    """Poor response should score low on rubric."""
    from tests.evals.llm_judge import judge_rubric

    query = "Show me my portfolio summary"
    tool_output = [
        '{"total_value": 125000.50, "holdings_count": 4}'
    ]
    response = "I think your portfolio might be worth something. Try checking later."

    result = await judge_rubric(query, response, tool_output)
    assert result.weighted_score < 3.0
    assert result.quality_level in ("poor", "critical", "acceptable")
