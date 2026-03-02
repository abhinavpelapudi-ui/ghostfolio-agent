from app.agent.tools.add_trade import add_trade
from app.agent.tools.dividend_history import dividend_history
from app.agent.tools.holding_detail import holding_detail
from app.agent.tools.market_sentiment import market_sentiment
from app.agent.tools.portfolio_performance import portfolio_performance
from app.agent.tools.portfolio_summary import portfolio_summary
from app.agent.tools.sector_performance import sector_performance
from app.agent.tools.stock_price import stock_price
from app.agent.tools.stock_trend import stock_trend
from app.agent.tools.stock_volume import stock_volume
from app.agent.tools.symbol_search import symbol_search
from app.agent.tools.transactions import transactions

ALL_TOOLS = [
    portfolio_summary,
    portfolio_performance,
    holding_detail,
    transactions,
    dividend_history,
    symbol_search,
    market_sentiment,
    add_trade,
    stock_price,
    stock_trend,
    sector_performance,
    stock_volume,
]
