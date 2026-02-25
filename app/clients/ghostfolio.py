"""Async HTTP client for the Ghostfolio REST API."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GhostfolioClient:
    def __init__(self) -> None:
        self._base_url = settings.ghostfolio_url.rstrip("/")
        self._access_token = settings.ghostfolio_access_token
        self._bearer_token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _authenticate(self) -> str:
        resp = await self._client.post(
            f"{self._base_url}/api/v1/auth/anonymous",
            json={"accessToken": self._access_token},
        )
        resp.raise_for_status()
        data = resp.json()
        self._bearer_token = data["authToken"]
        logger.info("Authenticated with Ghostfolio")
        return self._bearer_token

    async def _get(self, path: str, params: dict | None = None) -> dict:
        if not self._bearer_token:
            await self._authenticate()
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        resp = await self._client.get(
            f"{self._base_url}{path}", headers=headers, params=params
        )
        if resp.status_code == 401:
            await self._authenticate()
            headers = {"Authorization": f"Bearer {self._bearer_token}"}
            resp = await self._client.get(
                f"{self._base_url}{path}", headers=headers, params=params
            )
        resp.raise_for_status()
        return resp.json()

    # ── Portfolio ───────────────────────────────────────────────────
    async def get_portfolio_details(self) -> dict:
        return await self._get("/api/v1/portfolio/details")

    async def get_portfolio_holdings(self, date_range: str = "max") -> dict:
        return await self._get("/api/v1/portfolio/holdings", params={"range": date_range})

    async def get_portfolio_performance(self, date_range: str = "max") -> dict:
        return await self._get("/api/v2/portfolio/performance", params={"range": date_range})

    async def get_holding_detail(self, data_source: str, symbol: str) -> dict:
        return await self._get(f"/api/v1/portfolio/holding/{data_source}/{symbol}")

    async def _post(self, path: str, body: dict) -> dict:
        if not self._bearer_token:
            await self._authenticate()
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        resp = await self._client.post(
            f"{self._base_url}{path}", headers=headers, json=body
        )
        if resp.status_code == 401:
            await self._authenticate()
            headers = {"Authorization": f"Bearer {self._bearer_token}"}
            resp = await self._client.post(
                f"{self._base_url}{path}", headers=headers, json=body
            )
        resp.raise_for_status()
        return resp.json()

    # ── Orders ──────────────────────────────────────────────────────
    async def get_orders(self, **filters) -> dict:
        return await self._get("/api/v1/order", params=filters)

    async def create_order(self, order: dict) -> dict:
        return await self._post("/api/v1/order", order)

    # ── Dividends ───────────────────────────────────────────────────
    async def get_dividends(self, data_source: str, symbol: str) -> dict:
        return await self._get(f"/api/v1/portfolio/dividends/{data_source}/{symbol}")

    # ── Symbol Lookup ───────────────────────────────────────────────
    async def lookup_symbol(self, query: str) -> dict:
        return await self._get("/api/v1/symbol/lookup", params={"query": query})

    # ── Accounts ────────────────────────────────────────────────────
    async def get_accounts(self) -> dict:
        return await self._get("/api/v1/account")

    async def close(self) -> None:
        await self._client.aclose()


ghostfolio_client = GhostfolioClient()
