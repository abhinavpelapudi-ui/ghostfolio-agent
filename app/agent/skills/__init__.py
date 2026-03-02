"""Skill-based intent classification for the finance agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    display_name: str
    keywords: tuple[str, ...]
    relevant_tools: tuple[str, ...]
    prompt_addon: str
    priority: int = 0  # higher = checked first on tie


SKILLS: dict[str, Skill] = {
    "portfolio_analysis": Skill(
        name="portfolio_analysis",
        display_name="Portfolio Analysis",
        keywords=(
            "portfolio", "summary", "overview", "holdings", "allocation",
            "total", "value", "what do i own", "asset", "worth",
        ),
        relevant_tools=("portfolio_summary", "holding_detail"),
        prompt_addon=(
            "Focus on portfolio composition and allocations. "
            "Present holdings grouped by asset class with percentage weights. "
            "Highlight the top holdings and cash position."
        ),
        priority=0,  # default fallback
    ),
    "performance_tracking": Skill(
        name="performance_tracking",
        display_name="Performance Tracking",
        keywords=(
            "performance", "return", "gain", "loss", "profit",
            "how did", "ytd", "chart", "growth", "up", "down",
        ),
        relevant_tools=("portfolio_performance", "portfolio_summary"),
        prompt_addon=(
            "Focus on time-range performance comparisons. "
            "Present net and gross returns clearly. "
            "Compare across time periods when relevant."
        ),
        priority=1,
    ),
    "trade_execution": Skill(
        name="trade_execution",
        display_name="Trade Execution",
        keywords=(
            "buy", "sell", "bought", "sold", "trade", "purchase",
            "add trade", "shares of", "units of",
        ),
        relevant_tools=("add_trade", "symbol_search"),
        prompt_addon=(
            "CRITICAL: Confirm ALL trade details before executing. "
            "Always use symbol_search first if the user provides a company name instead of a ticker. "
            "Validate quantity, price, and date before calling add_trade."
        ),
        priority=2,  # highest — trade keywords are unambiguous
    ),
    "risk_assessment": Skill(
        name="risk_assessment",
        display_name="Risk Assessment",
        keywords=(
            "risk", "diversification", "diversified", "concentration", "sector",
            "geographic", "exposure", "safe", "volatile", "health",
        ),
        relevant_tools=("market_sentiment", "portfolio_summary", "sector_performance"),
        prompt_addon=(
            "Focus on risk analysis and diversification. "
            "Check concentration risk, sector exposure, and geographic distribution. "
            "Always include specific risk flags and thresholds."
        ),
        priority=1,
    ),
    "research": Skill(
        name="research",
        display_name="Research",
        keywords=(
            "search", "lookup", "find", "what is", "ticker", "symbol",
            "dividend", "history", "transactions", "orders",
        ),
        relevant_tools=("symbol_search", "holding_detail", "dividend_history", "transactions", "stock_price"),
        prompt_addon=(
            "Focus on data lookup and presentation. "
            "Present transaction history chronologically. "
            "For dividends, show total received and payment frequency."
        ),
        priority=1,
    ),
    "market_data": Skill(
        name="market_data",
        display_name="Market Data",
        keywords=(
            "price", "current price", "stock price", "how much is",
            "trading at", "trend", "trending", "volume", "sectors",
            "market trend", "how is the market", "doing today",
            "week trend", "buy volume", "sell volume",
        ),
        relevant_tools=("stock_price", "stock_trend", "sector_performance", "stock_volume"),
        prompt_addon=(
            "Focus on real-time market data from Yahoo Finance. "
            "Present prices with currency symbols and change percentages. "
            "For trends, describe the direction and magnitude clearly. "
            "For sector performance, highlight best and worst performers. "
            "Note: volume data shows total trading volume with price direction as a proxy for buy/sell pressure."
        ),
        priority=1,
    ),
}

DEFAULT_SKILL = SKILLS["portfolio_analysis"]


def classify_intent(message: str) -> Skill:
    """Keyword-based intent classification. Returns best-matching Skill."""
    message_lower = message.lower()
    best_skill: Skill | None = None
    best_score = 0

    for skill in SKILLS.values():
        score = sum(1 for kw in skill.keywords if kw in message_lower)
        weighted = score * 10 + skill.priority
        if score > 0 and weighted > best_score:
            best_score = weighted
            best_skill = skill

    return best_skill or DEFAULT_SKILL
