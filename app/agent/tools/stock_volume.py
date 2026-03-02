"""Tool: Get trading volume data for a stock."""

import asyncio
import json

import yfinance as yf
from langchain_core.tools import tool


@tool
async def stock_volume(symbol: str, period: str = "1w") -> str:
    """Get trading volume data for a stock including recent volume and average.
    Args:
        symbol: The ticker symbol (e.g., AAPL, MSFT, VOO)
        period: '1d' for today's volume or '1w' for this week's volume (default: 1w)
    Returns daily volume figures, average volume, and volume trend.
    Use when user asks about buy volume, sell volume, trading volume, or activity for a stock."""
    try:
        valid_periods = {"1d": "1d", "1w": "5d"}
        yf_period = valid_periods.get(period.lower(), "5d")
        display_period = period.lower() if period.lower() in valid_periods else "1w"

        ticker = yf.Ticker(symbol.upper())
        hist = await asyncio.to_thread(
            lambda: ticker.history(period=yf_period)
        )

        if hist.empty:
            return json.dumps({"error": f"No data found for {symbol.upper()}", "symbol": symbol.upper()})

        daily_volumes = []
        for timestamp, row in hist.iterrows():
            close_price = float(row["Close"])
            open_price = float(row["Open"])
            volume = int(row["Volume"])
            daily_volumes.append({
                "date": timestamp.strftime("%Y-%m-%d"),
                "volume": volume,
                "close": round(close_price, 2),
                "price_direction": "up" if close_price >= open_price else "down",
            })

        total_volume = sum(d["volume"] for d in daily_volumes)
        avg_volume = total_volume // len(daily_volumes) if daily_volumes else 0

        # Get 30-day average for comparison
        hist_30d = await asyncio.to_thread(
            lambda: ticker.history(period="1mo")
        )
        avg_30d_volume = int(hist_30d["Volume"].mean()) if not hist_30d.empty else 0

        latest = daily_volumes[-1] if daily_volumes else {}
        volume_vs_avg = ""
        if avg_30d_volume > 0 and latest.get("volume", 0) > 0:
            ratio = latest["volume"] / avg_30d_volume
            if ratio > 1.5:
                volume_vs_avg = "significantly above average"
            elif ratio > 1.1:
                volume_vs_avg = "above average"
            elif ratio < 0.5:
                volume_vs_avg = "significantly below average"
            elif ratio < 0.9:
                volume_vs_avg = "below average"
            else:
                volume_vs_avg = "near average"

        result = {
            "symbol": symbol.upper(),
            "period": display_period,
            "latest_volume": latest.get("volume", 0),
            "latest_date": latest.get("date", ""),
            "average_volume_period": avg_volume,
            "average_volume_30d": avg_30d_volume,
            "volume_assessment": volume_vs_avg,
            "total_volume": total_volume,
            "daily_breakdown": daily_volumes,
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "symbol": symbol.upper()})
