"""Tool: Add a buy or sell trade to the portfolio."""

import json
from datetime import datetime, timezone

from langchain_core.tools import tool

from app.clients.ghostfolio import get_client


@tool
async def add_trade(
    symbol: str,
    quantity: float,
    unit_price: float,
    trade_type: str = "BUY",
    currency: str = "USD",
    date: str = "",
    fee: float = 0,
    data_source: str = "YAHOO",
) -> str:
    """Add a buy or sell trade to the portfolio.
    Args:
        symbol: Ticker symbol (e.g., AAPL, VOO, MSFT, BTC-USD)
        quantity: Number of shares/units
        unit_price: Price per share/unit at time of purchase
        trade_type: 'BUY' or 'SELL' (default: BUY)
        currency: Currency code (default: USD)
        date: Trade date in YYYY-MM-DD format (default: today)
        fee: Transaction fee (default: 0)
        data_source: Data source for the symbol (default: YAHOO)
    Use when user says they bought or sold a stock, ETF, or crypto.
    Examples: "I bought 10 shares of AAPL at $230", "Add a purchase of 5 VOO at $520"."""
    try:
        # Validate trade type
        trade_type = trade_type.upper()
        if trade_type not in ("BUY", "SELL"):
            return json.dumps({"error": "trade_type must be 'BUY' or 'SELL'"})

        if quantity <= 0:
            return json.dumps({"error": "quantity must be greater than 0"})

        if unit_price <= 0:
            return json.dumps({"error": "unit_price must be greater than 0"})

        # Default to today if no date provided
        if not date:
            trade_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00.000Z")
        else:
            trade_date = f"{date}T00:00:00.000Z"

        # Get the user's first account
        accounts_data = await get_client().get_accounts()
        accounts = accounts_data.get("accounts", [])
        if not accounts:
            return json.dumps({"error": "No accounts found. Please create an account in Ghostfolio first."})
        account_id = accounts[0]["id"]

        order = {
            "accountId": account_id,
            "currency": currency.upper(),
            "dataSource": data_source,
            "date": trade_date,
            "fee": fee,
            "quantity": quantity,
            "symbol": symbol.upper(),
            "type": trade_type,
            "unitPrice": unit_price,
        }

        result = await get_client().create_order(order)

        total_cost = quantity * unit_price + fee
        return json.dumps({
            "success": True,
            "trade": {
                "id": result.get("id", ""),
                "type": trade_type,
                "symbol": symbol.upper(),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_cost": round(total_cost, 2),
                "fee": fee,
                "currency": currency.upper(),
                "date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "account": accounts[0].get("name", ""),
            },
            "message": f"Successfully added {trade_type} of {quantity} {symbol.upper()} at ${unit_price} (total: ${total_cost:.2f})",
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
