"""Shared test fixtures with mocked Ghostfolio API responses.

Mock data matches the REAL Ghostfolio API structure:
- holdings is a dict keyed by symbol (not a list)
- field names use 'valueInBaseCurrency' (not 'value')
- performance data is nested under 'performance' key
"""

import httpx
import pytest
import respx

MOCK_GHOSTFOLIO_URL = "http://localhost:3333"

# ── Mock Data ────────────────────────────────────────────────────────

MOCK_HOLDINGS = {
    "VOO": {
        "symbol": "VOO", "name": "Vanguard S&P 500 ETF",
        "valueInBaseCurrency": 50000, "allocationInPercentage": 0.40,
        "netPerformancePercent": 0.30,
        "assetClass": "EQUITY", "assetSubClass": "ETF",
        "dataSource": "YAHOO",
        "sectors": [{"name": "Technology", "weight": 0.30}, {"name": "Healthcare", "weight": 0.15}],
        "countries": [{"name": "United States", "weight": 1.0}],
    },
    "AAPL": {
        "symbol": "AAPL", "name": "Apple Inc.",
        "valueInBaseCurrency": 30000, "allocationInPercentage": 0.24,
        "netPerformancePercent": 0.45,
        "assetClass": "EQUITY", "assetSubClass": "STOCK",
        "dataSource": "YAHOO",
        "sectors": [{"name": "Technology", "weight": 1.0}],
        "countries": [{"name": "United States", "weight": 1.0}],
    },
    "MSFT": {
        "symbol": "MSFT", "name": "Microsoft Corp",
        "valueInBaseCurrency": 25000, "allocationInPercentage": 0.20,
        "netPerformancePercent": 0.35,
        "assetClass": "EQUITY", "assetSubClass": "STOCK",
        "dataSource": "YAHOO",
        "sectors": [{"name": "Technology", "weight": 1.0}],
        "countries": [{"name": "United States", "weight": 1.0}],
    },
    "BND": {
        "symbol": "BND", "name": "Vanguard Total Bond Market ETF",
        "valueInBaseCurrency": 20000.50, "allocationInPercentage": 0.16,
        "netPerformancePercent": 0.02,
        "assetClass": "FIXED_INCOME", "assetSubClass": "ETF",
        "dataSource": "YAHOO",
        "sectors": [],
        "countries": [{"name": "United States", "weight": 1.0}],
    },
}

MOCK_SUMMARY = {
    "currentValueInBaseCurrency": 125000.50,
    "totalInvestment": 100000.00,
    "netPerformance": 25000.50,
    "netPerformancePercentage": 0.250005,
    "grossPerformance": 26000.00,
    "annualizedPerformancePercent": 0.12,
    "dividendInBaseCurrency": 1250.00,
    "fees": 45.00,
    "cash": 5000.00,
}

MOCK_PERFORMANCE = {
    "performance": {
        "grossPerformance": 26000.00,
        "grossPerformancePercent": 0.26,
        "netPerformance": 25000.50,
        "netPerformancePercentage": 0.250005,
        "totalInvestment": 100000.00,
        "currentValueInBaseCurrency": 125000.50,
        "currentNetWorth": 130000.50,
        "annualizedPerformancePercent": 0.12,
        "dividend": 1250.00,
        "fees": 45.00,
    },
    "chart": [
        {"date": "2024-01-01", "value": 100000},
        {"date": "2025-01-01", "value": 125000.50},
    ],
}

MOCK_HOLDING_AAPL = {
    "name": "Apple Inc.",
    "currency": "USD",
    "marketPrice": 195.50,
    "quantity": 153.4,
    "valueInBaseCurrency": 29990.70,
    "averagePrice": 145.00,
    "investment": 22243.00,
    "grossPerformance": 7747.70,
    "grossPerformancePercent": 0.3483,
    "netPerformance": 7700.00,
    "netPerformancePercent": 0.3462,
    "dividend": 120.00,
    "firstBuyDate": "2023-03-15",
    "assetClass": "EQUITY",
    "assetSubClass": "STOCK",
    "sectors": [{"name": "Technology", "weight": 1.0}],
    "countries": [{"name": "United States", "weight": 1.0}],
}

MOCK_ORDERS = {
    "activities": [
        {
            "date": "2023-03-15T00:00:00.000Z",
            "type": "BUY",
            "quantity": 150,
            "unitPrice": 145.00,
            "fee": 4.95,
            "SymbolProfile": {"symbol": "AAPL", "name": "Apple Inc.", "currency": "USD"},
            "Account": {"name": "Brokerage"},
        },
        {
            "date": "2023-01-15T00:00:00.000Z",
            "type": "BUY",
            "quantity": 100,
            "unitPrice": 350.00,
            "fee": 0,
            "SymbolProfile": {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "currency": "USD"},
            "Account": {"name": "Brokerage"},
        },
        {
            "date": "2024-06-01T00:00:00.000Z",
            "type": "SELL",
            "quantity": 10,
            "unitPrice": 190.00,
            "fee": 4.95,
            "SymbolProfile": {"symbol": "AAPL", "name": "Apple Inc.", "currency": "USD"},
            "Account": {"name": "Brokerage"},
        },
    ]
}

MOCK_ACCOUNTS = {
    "accounts": [
        {"id": "acc-1", "name": "Brokerage", "balance": 5000, "currency": "USD"},
    ]
}


# ── Fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_ghostfolio():
    with respx.mock(base_url=MOCK_GHOSTFOLIO_URL, assert_all_called=False) as respx_mock:
        # Auth
        respx_mock.post("/api/v1/auth/anonymous").mock(
            return_value=httpx.Response(200, json={"authToken": "mock-jwt-token"})
        )

        # Portfolio details (holdings is a DICT keyed by symbol)
        respx_mock.get("/api/v1/portfolio/details").mock(
            return_value=httpx.Response(200, json={
                "summary": MOCK_SUMMARY,
                "holdings": MOCK_HOLDINGS,
            })
        )

        # Performance (nested under 'performance' key)
        respx_mock.get("/api/v2/portfolio/performance").mock(
            return_value=httpx.Response(200, json=MOCK_PERFORMANCE)
        )

        # Holding detail (AAPL)
        respx_mock.get("/api/v1/portfolio/holding/YAHOO/AAPL").mock(
            return_value=httpx.Response(200, json=MOCK_HOLDING_AAPL)
        )

        # Accounts
        respx_mock.get("/api/v1/account").mock(
            return_value=httpx.Response(200, json=MOCK_ACCOUNTS)
        )

        # Orders
        respx_mock.get("/api/v1/order").mock(
            return_value=httpx.Response(200, json=MOCK_ORDERS)
        )

        # Symbol lookup
        respx_mock.get("/api/v1/symbol/lookup").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "dataSource": "YAHOO",
                        "assetClass": "EQUITY",
                        "assetSubClass": "STOCK",
                        "currency": "USD",
                    }
                ]
            })
        )

        # Dividends
        respx_mock.get("/api/v1/portfolio/dividends/YAHOO/VOO").mock(
            return_value=httpx.Response(200, json={
                "dividends": [
                    {"date": "2024-03-15", "amount": 150.00},
                    {"date": "2024-06-15", "amount": 160.00},
                    {"date": "2024-09-15", "amount": 155.00},
                    {"date": "2024-12-15", "amount": 165.00},
                ]
            })
        )

        # Create order
        respx_mock.post("/api/v1/order").mock(
            return_value=httpx.Response(201, json={
                "id": "order-new-1",
                "type": "BUY",
                "symbol": "TSLA",
                "quantity": 5,
                "unitPrice": 250,
            })
        )

        yield respx_mock
