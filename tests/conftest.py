"""Shared test fixtures with mocked Ghostfolio API responses."""

import httpx
import pytest
import respx

MOCK_GHOSTFOLIO_URL = "http://localhost:3333"


@pytest.fixture
def mock_ghostfolio():
    with respx.mock(base_url=MOCK_GHOSTFOLIO_URL, assert_all_called=False) as respx_mock:
        # Auth
        respx_mock.post("/api/v1/auth/anonymous").mock(
            return_value=httpx.Response(200, json={"authToken": "mock-jwt-token"})
        )

        # Portfolio details
        respx_mock.get("/api/v1/portfolio/details").mock(
            return_value=httpx.Response(200, json={
                "summary": {
                    "currentValue": 125000.50,
                    "totalInvestment": 100000.00,
                    "absoluteChange": 25000.50,
                    "relativeChange": 0.250005,
                    "currency": "USD",
                    "dividendInBaseCurrency": 1250.00,
                    "feesInBaseCurrency": 45.00,
                },
                "holdings": [
                    {
                        "symbol": "VOO", "name": "Vanguard S&P 500 ETF",
                        "value": 50000, "allocationInPercentage": 0.40,
                        "netPerformancePercentage": 0.30,
                        "assetClass": "EQUITY", "assetSubClass": "ETF",
                        "dataSource": "YAHOO",
                        "sectors": [{"name": "Technology", "weight": 0.30}],
                        "countries": [{"name": "United States", "weight": 1.0}],
                    },
                    {
                        "symbol": "AAPL", "name": "Apple Inc.",
                        "value": 30000, "allocationInPercentage": 0.24,
                        "netPerformancePercentage": 0.45,
                        "assetClass": "EQUITY", "assetSubClass": "STOCK",
                        "dataSource": "YAHOO",
                        "sectors": [{"name": "Technology", "weight": 1.0}],
                        "countries": [{"name": "United States", "weight": 1.0}],
                    },
                    {
                        "symbol": "MSFT", "name": "Microsoft Corp",
                        "value": 25000, "allocationInPercentage": 0.20,
                        "netPerformancePercentage": 0.35,
                        "assetClass": "EQUITY", "assetSubClass": "STOCK",
                        "dataSource": "YAHOO",
                        "sectors": [{"name": "Technology", "weight": 1.0}],
                        "countries": [{"name": "United States", "weight": 1.0}],
                    },
                    {
                        "symbol": "BND", "name": "Vanguard Total Bond Market ETF",
                        "value": 20000.50, "allocationInPercentage": 0.16,
                        "netPerformancePercentage": 0.02,
                        "assetClass": "FIXED_INCOME", "assetSubClass": "ETF",
                        "dataSource": "YAHOO",
                        "sectors": [],
                        "countries": [{"name": "United States", "weight": 1.0}],
                    },
                ],
            })
        )

        # Performance
        respx_mock.get("/api/v2/portfolio/performance").mock(
            return_value=httpx.Response(200, json={
                "currentGrossPerformance": 26000.00,
                "currentGrossPerformancePercent": 0.26,
                "currentNetPerformance": 25000.50,
                "currentNetPerformancePercent": 0.250005,
                "totalInvestment": 100000.00,
                "currentValue": 125000.50,
                "annualizedPerformancePercent": 0.12,
                "dividend": 1250.00,
                "fees": 45.00,
                "chart": [
                    {"date": "2024-01-01", "value": 100000},
                    {"date": "2025-01-01", "value": 125000.50},
                ],
            })
        )

        # Holding detail (AAPL)
        respx_mock.get("/api/v1/portfolio/holding/YAHOO/AAPL").mock(
            return_value=httpx.Response(200, json={
                "name": "Apple Inc.",
                "currency": "USD",
                "marketPrice": 195.50,
                "quantity": 153.4,
                "value": 29990.70,
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
            })
        )

        # Accounts
        respx_mock.get("/api/v1/account").mock(
            return_value=httpx.Response(200, json=[
                {"id": "acc-1", "name": "Brokerage", "balance": 5000, "currency": "USD"},
            ])
        )

        # Orders
        respx_mock.get("/api/v1/order").mock(
            return_value=httpx.Response(200, json={
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
                ]
            })
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

        yield respx_mock
