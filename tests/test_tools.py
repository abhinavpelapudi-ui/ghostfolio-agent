"""Test individual tool output structure against mock Ghostfolio data."""

import json


async def test_portfolio_summary_tool(mock_ghostfolio):
    from app.agent.tools.portfolio_summary import portfolio_summary

    # Override the client's base URL for testing
    from app.clients.ghostfolio import ghostfolio_client
    ghostfolio_client._base_url = "http://localhost:3333"
    ghostfolio_client._access_token = "test-token"
    ghostfolio_client._bearer_token = None

    result = json.loads(await portfolio_summary.ainvoke({}))
    assert result["total_value"] == 125000.50
    assert result["currency"] == "USD"
    assert len(result["top_holdings"]) > 0
    assert result["top_holdings"][0]["symbol"] == "VOO"


async def test_portfolio_performance_tool(mock_ghostfolio):
    from app.agent.tools.portfolio_performance import portfolio_performance
    from app.clients.ghostfolio import ghostfolio_client
    ghostfolio_client._base_url = "http://localhost:3333"
    ghostfolio_client._access_token = "test-token"
    ghostfolio_client._bearer_token = None

    result = json.loads(await portfolio_performance.ainvoke({"date_range": "max"}))
    assert result["date_range"] == "max"
    assert result["current_net_performance"] == 25000.50


async def test_holding_detail_tool(mock_ghostfolio):
    from app.agent.tools.holding_detail import holding_detail
    from app.clients.ghostfolio import ghostfolio_client
    ghostfolio_client._base_url = "http://localhost:3333"
    ghostfolio_client._access_token = "test-token"
    ghostfolio_client._bearer_token = None

    result = json.loads(await holding_detail.ainvoke({"symbol": "AAPL"}))
    assert result["name"] == "Apple Inc."
    assert result["quantity"] == 153.4
