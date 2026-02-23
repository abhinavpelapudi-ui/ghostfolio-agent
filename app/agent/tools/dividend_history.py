"""Tool: Get dividend payment history for a specific holding."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import ghostfolio_client


@tool
async def dividend_history(symbol: str, data_source: str = "YAHOO") -> str:
    """Get dividend payment history for a specific holding.
    Returns chronological list of dividend payments with amounts and dates.
    Use when user asks about dividends received from a stock or ETF."""
    try:
        data = await ghostfolio_client.get_dividends(data_source, symbol.upper())
        dividends = data if isinstance(data, list) else data.get("dividends", [])

        total = sum(d.get("amount", 0) for d in dividends)

        result = {
            "symbol": symbol.upper(),
            "data_source": data_source,
            "total_dividends_received": round(total, 2),
            "payment_count": len(dividends),
            "payments": [
                {"date": d.get("date", ""), "amount": d.get("amount", 0)}
                for d in dividends
            ],
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
