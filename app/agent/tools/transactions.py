"""Tool: Get transaction/order history from the portfolio."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import ghostfolio_client


@tool
async def transactions(
    symbol: str = "",
    asset_class: str = "",
    take: int = 50,
    skip: int = 0,
) -> str:
    """Get transaction/order history from the portfolio.
    Can filter by symbol or asset class. Returns buy/sell orders with dates, quantities, prices.
    Use when user asks about their trades, purchase history, or when they bought/sold something."""
    params: dict = {"take": take, "skip": skip}
    if asset_class:
        params["assetClasses"] = asset_class

    try:
        orders_data = await ghostfolio_client.get_orders(**params)
        activities = orders_data if isinstance(orders_data, list) else orders_data.get("activities", [])

        if symbol:
            activities = [
                a for a in activities
                if a.get("SymbolProfile", {}).get("symbol", "").upper() == symbol.upper()
            ]

        result = {
            "total_count": len(activities),
            "showing": min(take, len(activities)),
            "transactions": [],
        }

        for act in activities[:take]:
            profile = act.get("SymbolProfile", {})
            result["transactions"].append({
                "date": act.get("date", ""),
                "type": act.get("type", ""),
                "symbol": profile.get("symbol", ""),
                "name": profile.get("name", ""),
                "quantity": act.get("quantity", 0),
                "unit_price": act.get("unitPrice", 0),
                "fee": act.get("fee", 0),
                "currency": profile.get("currency", ""),
                "account_name": act.get("Account", {}).get("name", ""),
            })

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
