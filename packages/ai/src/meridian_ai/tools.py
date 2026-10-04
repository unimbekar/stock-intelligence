"""Tool names the assistant is allowed to call. Implementations live with each domain."""

from __future__ import annotations

TOOLS: dict[str, str] = {
    "get_stock_quote": "Latest demo or provider quote for one ticker.",
    "get_historical_prices": "Daily bars for one ticker.",
    "get_fundamentals": "Fundamentals stored for one ticker.",
    "get_technical_indicators": "Indicators computed from that ticker's bars.",
    "get_news": "News items already retrieved by the news provider.",
    "get_research": "Research evidence already retrieved by the research provider.",
    "get_analyst_ratings": "Analyst consensus from the analyst provider.",
    "get_portfolio": "A portfolio the signed-in user owns.",
    "get_positions": "Positions derived from that portfolio's transactions.",
    "get_watchlist": "A watchlist the signed-in user owns.",
    "calculate_position_size": "Share count from account, risk percent, entry, and stop.",
    "calculate_risk": "Risk, reward, and limit checks for a proposed trade.",
    "calculate_portfolio_metrics": "P&L, allocation, and performance from positions and marks.",
}
