"""Tool: Get current stock price from Yahoo Finance."""

import asyncio
import json

import yfinance as yf
from langchain_core.tools import tool


@tool
async def stock_price(symbol: str) -> str:
    """Get the current market price for a stock, ETF, or cryptocurrency.
    Args:
        symbol: The ticker symbol (e.g., AAPL, MSFT, VOO, BTC-USD)
    Returns current price, previous close, day change, and basic quote data.
    Use when user asks 'what is the price of X' or 'how much is X trading at'."""
    try:
        ticker = yf.Ticker(symbol.upper())
        info = await asyncio.to_thread(lambda: ticker.fast_info)

        last_price = float(info.get("lastPrice", 0))
        prev_close = float(info.get("previousClose", 0))

        result = {
            "symbol": symbol.upper(),
            "current_price": round(last_price, 2),
            "previous_close": round(prev_close, 2),
            "open": round(float(info.get("open", 0)), 2),
            "day_high": round(float(info.get("dayHigh", 0)), 2),
            "day_low": round(float(info.get("dayLow", 0)), 2),
            "currency": info.get("currency", "USD"),
        }

        if prev_close > 0:
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100
            result["day_change"] = round(change, 2)
            result["day_change_pct"] = round(change_pct, 2)

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol.upper()})
