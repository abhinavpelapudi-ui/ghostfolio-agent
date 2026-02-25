"""Tool: Get detailed information about a specific holding."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import get_client


@tool
async def holding_detail(symbol: str, data_source: str = "YAHOO") -> str:
    """Get detailed information about a specific holding in the portfolio.
    Args:
        symbol: The ticker symbol (e.g., AAPL, MSFT, VOO)
        data_source: Data source identifier, usually 'YAHOO' (default)
    Returns details including current value, quantity, average cost, performance,
    dividends, and sector information.
    Use when user asks about a specific stock or ETF they hold."""
    try:
        detail = await get_client().get_holding_detail(data_source, symbol.upper())
        result = {
            "symbol": symbol.upper(),
            "data_source": data_source,
            "name": detail.get("name", ""),
            "currency": detail.get("currency", "USD"),
            "market_price": detail.get("marketPrice", 0),
            "quantity": detail.get("quantity", 0),
            "value": detail.get("value", 0),
            "average_price": detail.get("averagePrice", 0),
            "investment": detail.get("investment", 0),
            "gross_performance": detail.get("grossPerformance", 0),
            "gross_performance_pct": round(detail.get("grossPerformancePercent", 0) * 100, 2),
            "net_performance": detail.get("netPerformance", 0),
            "net_performance_pct": round(detail.get("netPerformancePercent", 0) * 100, 2),
            "dividend": detail.get("dividend", 0),
            "first_buy_date": detail.get("firstBuyDate", ""),
            "asset_class": detail.get("assetClass", ""),
            "asset_sub_class": detail.get("assetSubClass", ""),
            "sectors": detail.get("sectors", []),
            "countries": detail.get("countries", []),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
