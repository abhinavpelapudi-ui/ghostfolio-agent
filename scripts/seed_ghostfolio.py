"""Seed a local Ghostfolio instance with sample portfolio data.

Usage:
    python scripts/seed_ghostfolio.py

Requires GHOSTFOLIO_URL and GHOSTFOLIO_ACCESS_TOKEN env vars.
"""

import os
import sys

import httpx

GHOSTFOLIO_URL = os.environ.get("GHOSTFOLIO_URL", "http://localhost:3333")
ACCESS_TOKEN = os.environ.get("GHOSTFOLIO_ACCESS_TOKEN", "")

SAMPLE_ORDERS = [
    {"symbol": "VOO", "type": "BUY", "date": "2023-01-15T00:00:00.000Z", "quantity": 100, "unitPrice": 350.00, "fee": 0, "currency": "USD", "dataSource": "YAHOO"},
    {"symbol": "AAPL", "type": "BUY", "date": "2023-03-15T00:00:00.000Z", "quantity": 150, "unitPrice": 145.00, "fee": 4.95, "currency": "USD", "dataSource": "YAHOO"},
    {"symbol": "MSFT", "type": "BUY", "date": "2023-06-01T00:00:00.000Z", "quantity": 60, "unitPrice": 340.00, "fee": 4.95, "currency": "USD", "dataSource": "YAHOO"},
    {"symbol": "BND", "type": "BUY", "date": "2023-02-01T00:00:00.000Z", "quantity": 250, "unitPrice": 72.00, "fee": 0, "currency": "USD", "dataSource": "YAHOO"},
    {"symbol": "GOOGL", "type": "BUY", "date": "2024-01-10T00:00:00.000Z", "quantity": 30, "unitPrice": 140.00, "fee": 4.95, "currency": "USD", "dataSource": "YAHOO"},
]


def seed():
    if not ACCESS_TOKEN:
        print("Error: GHOSTFOLIO_ACCESS_TOKEN not set")
        sys.exit(1)

    client = httpx.Client(timeout=30.0)

    # Authenticate
    resp = client.post(f"{GHOSTFOLIO_URL}/api/v1/auth/anonymous", json={"accessToken": ACCESS_TOKEN})
    resp.raise_for_status()
    bearer = resp.json()["authToken"]
    headers = {"Authorization": f"Bearer {bearer}"}

    print(f"Authenticated with Ghostfolio at {GHOSTFOLIO_URL}")

    # Import orders
    resp = client.post(
        f"{GHOSTFOLIO_URL}/api/v1/import",
        json={"activities": SAMPLE_ORDERS},
        headers=headers,
    )

    if resp.status_code == 201:
        print(f"Successfully imported {len(SAMPLE_ORDERS)} orders")
    else:
        print(f"Import failed: {resp.status_code} — {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    seed()
