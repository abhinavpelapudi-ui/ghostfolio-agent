"""Tool: Get overall market performance by sector."""

import asyncio
import json

import yfinance as yf
from langchain_core.tools import tool

# SPDR sector ETFs — standard proxy for S&P 500 sector performance
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}


@tool
async def sector_performance(period: str = "1w") -> str:
    """Get overall market trend by sector using sector ETFs.
    Args:
        period: Time period — '1d' for today, '1w' for this week, '1m' for this month (default: 1w)
    Returns performance of each major market sector (Technology, Healthcare, etc.).
    Use when user asks 'how is the market doing', 'sector performance', or 'which sectors are up'."""
    try:
        valid_periods = {"1d": "1d", "1w": "5d", "1m": "1mo"}
        yf_period = valid_periods.get(period.lower(), "5d")
        display_period = period.lower() if period.lower() in valid_periods else "1w"

        def fetch_all():
            results = {}
            tickers = yf.Tickers(" ".join(SECTOR_ETFS.values()))
            for sector_name, etf_symbol in SECTOR_ETFS.items():
                try:
                    hist = tickers.tickers[etf_symbol].history(period=yf_period)
                    if not hist.empty:
                        start = float(hist.iloc[0]["Close"])
                        end = float(hist.iloc[-1]["Close"])
                        change_pct = ((end - start) / start) * 100 if start > 0 else 0
                        results[sector_name] = {
                            "etf": etf_symbol,
                            "current_price": round(end, 2),
                            "change_pct": round(change_pct, 2),
                            "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
                        }
                except Exception:
                    results[sector_name] = {"etf": etf_symbol, "error": "data unavailable"}
            return results

        sectors = await asyncio.to_thread(fetch_all)

        # Sort by performance
        sorted_sectors = dict(
            sorted(sectors.items(), key=lambda x: x[1].get("change_pct", 0), reverse=True)
        )

        valid = [(k, v) for k, v in sorted_sectors.items() if "change_pct" in v]
        best = valid[0] if valid else None
        worst = valid[-1] if valid else None

        result = {
            "period": display_period,
            "sectors": sorted_sectors,
            "best_sector": {"name": best[0], **best[1]} if best else None,
            "worst_sector": {"name": worst[0], **worst[1]} if worst else None,
            "sectors_up": sum(1 for v in sectors.values() if v.get("change_pct", 0) > 0),
            "sectors_down": sum(1 for v in sectors.values() if v.get("change_pct", 0) < 0),
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
