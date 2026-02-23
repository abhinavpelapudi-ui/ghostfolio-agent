"""Test the Ghostfolio API client with mocked HTTP responses."""

import pytest

from app.clients.ghostfolio import GhostfolioClient


@pytest.fixture
async def client(mock_ghostfolio):
    c = GhostfolioClient()
    c._base_url = "http://localhost:3333"
    c._access_token = "test-token"
    yield c
    await c.close()


async def test_authenticate(client):
    token = await client._authenticate()
    assert token == "mock-jwt-token"
    assert client._bearer_token == "mock-jwt-token"


async def test_get_portfolio_details(client):
    details = await client.get_portfolio_details()
    assert "summary" in details
    assert details["summary"]["currentValue"] == 125000.50


async def test_get_portfolio_performance(client):
    perf = await client.get_portfolio_performance(date_range="max")
    assert perf["currentValue"] == 125000.50
    assert len(perf["chart"]) == 2


async def test_get_holding_detail(client):
    detail = await client.get_holding_detail("YAHOO", "AAPL")
    assert detail["name"] == "Apple Inc."
    assert detail["quantity"] == 153.4


async def test_get_accounts(client):
    accounts = await client.get_accounts()
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Brokerage"
