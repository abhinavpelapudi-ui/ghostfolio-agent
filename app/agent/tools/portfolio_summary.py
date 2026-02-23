"""Tool: Get portfolio summary with total value, allocations, and top holdings."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import ghostfolio_client


@tool
async def portfolio_summary() -> str:
    """Get a summary of the entire portfolio including total value, allocations by asset class,
    top holdings, and account breakdown. Use this when the user asks about their portfolio overview,
    total value, what they own, or asset allocation."""
    try:
        details = await ghostfolio_client.get_portfolio_details()
        summary = details.get("summary", {})
        holdings = details.get("holdings", [])

        result = {
            "total_value": summary.get("currentValue", 0),
            "total_investment": summary.get("totalInvestment", 0),
            "absolute_change": summary.get("absoluteChange", 0),
            "relative_change_pct": round((summary.get("relativeChange", 0)) * 100, 2),
            "currency": summary.get("currency", "USD"),
            "dividend_in_base_currency": summary.get("dividendInBaseCurrency", 0),
            "fees_in_base_currency": summary.get("feesInBaseCurrency", 0),
            "holdings_count": len(holdings) if isinstance(holdings, list) else 0,
            "top_holdings": [],
            "allocation_by_asset_class": {},
        }

        if isinstance(holdings, list):
            sorted_h = sorted(holdings, key=lambda h: h.get("value", 0), reverse=True)
            for h in sorted_h[:5]:
                result["top_holdings"].append({
                    "symbol": h.get("symbol", ""),
                    "name": h.get("name", ""),
                    "value": h.get("value", 0),
                    "weight_pct": round(h.get("allocationInPercentage", 0) * 100, 2),
                    "performance_pct": round(h.get("netPerformancePercentage", 0) * 100, 2),
                })

            for h in holdings:
                ac = h.get("assetClass", "UNKNOWN")
                result["allocation_by_asset_class"][ac] = (
                    result["allocation_by_asset_class"].get(ac, 0) + h.get("value", 0)
                )

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
