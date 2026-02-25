"""Tool: Get portfolio summary with total value, allocations, and top holdings."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import get_client


@tool
async def portfolio_summary() -> str:
    """Get a summary of the entire portfolio including total value, allocations by asset class,
    top holdings, and account breakdown. Use this when the user asks about their portfolio overview,
    total value, what they own, or asset allocation."""
    try:
        details = await get_client().get_portfolio_details()
        summary = details.get("summary", {})
        holdings_raw = details.get("holdings", {})

        # holdings is a dict keyed by symbol, convert to list
        if isinstance(holdings_raw, dict):
            holdings = list(holdings_raw.values())
        else:
            holdings = holdings_raw or []

        result = {
            "total_value": summary.get("currentValueInBaseCurrency", 0),
            "total_investment": summary.get("totalInvestment", 0),
            "net_performance": summary.get("netPerformance", 0),
            "net_performance_pct": round(summary.get("netPerformancePercentage", 0) * 100, 2),
            "gross_performance": summary.get("grossPerformance", 0),
            "annualized_return_pct": round(summary.get("annualizedPerformancePercent", 0) * 100, 2),
            "dividend_in_base_currency": summary.get("dividendInBaseCurrency", 0),
            "fees": summary.get("fees", 0),
            "cash": summary.get("cash", 0),
            "holdings_count": len(holdings),
            "top_holdings": [],
            "allocation_by_asset_class": {},
        }

        sorted_h = sorted(holdings, key=lambda h: h.get("valueInBaseCurrency", 0), reverse=True)
        for h in sorted_h[:5]:
            result["top_holdings"].append({
                "symbol": h.get("symbol", ""),
                "name": h.get("name", ""),
                "value": h.get("valueInBaseCurrency", 0),
                "weight_pct": round(h.get("allocationInPercentage", 0) * 100, 2),
                "performance_pct": round(h.get("netPerformancePercent", 0) * 100, 2),
            })

        for h in holdings:
            ac = h.get("assetClass", "UNKNOWN")
            result["allocation_by_asset_class"][ac] = round(
                result["allocation_by_asset_class"].get(ac, 0) + h.get("valueInBaseCurrency", 0), 2
            )

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
