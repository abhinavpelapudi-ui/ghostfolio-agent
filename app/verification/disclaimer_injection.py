"""Inject financial disclaimer into agent responses."""

from app.agent.prompts import FINANCIAL_DISCLAIMER

DISCLAIMER_TRIGGERS = [
    "return", "performance", "gain", "loss", "risk", "volatility",
    "allocation", "diversification", "dividend", "yield", "growth",
    "investment", "portfolio", "value", "profit",
]


def inject_disclaimer(response: str) -> str:
    response_lower = response.lower()
    needs_disclaimer = any(trigger in response_lower for trigger in DISCLAIMER_TRIGGERS)
    if needs_disclaimer and FINANCIAL_DISCLAIMER not in response:
        return response + FINANCIAL_DISCLAIMER
    return response
