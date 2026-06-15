"""
data_fetcher.py
───────────────
Downloads OHLCV data via yfinance in one batched call.
Caches results as a parquet file — skips re-downloading within CACHE_HOURS.
"""
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from config import DATA_CACHE_DIR, CACHE_HOURS


def fetch_stock_data(symbols: list[str], lookback_days: int) -> dict[str, pd.DataFrame]:
    """
    Returns {symbol: OHLCV DataFrame} for all symbols.
    Columns are lowercase: open, high, low, close, volume.
    """
    os.makedirs(DATA_CACHE_DIR, exist_ok=True)
    cache_path = f"{DATA_CACHE_DIR}/ohlcv_{len(symbols)}_{lookback_days}d.parquet"

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if os.path.exists(cache_path):
        age_secs = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))).seconds
        if age_secs < CACHE_HOURS * 3600:
            print(f"✓ Data loaded from cache (age: {age_secs // 60}m)")
            raw = pd.read_parquet(cache_path)
            return _unpack(raw, symbols)

    # ── Download ──────────────────────────────────────────────────────────────
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    print(f"→ Downloading {len(symbols)} stocks from {start}…")

    raw = yf.download(
        symbols,
        start=start,
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=True,
    )
    raw.to_parquet(cache_path)
    print(f"✓ Saved to cache → {cache_path}")
    return _unpack(raw, symbols)


def _unpack(raw: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Unpack multi-symbol yfinance DataFrame into per-symbol dict."""
    result = {}
    multi = isinstance(raw.columns, pd.MultiIndex)

    for sym in symbols:
        try:
            df = raw[sym].copy() if multi else raw.copy()
            df = df.dropna()
            if len(df) > 10:
                df.columns = [c.lower() for c in df.columns]
                result[sym] = df
        except Exception:
            pass

    print(f"✓ {len(result)} symbols ready")
    return result