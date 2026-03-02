"""Tool: Add a buy or sell trade to the portfolio (two-phase confirmation)."""

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
    confirmed: bool = False,
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
        confirmed: MUST be True to execute. First call with False to preview, then True to execute.
    IMPORTANT: You MUST call this tool TWICE for every trade:
    1. First call with confirmed=False — returns a preview for the user to approve.
    2. After the user confirms, call again with confirmed=True to actually execute the trade.
    NEVER set confirmed=True on the first call. Always show the preview first and ask the user to confirm."""
    try:
        # Validate trade type
        trade_type = trade_type.upper()
        if trade_type not in ("BUY", "SELL"):
            return json.dumps({"error": "trade_type must be 'BUY' or 'SELL'"})

        if quantity <= 0:
            return json.dumps({"error": "quantity must be greater than 0"})

        if unit_price <= 0:
            return json.dumps({"error": "unit_price must be greater than 0"})

        trade_date_display = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total_cost = quantity * unit_price + fee

        # Phase 1: Preview — do NOT execute, return summary for user confirmation
        if not confirmed:
            return json.dumps({
                "pending_confirmation": True,
                "preview": {
                    "type": trade_type,
                    "symbol": symbol.upper(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_cost": round(total_cost, 2),
                    "fee": fee,
                    "currency": currency.upper(),
                    "date": trade_date_display,
                    "data_source": data_source,
                },
                "message": (
                    f"Please confirm this trade:\n"
                    f"  {trade_type} {quantity} x {symbol.upper()} @ ${unit_price:.2f}\n"
                    f"  Total: ${total_cost:.2f} (fee: ${fee:.2f})\n"
                    f"  Date: {trade_date_display}\n\n"
                    f"Reply 'yes' or 'confirm' to execute this trade."
                ),
            }, indent=2)

        # Phase 2: Confirmed — execute the trade
        if not date:
            trade_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00.000Z")
        else:
            trade_date = f"{date}T00:00:00.000Z"

        # Get the user's first account (auto-create if none exist)
        client = get_client()
        accounts_data = await client.get_accounts()
        accounts = accounts_data.get("accounts", [])
        if not accounts:
            new_account = await client.create_account(name="Default", currency=currency.upper())
            account_id = new_account["id"]
            accounts = [new_account]
        else:
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
                "date": trade_date_display,
                "account": accounts[0].get("name", ""),
            },
            "message": (
                f"Successfully added {trade_type} of {quantity} "
                f"{symbol.upper()} at ${unit_price} (total: ${total_cost:.2f})"
            ),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
