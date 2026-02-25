"""Tool: Search for a stock, ETF, or fund symbol by name or ticker."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import get_client


@tool
async def symbol_search(query: str) -> str:
    """Search for a stock, ETF, or fund symbol by name or ticker.
    Returns matching symbols with their data source, name, and asset type.
    Use when user mentions a company name and you need to resolve the ticker symbol,
    or when they want to look up a specific investment."""
    try:
        data = await get_client().lookup_symbol(query)
        items = data.get("items", [])

        result = {
            "query": query,
            "results_count": len(items),
            "results": [
                {
                    "symbol": item.get("symbol", ""),
                    "name": item.get("name", ""),
                    "data_source": item.get("dataSource", ""),
                    "asset_class": item.get("assetClass", ""),
                    "asset_sub_class": item.get("assetSubClass", ""),
                    "currency": item.get("currency", ""),
                }
                for item in items[:10]
            ],
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
