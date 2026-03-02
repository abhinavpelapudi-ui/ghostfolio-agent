"""Tests for skill-based intent classification."""

from app.agent.skills import SKILLS, classify_intent


def test_classify_portfolio_analysis():
    assert classify_intent("show me my portfolio summary").name == "portfolio_analysis"


def test_classify_portfolio_holdings():
    assert classify_intent("what are my holdings?").name == "portfolio_analysis"


def test_classify_portfolio_value():
    assert classify_intent("what is my total portfolio value?").name == "portfolio_analysis"


def test_classify_performance_tracking():
    assert classify_intent("how did my portfolio perform this year?").name == "performance_tracking"


def test_classify_performance_returns():
    assert classify_intent("show me my returns for ytd").name == "performance_tracking"


def test_classify_trade_execution_buy():
    assert classify_intent("I bought 10 shares of AAPL at $230").name == "trade_execution"


def test_classify_trade_execution_sell():
    assert classify_intent("sell 5 shares of MSFT").name == "trade_execution"


def test_classify_risk_assessment():
    assert classify_intent("how is my diversification?").name == "risk_assessment"


def test_classify_risk_concentration():
    assert classify_intent("do I have concentration risk?").name == "risk_assessment"


def test_classify_research_search():
    assert classify_intent("search for Apple stock").name == "research"


def test_classify_research_dividend():
    assert classify_intent("show dividend history for VOO").name == "research"


def test_classify_research_transactions():
    assert classify_intent("show my transactions").name == "research"


def test_classify_fallback():
    assert classify_intent("hello there").name == "portfolio_analysis"


def test_classify_empty_string():
    assert classify_intent("").name == "portfolio_analysis"


def test_all_skills_have_required_fields():
    for name, skill in SKILLS.items():
        assert skill.name == name
        assert len(skill.display_name) > 0
        assert len(skill.keywords) > 0
        assert len(skill.relevant_tools) > 0
        assert len(skill.prompt_addon) > 0


def test_classify_market_data_price():
    assert classify_intent("what is the current price of AAPL").name == "market_data"


def test_classify_market_data_trend():
    assert classify_intent("show me the trend for MSFT this week").name == "market_data"


def test_classify_market_data_sector():
    assert classify_intent("show me sectors doing today").name == "market_data"


def test_classify_market_data_volume():
    assert classify_intent("show me the trading volume for TSLA").name == "market_data"


def test_trade_has_highest_priority():
    trade = SKILLS["trade_execution"]
    for name, skill in SKILLS.items():
        if name != "trade_execution":
            assert trade.priority >= skill.priority
