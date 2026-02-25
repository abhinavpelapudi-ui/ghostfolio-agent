"""Stage 1: Golden Set Evals — deterministic, binary, no LLM needed.

Run after every commit. If these fail, something is fundamentally broken.
Zero API cost. Zero ambiguity.

Usage:
    pytest tests/evals/test_golden_sets.py -v
"""

import json
import os
from pathlib import Path

import pytest
import yaml

from tests.evals.evaluator import EvalResult, evaluate_case

GOLDEN_DATA_PATH = Path(__file__).parent / "golden_data.yaml"


def load_golden_cases() -> list[dict]:
    with open(GOLDEN_DATA_PATH) as f:
        return yaml.safe_load(f)


GOLDEN_CASES = load_golden_cases()


def _setup_mock_client():
    """Point the ghostfolio client at the mock server."""
    from app.clients.ghostfolio import ghostfolio_client

    ghostfolio_client._base_url = "http://localhost:3333"
    ghostfolio_client._access_token = "test-token"
    ghostfolio_client._bearer_token = None


async def _run_tool_and_collect(query: str, mock_ghostfolio) -> dict:
    """Run the agent's tools against mock data and collect response + tools called.

    Instead of running the full LLM agent (which would require API keys),
    we test tool invocation directly based on expected tool mapping.
    This keeps golden sets deterministic and free.
    """
    _setup_mock_client()

    from app.agent.tools import ALL_TOOLS

    tool_map = {t.name: t for t in ALL_TOOLS}
    return tool_map


# ── Parametrized Golden Set Tests ────────────────────────────────

@pytest.fixture
def setup_client(mock_ghostfolio):
    _setup_mock_client()


class TestGoldenSetTools:
    """Test that each tool returns correct data against mock API."""

    @pytest.mark.asyncio
    async def test_gs001_portfolio_summary(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.portfolio_summary import portfolio_summary

        result = json.loads(await portfolio_summary.ainvoke({}))
        assert result["total_value"] == 125000.50
        assert result["holdings_count"] == 4
        assert result["top_holdings"][0]["symbol"] == "VOO"

    @pytest.mark.asyncio
    async def test_gs004_portfolio_performance(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.portfolio_performance import portfolio_performance

        result = json.loads(await portfolio_performance.ainvoke({"date_range": "max"}))
        assert result["date_range"] == "max"
        assert result["net_performance"] == 25000.50

    @pytest.mark.asyncio
    async def test_gs006_holding_detail(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.holding_detail import holding_detail

        result = json.loads(await holding_detail.ainvoke({"symbol": "AAPL"}))
        assert result["name"] == "Apple Inc."
        assert result["quantity"] == 153.4

    @pytest.mark.asyncio
    async def test_gs008_transactions(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.transactions import transactions

        result = json.loads(await transactions.ainvoke({}))
        assert result["total_count"] >= 2
        symbols = [t["symbol"] for t in result["transactions"]]
        assert "AAPL" in symbols

    @pytest.mark.asyncio
    async def test_gs010_dividend_history(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.dividend_history import dividend_history

        result = json.loads(await dividend_history.ainvoke({"symbol": "VOO"}))
        assert len(result["payments"]) == 4
        assert result["total_dividends_received"] == 630.00

    @pytest.mark.asyncio
    async def test_gs011_symbol_search(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.symbol_search import symbol_search

        result = json.loads(await symbol_search.ainvoke({"query": "Apple"}))
        symbols = [r["symbol"] for r in result["results"]]
        assert "AAPL" in symbols

    @pytest.mark.asyncio
    async def test_gs012_market_sentiment(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.market_sentiment import market_sentiment

        result = json.loads(await market_sentiment.ainvoke({}))
        assert result["holdings_count"] == 4
        assert "Technology" in result["sector_allocation"]

    @pytest.mark.asyncio
    async def test_gs013_add_trade(self, mock_ghostfolio):
        _setup_mock_client()
        from app.agent.tools.add_trade import add_trade

        result = json.loads(await add_trade.ainvoke({
            "symbol": "TSLA",
            "quantity": 5,
            "unit_price": 250,
            "trade_type": "BUY",
        }))
        assert result["success"] is True
        assert result["trade"]["symbol"] == "TSLA"
        assert result["trade"]["quantity"] == 5


class TestGoldenSetEvaluator:
    """Test the evaluator logic itself against known inputs."""

    def test_all_checks_pass(self):
        case = {
            "id": "test-pass",
            "expected_tools": ["portfolio_summary"],
            "must_contain": ["125,000", "VOO"],
            "must_not_contain": ["I don't know"],
        }
        result = evaluate_case(
            case=case,
            response_text="Your portfolio is worth $125,000 with top holding VOO.",
            tools_called=["portfolio_summary"],
        )
        assert result.passed
        assert result.tool_check_passed
        assert result.content_check_passed
        assert result.negative_check_passed

    def test_tool_selection_fails(self):
        case = {
            "id": "test-tool-fail",
            "expected_tools": ["portfolio_summary"],
            "must_contain": [],
            "must_not_contain": [],
        }
        result = evaluate_case(
            case=case,
            response_text="Here is your data.",
            tools_called=["holding_detail"],
        )
        assert not result.passed
        assert not result.tool_check_passed

    def test_content_validation_fails(self):
        case = {
            "id": "test-content-fail",
            "expected_tools": [],
            "must_contain": ["125,000"],
            "must_not_contain": [],
        }
        result = evaluate_case(
            case=case,
            response_text="Your portfolio is doing great!",
            tools_called=[],
        )
        assert not result.passed
        assert not result.content_check_passed

    def test_negative_validation_fails(self):
        case = {
            "id": "test-negative-fail",
            "expected_tools": [],
            "must_contain": [],
            "must_not_contain": ["I don't know"],
        }
        result = evaluate_case(
            case=case,
            response_text="I don't know what your portfolio looks like.",
            tools_called=[],
        )
        assert not result.passed
        assert not result.negative_check_passed

    def test_contain_any_passes(self):
        case = {
            "id": "test-any-pass",
            "expected_tools": [],
            "must_contain_any": ["disclaimer", "not financial advice"],
        }
        result = evaluate_case(
            case=case,
            response_text="This is not financial advice.",
            tools_called=[],
        )
        assert result.passed
        assert result.contain_any_check_passed

    def test_contain_any_fails(self):
        case = {
            "id": "test-any-fail",
            "expected_tools": [],
            "must_contain_any": ["disclaimer", "not financial advice"],
        }
        result = evaluate_case(
            case=case,
            response_text="Buy everything!",
            tools_called=[],
        )
        assert not result.passed
        assert not result.contain_any_check_passed

    def test_adversarial_no_advice(self):
        """Agent must NOT give investment advice."""
        case = {
            "id": "test-adversarial",
            "expected_tools": [],
            "must_not_contain": ["you should buy", "I recommend buying"],
            "must_contain_any": ["not financial advice", "disclaimer", "cannot provide"],
        }
        result = evaluate_case(
            case=case,
            response_text="I cannot provide investment recommendations. This is not financial advice.",
            tools_called=[],
        )
        assert result.passed
