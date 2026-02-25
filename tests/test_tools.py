"""Test individual tool output structure against mock Ghostfolio data."""

import json

import pytest


def _setup():
    from app.clients.ghostfolio import ghostfolio_client
    ghostfolio_client._base_url = "http://localhost:3333"
    ghostfolio_client._access_token = "test-token"
    ghostfolio_client._bearer_token = None


@pytest.mark.asyncio
async def test_portfolio_summary_tool(mock_ghostfolio):
    _setup()
    from app.agent.tools.portfolio_summary import portfolio_summary

    result = json.loads(await portfolio_summary.ainvoke({}))
    assert result["total_value"] == 125000.50
    assert result["holdings_count"] == 4
    assert len(result["top_holdings"]) > 0
    assert result["top_holdings"][0]["symbol"] == "VOO"


@pytest.mark.asyncio
async def test_portfolio_performance_tool(mock_ghostfolio):
    _setup()
    from app.agent.tools.portfolio_performance import portfolio_performance

    result = json.loads(await portfolio_performance.ainvoke({"date_range": "max"}))
    assert result["date_range"] == "max"
    assert result["net_performance"] == 25000.50


@pytest.mark.asyncio
async def test_holding_detail_tool(mock_ghostfolio):
    _setup()
    from app.agent.tools.holding_detail import holding_detail

    result = json.loads(await holding_detail.ainvoke({"symbol": "AAPL"}))
    assert result["name"] == "Apple Inc."
    assert result["quantity"] == 153.4


@pytest.mark.asyncio
async def test_transactions_tool(mock_ghostfolio):
    _setup()
    from app.agent.tools.transactions import transactions

    result = json.loads(await transactions.ainvoke({}))
    assert result["total_count"] == 3
    symbols = [t["symbol"] for t in result["transactions"]]
    assert "AAPL" in symbols
    assert "VOO" in symbols


@pytest.mark.asyncio
async def test_market_sentiment_tool(mock_ghostfolio):
    _setup()
    from app.agent.tools.market_sentiment import market_sentiment

    result = json.loads(await market_sentiment.ainvoke({}))
    assert result["holdings_count"] == 4
    assert "Technology" in result["sector_allocation"]


@pytest.mark.asyncio
async def test_add_trade_tool(mock_ghostfolio):
    _setup()
    from app.agent.tools.add_trade import add_trade

    result = json.loads(await add_trade.ainvoke({
        "symbol": "TSLA", "quantity": 5, "unit_price": 250,
    }))
    assert result["success"] is True
    assert result["trade"]["symbol"] == "TSLA"
