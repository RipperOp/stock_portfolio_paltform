from django.urls import path
from .views import (
    get_stock_data,
    home,
    watchlist,
    strategy,
    backtest_stock,
    backtest_results,
    login_view,
    logout_view,
    register_view,
    paper_trading_dashboard,
    execute_paper_trade,
    get_portfolio_value,
    portfolio,
)

urlpatterns = [
    # Page Routes
    path("", home, name="home"),
    path("watchlist/", watchlist, name="watchlist"),
    path("strategy/", strategy, name="strategy"),
    path("backtest/", backtest_results, name="backtest_results"),  # Backtest results page
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", register_view, name="register"),

    # API Routes
    path("api/stocks/", get_stock_data, name="get_stock_data"),
    path("api/backtest/", backtest_stock, name="backtest_stock"),  # API for backtesting stocks

    # Paper Trading URLs
    path('paper-trading/', paper_trading_dashboard, name='paper_trading_dashboard'),
    path('paper-trading/execute-trade/', execute_paper_trade, name='execute_paper_trade'),
    path('portfolio/', portfolio, name='portfolio'),
    path('api/portfolio/value/', get_portfolio_value, name='get_portfolio_value'),
]
