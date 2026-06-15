"""
config.py — All settings in one file. Tweak here, nothing else needs to change.
"""
import os

# ── Claude API ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"   # efficient & cheap
MAX_TOKENS        = 1000                  # enough for strategy JSON + Pine Script

# ── TradingView Screener ────────────────────────────────────────────────────
MIN_MARKET_CAP   = 1_000_000_000   # $1B — filter out micro-caps
MIN_VOLUME       = 500_000          # daily volume floor
MAX_STOCKS       = 300              # max stocks to scan (raise for broader coverage)
EXCHANGES        = ["NYSE", "NASDAQ"]

# ── Data Cache ──────────────────────────────────────────────────────────────
DATA_CACHE_DIR   = ".cache/data"
CACHE_HOURS      = 6                # hours before market data is re-fetched

# ── Scanner Performance ─────────────────────────────────────────────────────
PARALLEL_WORKERS = 8                # threads for parallel indicator + eval