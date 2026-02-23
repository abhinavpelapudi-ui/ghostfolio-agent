"""Detect when the agent mentions symbols or values not present in tool data."""

import re

TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")

IGNORE_WORDS = {
    "USD", "EUR", "GBP", "ETF", "CEO", "IPO", "GDP", "YTD", "BUY", "SELL",
    "THE", "AND", "FOR", "NOT", "BUT", "ARE", "ALL", "CAN", "HAS", "HER",
    "ONE", "OUR", "OUT", "YOU", "DAY", "GET", "HIS", "HOW", "ITS", "MAY",
    "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "TOP", "FEE",
}


def check_hallucination(response: str, tool_outputs: list[str]) -> dict:
    all_tool_data = " ".join(tool_outputs)

    response_tickers = set(TICKER_RE.findall(response)) - IGNORE_WORDS
    tool_tickers = set(TICKER_RE.findall(all_tool_data)) - IGNORE_WORDS

    unknown_tickers = response_tickers - tool_tickers

    flagged = []
    for ticker in unknown_tickers:
        pattern = rf"(\$\s*{ticker}|{ticker}\s+(?:stock|shares|holding|position|etf|fund))"
        if re.search(pattern, response, re.IGNORECASE):
            flagged.append(ticker)

    return {
        "detected": len(flagged) > 0,
        "unknown_tickers": flagged,
    }
