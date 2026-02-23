"""Enforce risk threshold warnings when certain conditions are met."""

import json

RISK_THRESHOLDS = {
    "single_holding_concentration": 25.0,
    "top_3_concentration": 60.0,
    "max_drawdown_warning": -20.0,
    "min_holdings_diversification": 5,
}


def check_risk_thresholds(tool_outputs: list[str]) -> list[str]:
    warnings = []

    for output in tool_outputs:
        try:
            data = json.loads(output) if isinstance(output, str) else output
        except (json.JSONDecodeError, TypeError):
            continue

        concentration = data.get("concentration", {})
        top_pct = concentration.get("top_holding_pct", 0)
        if top_pct > RISK_THRESHOLDS["single_holding_concentration"]:
            symbol = concentration.get("top_holding_symbol", "Unknown")
            warnings.append(
                f"Concentration risk: {symbol} represents {top_pct}% of portfolio "
                f"(threshold: {RISK_THRESHOLDS['single_holding_concentration']}%)"
            )

        top3 = concentration.get("top_3_pct", 0)
        if top3 > RISK_THRESHOLDS["top_3_concentration"]:
            warnings.append(f"Top 3 holdings represent {top3}% of portfolio")

        net_pct = data.get("current_net_performance_pct", 0)
        if net_pct < RISK_THRESHOLDS["max_drawdown_warning"]:
            warnings.append(f"Significant loss: portfolio is down {net_pct}%")

    return warnings
