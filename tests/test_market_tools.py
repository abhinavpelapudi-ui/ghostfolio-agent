"""Tests for market data tools with mocked yfinance."""

import json

import pandas as pd
import pytest
import yfinance

# ── stock_price ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stock_price_returns_price(monkeypatch):
    class FakeFastInfo:
        def get(self, key, default=None):
            return {
                "lastPrice": 195.50, "previousClose": 190.0,
                "open": 191.0, "dayHigh": 196.0, "dayLow": 189.5,
                "currency": "USD",
            }.get(key, default)

    class FakeTicker:
        def __init__(self, symbol):
            self.fast_info = FakeFastInfo()

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    from app.agent.tools.stock_price import stock_price
    result = json.loads(await stock_price.ainvoke({"symbol": "AAPL"}))
    assert result["symbol"] == "AAPL"
    assert result["current_price"] == 195.50
    assert result["previous_close"] == 190.0
    assert result["day_change"] == 5.50
    assert result["day_change_pct"] == pytest.approx(2.89, abs=0.01)


@pytest.mark.asyncio
async def test_stock_price_error_handling(monkeypatch):
    def bad_ticker(symbol):
        raise ValueError("No data")

    monkeypatch.setattr(yfinance, "Ticker", bad_ticker)

    from app.agent.tools.stock_price import stock_price
    result = json.loads(await stock_price.ainvoke({"symbol": "INVALID"}))
    assert "error" in result


# ── stock_trend ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stock_trend_weekly(monkeypatch):
    dates = pd.date_range("2025-02-24", periods=5, freq="D")
    fake_hist = pd.DataFrame({
        "Close": [100.0, 102.0, 101.0, 103.0, 105.0],
        "Volume": [1000, 1200, 900, 1100, 1500],
    }, index=dates)

    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, period=None, interval=None):
            return fake_hist

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    from app.agent.tools.stock_trend import stock_trend
    result = json.loads(await stock_trend.ainvoke({"symbol": "AAPL", "period": "1w"}))
    assert result["symbol"] == "AAPL"
    assert result["period"] == "1w"
    assert result["start_price"] == 100.0
    assert result["end_price"] == 105.0
    assert result["direction"] == "up"
    assert result["data_points_count"] == 5


@pytest.mark.asyncio
async def test_stock_trend_empty_data(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, period=None, interval=None):
            return pd.DataFrame()

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    from app.agent.tools.stock_trend import stock_trend
    result = json.loads(await stock_trend.ainvoke({"symbol": "FAKE"}))
    assert "error" in result


# ── sector_performance ───────────────────────────────────────


@pytest.mark.asyncio
async def test_sector_performance(monkeypatch):
    from app.agent.tools.sector_performance import SECTOR_ETFS

    dates = pd.date_range("2025-02-24", periods=2, freq="D")

    class FakeIndividualTicker:
        def __init__(self, change_pct):
            start = 100.0
            end = start * (1 + change_pct / 100)
            self._hist = pd.DataFrame({"Close": [start, end]}, index=dates)

        def history(self, period=None):
            return self._hist

    class FakeTickers:
        def __init__(self, symbols_str):
            self.tickers = {}
            changes = [3.0, 2.0, 1.5, 1.0, 0.5, -0.5, -1.0, -1.5, -2.0, -2.5, -3.0]
            for i, etf in enumerate(SECTOR_ETFS.values()):
                self.tickers[etf] = FakeIndividualTicker(changes[i])

    monkeypatch.setattr(yfinance, "Tickers", FakeTickers)

    from app.agent.tools.sector_performance import sector_performance
    result = json.loads(await sector_performance.ainvoke({"period": "1w"}))
    assert result["period"] == "1w"
    assert "sectors" in result
    assert len(result["sectors"]) == 11
    assert result["best_sector"] is not None
    assert result["worst_sector"] is not None
    assert result["sectors_up"] > 0
    assert result["sectors_down"] > 0


# ── stock_volume ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stock_volume(monkeypatch):
    dates_5d = pd.date_range("2025-02-24", periods=5, freq="D")
    fake_hist = pd.DataFrame({
        "Open": [100, 102, 101, 103, 104],
        "Close": [102, 101, 103, 104, 106],
        "Volume": [1000000, 1200000, 900000, 1100000, 1500000],
    }, index=dates_5d)

    dates_30d = pd.date_range("2025-02-01", periods=20, freq="D")
    fake_30d = pd.DataFrame({
        "Open": [100] * 20,
        "Close": [102] * 20,
        "Volume": [1000000] * 20,
    }, index=dates_30d)

    call_count = {"n": 0}

    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, period=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return fake_hist
            return fake_30d

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    from app.agent.tools.stock_volume import stock_volume
    result = json.loads(await stock_volume.ainvoke({"symbol": "AAPL"}))
    assert result["symbol"] == "AAPL"
    assert result["latest_volume"] == 1500000
    assert len(result["daily_breakdown"]) == 5
    assert result["average_volume_30d"] > 0
    assert result["volume_assessment"] != ""


@pytest.mark.asyncio
async def test_stock_volume_empty(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            pass

        def history(self, period=None):
            return pd.DataFrame()

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    from app.agent.tools.stock_volume import stock_volume
    result = json.loads(await stock_volume.ainvoke({"symbol": "FAKE"}))
    assert "error" in result
