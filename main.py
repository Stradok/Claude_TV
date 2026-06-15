#!/usr/bin/env python3
"""
main.py — Claude × TradingView Stock Scanner
─────────────────────────────────────────────
Usage:
  python main.py                              # interactive prompt
  python main.py "RSI 14 below 30"           # inline strategy
  python main.py strategy.txt                # load from file
  python main.py "RSI below 30" --limit 50  # scan first N stocks only
"""
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.strategy_parser   import parse_strategy
from modules.screener          import get_stock_universe
from modules.data_fetcher      import fetch_stock_data
from modules.indicator_engine  import calculate_indicators
from modules.evaluator         import evaluate_conditions
from modules.reporter          import format_results
from config                    import PARALLEL_WORKERS


# ── Per-stock worker (runs in thread pool) ────────────────────────────────────
def _scan_one(args: tuple) -> dict | None:
    symbol, df, conditions, indicators = args
    df = calculate_indicators(df.copy(), indicators)
    if evaluate_conditions(df, conditions):
        return {
            "symbol": symbol,
            "close":  round(float(df["close"].iloc[-1]), 2),
            "volume": int(df["volume"].iloc[-1]),
        }
    return None


# ── Main pipeline ─────────────────────────────────────────────────────────────
def scan(strategy_text: str, limit: int | None = None) -> list[dict]:
    print("\n┌─ Claude × TradingView Scanner ─────────────────────")

    # 1. Parse strategy — Claude API (cached after first call)
    parsed = parse_strategy(strategy_text)
    print(f"│  Summary    : {parsed['summary']}")
    print(f"│  Indicators : {[i['name'] for i in parsed['indicators']]}")
    print(f"│  Conditions : {len(parsed['conditions'])}")
    print(f"│  Timeframe  : {parsed['timeframe']}")
    print("│")

    # 2. Stock universe
    symbols = get_stock_universe()
    if limit:
        symbols = symbols[:limit]
        print(f"  (limited to first {limit} stocks)")

    # 3. OHLCV data — cached locally
    lookback_days = parsed.get("lookback_bars", 50) * 2   # 2× buffer for indicators
    stock_data = fetch_stock_data(symbols, lookback_days)

    # 4. Parallel scan
    print(f"\n→ Scanning {len(stock_data)} stocks with {PARALLEL_WORKERS} threads…")
    matches = []
    tasks   = [
        (sym, df, parsed["conditions"], parsed["indicators"])
        for sym, df in stock_data.items()
    ]

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {executor.submit(_scan_one, t): t[0] for t in tasks}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  … {done}/{len(tasks)}")
            result = future.result()
            if result:
                matches.append(result)

    # 5. Report
    format_results(matches, parsed["summary"])
    return matches


# ── CLI entry ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude × TradingView Stock Scanner")
    parser.add_argument("strategy", nargs="?", help="Strategy text or path to .txt file")
    parser.add_argument("--limit",  type=int,   help="Max stocks to scan")
    args = parser.parse_args()

    strategy = args.strategy

    if strategy is None:
        print("📊 Claude × TradingView Stock Scanner")
        print("Describe your strategy and press Enter:\n")
        strategy = input("> ").strip()
    elif strategy.endswith(".txt"):
        with open(strategy) as f:
            strategy = f.read().strip()

    if not strategy:
        print("No strategy provided. Exiting.")
        sys.exit(1)

    scan(strategy, args.limit)