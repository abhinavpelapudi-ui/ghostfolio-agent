"""Tool: Get stock price trend for a day or week."""

import asyncio
import json

import yfinance as yf
from langchain_core.tools import tool

VALID_PERIODS = {"1d": ("1d", "5m"), "1w": ("5d", "1h")}


@tool
async def stock_trend(symbol: str, period: str = "1w") -> str:
    """Get stock price trend over a day or week with data points.
    Args:
        symbol: The ticker symbol (e.g., AAPL, MSFT, VOO)
        period: '1d' for intraday trend or '1w' for weekly trend (default: 1w)
    Returns price data points showing the trend, plus high/low/change summary.
    Use when user asks 'how has X trended this week' or 'show me the trend for X'."""
    try:
        period = period.lower()
        if period not in VALID_PERIODS:
            period = "1w"
        yf_period, yf_interval = VALID_PERIODS[period]

        ticker = yf.Ticker(symbol.upper())
        hist = await asyncio.to_thread(
            lambda: ticker.history(period=yf_period, interval=yf_interval)
        )

        if hist.empty:
            return json.dumps({"error": f"No data found for {symbol.upper()}", "symbol": symbol.upper()})

        data_points = []
        for timestamp, row in hist.iterrows():
            data_points.append({
                "datetime": timestamp.strftime("%Y-%m-%d %H:%M"),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        start_price = float(hist.iloc[0]["Close"])
        end_price = float(hist.iloc[-1]["Close"])
        change = end_price - start_price
        change_pct = (change / start_price) * 100 if start_price > 0 else 0

        result = {
            "symbol": symbol.upper(),
            "period": period,
            "start_price": round(start_price, 2),
            "end_price": round(end_price, 2),
            "high": round(float(hist["Close"].max()), 2),
            "low": round(float(hist["Close"].min()), 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "direction": "up" if change > 0 else "down" if change < 0 else "flat",
            "data_points_count": len(data_points),
            "data_points": data_points,
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol.upper()})
