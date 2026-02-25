"""Tool: Get portfolio performance metrics for a given time range."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import get_client

VALID_RANGES = {"1d", "1w", "1m", "3m", "6m", "ytd", "1y", "3y", "5y", "max"}


@tool
async def portfolio_performance(date_range: str = "max") -> str:
    """Get portfolio performance metrics for a given time range.
    Supported ranges: 1d, 1w, 1m, 3m, 6m, ytd, 1y, 3y, 5y, max.
    Returns absolute return, percentage return, and performance chart data.
    Use when user asks about returns, gains, losses, or how the portfolio performed."""
    if date_range not in VALID_RANGES:
        date_range = "max"

    try:
        data = await get_client().get_portfolio_performance(date_range=date_range)
        perf = data.get("performance", {})
        chart = data.get("chart", [])

        result = {
            "date_range": date_range,
            "net_performance": perf.get("netPerformance", 0),
            "net_performance_pct": round(perf.get("netPerformancePercentage", 0) * 100, 2),
            "total_investment": perf.get("totalInvestment", 0),
            "current_value": perf.get("currentValueInBaseCurrency", 0),
            "current_net_worth": perf.get("currentNetWorth", 0),
            "chart_points": len(chart),
            "first_date": chart[0].get("date", "") if chart else "",
            "last_date": chart[-1].get("date", "") if chart else "",
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
