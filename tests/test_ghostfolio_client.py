"""Test the Ghostfolio API client with mocked HTTP responses."""

import pytest

from app.clients.ghostfolio import GhostfolioClient, _default_client, get_client, use_client


@pytest.fixture
async def client(mock_ghostfolio):
    c = GhostfolioClient(access_token="test-token", base_url="http://localhost:3333")
    yield c
    await c.close()


async def test_authenticate(client):
    token = await client._authenticate()
    assert token == "mock-jwt-token"
    assert client._bearer_token == "mock-jwt-token"


async def test_get_portfolio_details(client):
    details = await client.get_portfolio_details()
    assert "summary" in details
    assert details["summary"]["currentValueInBaseCurrency"] == 125000.50
    # holdings is a dict keyed by symbol
    assert isinstance(details["holdings"], dict)
    assert "VOO" in details["holdings"]


async def test_get_portfolio_performance(client):
    perf = await client.get_portfolio_performance(date_range="max")
    assert "performance" in perf
    assert perf["performance"]["netPerformance"] == 25000.50
    assert len(perf["chart"]) == 2


async def test_get_holding_detail(client):
    detail = await client.get_holding_detail("YAHOO", "AAPL")
    assert detail["name"] == "Apple Inc."
    assert detail["quantity"] == 153.4


async def test_get_accounts(client):
    accounts = await client.get_accounts()
    assert "accounts" in accounts
    assert len(accounts["accounts"]) == 1
    assert accounts["accounts"][0]["name"] == "Brokerage"


async def test_get_orders(client):
    orders = await client.get_orders()
    assert "activities" in orders
    assert len(orders["activities"]) == 3


async def test_create_order(client):
    order = {
        "accountId": "acc-1",
        "symbol": "TSLA",
        "quantity": 5,
        "unitPrice": 250,
        "type": "BUY",
        "currency": "USD",
        "dataSource": "YAHOO",
        "date": "2025-01-01T00:00:00.000Z",
        "fee": 0,
    }
    result = await client.create_order(order)
    assert result["id"] == "order-new-1"


# ── Context var tests ────────────────────────────────────────────────

def test_get_client_returns_default():
    """When no context var is set, get_client() returns the default singleton."""
    assert get_client() is _default_client


async def test_use_client_overrides(mock_ghostfolio):
    """use_client() context manager sets and resets the active client."""
    custom = GhostfolioClient(access_token="custom-token", base_url="http://localhost:3333")
    with use_client(custom):
        assert get_client() is custom
    # After context manager exits, should revert to default
    assert get_client() is _default_client
    await custom.close()


def test_parametrized_constructor():
    """GhostfolioClient accepts explicit access_token and base_url."""
    c = GhostfolioClient(access_token="my-token", base_url="http://example.com:3333/")
    assert c._access_token == "my-token"
    assert c._base_url == "http://example.com:3333"
