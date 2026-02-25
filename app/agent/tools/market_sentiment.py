"""Tool: Analyze portfolio risk and diversification metrics."""

import json

from langchain_core.tools import tool

from app.clients.ghostfolio import get_client


@tool
async def market_sentiment() -> str:
    """Analyze portfolio risk and diversification metrics.
    Returns sector concentration, asset class breakdown, geographic exposure,
    and flags potential risks like over-concentration.
    Use when user asks about risk, diversification, or portfolio health."""
    try:
        details = await get_client().get_portfolio_details()
        holdings_raw = details.get("holdings", {})

        # holdings is a dict keyed by symbol, convert to list
        if isinstance(holdings_raw, dict):
            holdings = list(holdings_raw.values())
        else:
            holdings = holdings_raw or []

        if not holdings:
            return json.dumps({"error": "No holdings found in portfolio"})

        total_value = sum(h.get("valueInBaseCurrency", 0) for h in holdings)
        if total_value == 0:
            return json.dumps({"error": "Portfolio total value is zero"})

        # Sector concentration
        sectors: dict[str, float] = {}
        for h in holdings:
            for s in h.get("sectors", []):
                name = s.get("name", "Unknown")
                weight = s.get("weight", 0) * h.get("valueInBaseCurrency", 0)
                sectors[name] = sectors.get(name, 0) + weight
        sector_pcts = {k: round(v / total_value * 100, 2) for k, v in sectors.items()}

        # Geographic exposure
        countries: dict[str, float] = {}
        for h in holdings:
            for c in h.get("countries", []):
                name = c.get("name", "Unknown")
                weight = c.get("weight", 0) * h.get("valueInBaseCurrency", 0)
                countries[name] = countries.get(name, 0) + weight
        country_pcts = {k: round(v / total_value * 100, 2) for k, v in countries.items()}

        # Asset class breakdown
        asset_classes: dict[str, float] = {}
        for h in holdings:
            ac = h.get("assetClass", "UNKNOWN")
            asset_classes[ac] = asset_classes.get(ac, 0) + h.get("valueInBaseCurrency", 0)
        ac_pcts = {k: round(v / total_value * 100, 2) for k, v in asset_classes.items()}

        # Concentration risk
        sorted_holdings = sorted(holdings, key=lambda h: h.get("valueInBaseCurrency", 0), reverse=True)
        top_holding_pct = round(sorted_holdings[0].get("valueInBaseCurrency", 0) / total_value * 100, 2)
        top_3_pct = round(sum(h.get("valueInBaseCurrency", 0) for h in sorted_holdings[:3]) / total_value * 100, 2)

        # Risk flags
        risk_flags = []
        if top_holding_pct > 25:
            risk_flags.append(
                f"Single holding concentration: {sorted_holdings[0].get('symbol', '?')} at {top_holding_pct}%"
            )
        if top_3_pct > 60:
            risk_flags.append(f"Top 3 holdings represent {top_3_pct}% of portfolio")
        if len(holdings) < 5:
            risk_flags.append(f"Low diversification: only {len(holdings)} holdings")
        if len(sector_pcts) <= 2:
            risk_flags.append("Narrow sector exposure")

        result = {
            "total_value": round(total_value, 2),
            "holdings_count": len(holdings),
            "sector_allocation": dict(sorted(sector_pcts.items(), key=lambda x: x[1], reverse=True)),
            "geographic_allocation": dict(sorted(country_pcts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "asset_class_allocation": ac_pcts,
            "concentration": {
                "top_holding_pct": top_holding_pct,
                "top_holding_symbol": sorted_holdings[0].get("symbol", ""),
                "top_3_pct": top_3_pct,
            },
            "risk_flags": risk_flags,
            "diversification_score": "low" if len(risk_flags) >= 3 else "moderate" if risk_flags else "good",
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
