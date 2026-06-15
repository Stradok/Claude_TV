"""
screener.py
───────────
Gets the stock universe from TradingView's screener.
Falls back to S&P 500 Wikipedia list if TradingView is unreachable.
"""
from config import MIN_MARKET_CAP, MIN_VOLUME, MAX_STOCKS, EXCHANGES


def get_stock_universe() -> list[str]:
    """Return list of stock symbols to scan."""
    print("→ Fetching stock universe from TradingView screener…")
    try:
        from tradingview_screener import Query, col as c
        _, df = (
            Query()
            .select("name", "close", "volume", "market_cap_basic")
            .where(
                c("market_cap_basic") > MIN_MARKET_CAP,
                c("volume")           > MIN_VOLUME,
                c("type").isin(["stock"]),
                c("exchange").isin(EXCHANGES),
            )
            .order_by("market_cap_basic", ascending=False)
            .limit(MAX_STOCKS)
            .get_scanner_data()
        )
        symbols = df["name"].tolist()
        print(f"✓ {len(symbols)} stocks from TradingView")
        return symbols

    except Exception as e:
        print(f"⚠ TradingView screener failed ({e}), using S&P 500 fallback")
        return _sp500_fallback()


def _sp500_fallback() -> list[str]:
    """Scrape S&P 500 tickers from Wikipedia."""
    import pandas as pd
    df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    symbols = df["Symbol"].str.replace(".", "-", regex=False).tolist()
    print(f"✓ {len(symbols)} stocks from S&P 500 fallback")
    return symbols