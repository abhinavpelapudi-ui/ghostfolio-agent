"""Verify that numbers cited in the agent's response match tool output data."""

import re


def check_numerical_consistency(response: str, tool_outputs: list[str]) -> dict:
    dollar_pattern = r"\$[\d,]+\.?\d*"
    pct_pattern = r"[\d]+\.?\d*%"

    response_dollars = set(re.findall(dollar_pattern, response))
    response_pcts = set(re.findall(pct_pattern, response))

    all_tool_data = " ".join(tool_outputs)

    inconsistencies = []
    for dollar in response_dollars:
        numeric_val = dollar.replace("$", "").replace(",", "")
        if numeric_val not in all_tool_data and dollar not in all_tool_data:
            inconsistencies.append(f"Dollar amount {dollar} not found in tool data")

    for pct in response_pcts:
        numeric_val = pct.replace("%", "")
        if numeric_val not in all_tool_data and pct not in all_tool_data:
            inconsistencies.append(f"Percentage {pct} not found in tool data")

    return {
        "consistent": len(inconsistencies) == 0,
        "inconsistencies": inconsistencies,
    }
