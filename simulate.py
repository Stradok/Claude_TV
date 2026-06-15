#!/usr/bin/env python3
"""
simulate.py — Offline simulation tests for Claude × TradingView Scanner.
Tests every module with synthetic data and a mocked Claude response.
No API calls, no network, no tokens consumed.
"""
import sys, os, json, hashlib, traceback
import numpy as np
import pandas as pd

PASS = 0
FAIL = 0

def ok(name):
    global PASS
    PASS += 1
    print(f"  ✓  {name}")

def fail(name, reason):
    global FAIL
    FAIL += 1
    print(f"  ✗  {name}: {reason}")


# ── Build synthetic OHLCV data ────────────────────────────────────────────────
def make_ohlcv(n=300, trend="up", rsi_target=25):
    """Generate n bars of synthetic OHLCV.  trend='up' makes price rise slowly."""
    np.random.seed(42)
    close = np.full(n, 100.0)
    for i in range(1, n):
        close[i] = close[i-1] * (1 + np.random.normal(0.001 if trend == "up" else -0.001, 0.012))

    # Force last few bars to have low RSI (make price drop hard at end)
    if rsi_target == "low":
        for i in range(n-15, n):
            close[i] = close[i-1] * 0.992   # persistent drop → RSI will be low

    high   = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low    = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_  = close * (1 + np.random.normal(0, 0.003, n))
    volume = np.random.randint(500_000, 5_000_000, n).astype(float)

    df = pd.DataFrame({
        "open":   open_,
        "high":   high,
        "low":    low,
        "close":  close,
        "volume": volume,
    })
    df.index = pd.date_range("2024-01-01", periods=n, freq="B")
    return df


# ── Pre-baked parsed strategy (mirrors what Claude would return) ──────────────
MOCK_PARSED = {
    "summary": "RSI 14 below 30 AND price above 200-day SMA",
    "indicators": [
        {"name": "RSI",  "period": 14,  "column": "rsi_14",  "source": "close"},
        {"name": "SMA",  "period": 200, "column": "sma_200", "source": "close"},
    ],
    "conditions": [
        {"type": "threshold",  "column": "rsi_14",  "operator": "<", "value": 30,      "label": "RSI(14) < 30"},
        {"type": "comparison", "left":   "close",   "operator": ">", "right": "sma_200","label": "Price > SMA200"},
    ],
    "timeframe": "Daily",
    "lookback_bars": 50,
    "pine_script": "//@version=5\nindicator('RSI Strategy', overlay=true)",
}


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 1 — indicator_engine: RSI and SMA calculate without error
# ════════════════════════════════════════════════════════════════════════════════
def test_indicator_engine():
    sys.path.insert(0, "/home/amman/Desktop/claude_TV")
    from modules.indicator_engine import calculate_indicators

    df = make_ohlcv(300)
    indicators = MOCK_PARSED["indicators"]
    df = calculate_indicators(df.copy(), indicators)

    assert "rsi_14"  in df.columns, "rsi_14 column missing"
    assert "sma_200" in df.columns, "sma_200 column missing"

    last_rsi = df["rsi_14"].dropna().iloc[-1]
    last_sma = df["sma_200"].dropna().iloc[-1]

    assert 0 < last_rsi < 100,     f"RSI out of range: {last_rsi:.2f}"
    assert last_sma > 0,           f"SMA not positive: {last_sma:.2f}"

    ok(f"indicator_engine — RSI={last_rsi:.1f}, SMA200={last_sma:.2f}")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 2 — evaluator: a stock that SHOULD match returns True
# ════════════════════════════════════════════════════════════════════════════════
def test_evaluator_match():
    from modules.indicator_engine import calculate_indicators
    from modules.evaluator import evaluate_conditions

    # Use uptrend (price > SMA200) + forced RSI drop at end
    df = make_ohlcv(300, trend="up", rsi_target="low")
    df = calculate_indicators(df.copy(), MOCK_PARSED["indicators"])

    # Manually force the last bar to match: rsi_14 < 30 and close > sma_200
    df = df.dropna()
    df.loc[df.index[-1], "rsi_14"]  = 25.0          # force RSI under 30
    df.loc[df.index[-1], "sma_200"] = df["close"].iloc[-1] * 0.95  # force price > SMA

    result = evaluate_conditions(df, MOCK_PARSED["conditions"])
    assert result is True, "Expected match=True"
    ok("evaluator — forced match returns True")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 3 — evaluator: a stock that should NOT match returns False
# ════════════════════════════════════════════════════════════════════════════════
def test_evaluator_no_match():
    from modules.indicator_engine import calculate_indicators
    from modules.evaluator import evaluate_conditions

    df = make_ohlcv(300)
    df = calculate_indicators(df.copy(), MOCK_PARSED["indicators"])
    df = df.dropna()

    # Force RSI to 60 (well above 30) → condition should fail
    df.loc[df.index[-1], "rsi_14"] = 60.0

    result = evaluate_conditions(df, MOCK_PARSED["conditions"])
    assert result is False, "Expected match=False"
    ok("evaluator — RSI=60 correctly returns False")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 4 — evaluator: crossover detection
# ════════════════════════════════════════════════════════════════════════════════
def test_evaluator_crossover():
    from modules.evaluator import evaluate_conditions

    df = make_ohlcv(50)
    # Simulate EMA12 crossing above EMA26
    df["ema_12"] = 100.0
    df["ema_26"] = 101.0
    df.loc[df.index[-2], "ema_12"] = 99.0   # was below
    df.loc[df.index[-2], "ema_26"] = 101.0
    df.loc[df.index[-1], "ema_12"] = 102.0  # now above
    df.loc[df.index[-1], "ema_26"] = 101.0

    conditions = [{"type": "crossover", "fast": "ema_12", "slow": "ema_26", "label": "EMA12 x EMA26"}]
    result = evaluate_conditions(df, conditions)
    assert result is True, "Expected crossover=True"
    ok("evaluator — crossover detected correctly")


def test_evaluator_no_crossover():
    from modules.evaluator import evaluate_conditions

    df = make_ohlcv(50)
    df["ema_12"] = 100.0
    df["ema_26"] = 101.0  # fast stays below slow — no crossover

    conditions = [{"type": "crossover", "fast": "ema_12", "slow": "ema_26", "label": "EMA12 x EMA26"}]
    result = evaluate_conditions(df, conditions)
    assert result is False, "Expected crossover=False when no cross"
    ok("evaluator — no crossover correctly returns False")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 5 — strategy_parser cache (no real API call)
# ════════════════════════════════════════════════════════════════════════════════
def test_strategy_parser_cache():
    os.makedirs("/home/amman/Desktop/claude_TV/.cache", exist_ok=True)
    cache_file = "/home/amman/Desktop/claude_TV/.cache/strategy_parse.json"

    strategy_text = "RSI 14 below 30 AND price above 200-day SMA"
    strategy_hash = hashlib.md5(strategy_text.encode()).hexdigest()

    # Pre-seed the cache so no Claude call is made
    with open(cache_file, "w") as f:
        json.dump({"hash": strategy_hash, "result": MOCK_PARSED}, f)

    # Now import and call parse_strategy — it should hit cache
    # Temporarily set a dummy API key so Anthropic client doesn't error on init
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-sim-00000000000000000000"
    os.chdir("/home/amman/Desktop/claude_TV")

    from modules.strategy_parser import parse_strategy
    result = parse_strategy(strategy_text)

    assert result["summary"] == MOCK_PARSED["summary"]
    assert len(result["indicators"]) == 2
    assert len(result["conditions"]) == 2
    ok("strategy_parser — cache hit returns correct structure (0 tokens)")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 6 — reporter: formats without crashing
# ════════════════════════════════════════════════════════════════════════════════
def test_reporter():
    sys.path.insert(0, "/home/amman/Desktop/claude_TV")
    os.chdir("/home/amman/Desktop/claude_TV")
    from modules.reporter import format_results

    matches = [
        {"symbol": "AAPL", "close": 185.5,  "volume": 72_000_000},
        {"symbol": "MSFT", "close": 415.2,  "volume": 24_000_000},
        {"symbol": "TSLA", "close": 265.0,  "volume": 110_000_000},
    ]
    format_results(matches, MOCK_PARSED["summary"])
    ok("reporter — formats 3 matches without error")


def test_reporter_empty():
    from modules.reporter import format_results
    format_results([], MOCK_PARSED["summary"])
    ok("reporter — handles empty results without error")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 7 — data_fetcher _unpack: handles multi-index DataFrame
# ════════════════════════════════════════════════════════════════════════════════
def test_data_fetcher_unpack():
    sys.path.insert(0, "/home/amman/Desktop/claude_TV")
    from modules.data_fetcher import _unpack

    # Build fake multi-index DataFrame (mimics yfinance output: (ticker, column))
    syms = ["AAPL", "MSFT"]
    cols = pd.MultiIndex.from_product([syms, ["Open","High","Low","Close","Volume"]])
    data = np.random.rand(20, len(cols))
    raw  = pd.DataFrame(data, columns=cols)

    result = _unpack(raw, syms)
    assert "AAPL" in result, "AAPL missing from unpacked result"
    assert "MSFT" in result, "MSFT missing from unpacked result"
    assert "close" in result["AAPL"].columns, "lowercase 'close' missing"
    ok(f"data_fetcher — _unpack returned {len(result)} symbols with lowercase columns")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 8 — full pipeline dry-run (no network, no API)
# ════════════════════════════════════════════════════════════════════════════════
def test_full_pipeline_dryrun():
    """Simulates the scan() pipeline using synthetic data and mocked strategy."""
    from modules.indicator_engine import calculate_indicators
    from modules.evaluator import evaluate_conditions

    symbols_data = {}
    for sym in ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]:
        df = make_ohlcv(300, trend="up")
        df = calculate_indicators(df.copy(), MOCK_PARSED["indicators"])
        df = df.dropna()
        symbols_data[sym] = df

    # Force AAPL and TSLA to match
    for sym in ["AAPL", "TSLA"]:
        df = symbols_data[sym]
        df.loc[df.index[-1], "rsi_14"]  = 22.0
        df.loc[df.index[-1], "sma_200"] = df["close"].iloc[-1] * 0.90

    matches = []
    for sym, df in symbols_data.items():
        if evaluate_conditions(df, MOCK_PARSED["conditions"]):
            matches.append({"symbol": sym, "close": round(float(df["close"].iloc[-1]), 2), "volume": int(df["volume"].iloc[-1])})

    assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}: {[m['symbol'] for m in matches]}"
    assert {m["symbol"] for m in matches} == {"AAPL", "TSLA"}
    ok(f"full pipeline dry-run — correctly found {len(matches)} matches: {[m['symbol'] for m in matches]}")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 9 — MACD and Bollinger Bands indicators
# ════════════════════════════════════════════════════════════════════════════════
def test_macd_and_bb():
    from modules.indicator_engine import calculate_indicators

    df = make_ohlcv(300)
    indicators = [
        {"name": "MACD",    "period": 12, "column": "macd",     "source": "close"},
        {"name": "BBANDS",  "period": 20, "column": "bb_upper", "source": "close"},
        {"name": "STOCH",   "period": 14, "column": "stoch_k",  "source": "close"},
    ]
    df = calculate_indicators(df.copy(), indicators)

    assert "macd"        in df.columns, "macd missing"
    assert "macd_signal" in df.columns, "macd_signal missing"
    assert "bb_upper"    in df.columns, "bb_upper missing"
    assert "stoch_k"     in df.columns, "stoch_k missing"
    ok("indicator_engine — MACD, Bollinger Bands, Stochastic all calculated")


# ════════════════════════════════════════════════════════════════════════════════
#  TEST 10 — edge case: too-short DataFrame
# ════════════════════════════════════════════════════════════════════════════════
def test_evaluator_short_df():
    from modules.evaluator import evaluate_conditions

    df = make_ohlcv(1)   # only 1 bar — evaluator needs ≥2
    result = evaluate_conditions(df, MOCK_PARSED["conditions"])
    assert result is False, "Expected False for 1-bar DataFrame"
    ok("evaluator — 1-bar DataFrame safely returns False")


# ════════════════════════════════════════════════════════════════════════════════
#  RUN ALL
# ════════════════════════════════════════════════════════════════════════════════
TESTS = [
    ("indicator_engine — RSI + SMA",         test_indicator_engine),
    ("evaluator — forced match",             test_evaluator_match),
    ("evaluator — RSI too high no match",    test_evaluator_no_match),
    ("evaluator — crossover True",           test_evaluator_crossover),
    ("evaluator — crossover False",          test_evaluator_no_crossover),
    ("strategy_parser — cache (0 tokens)",   test_strategy_parser_cache),
    ("reporter — 3 matches",                 test_reporter),
    ("reporter — empty",                     test_reporter_empty),
    ("data_fetcher — _unpack multi-index",   test_data_fetcher_unpack),
    ("full pipeline dry-run",                test_full_pipeline_dryrun),
    ("MACD + BB + Stochastic indicators",    test_macd_and_bb),
    ("evaluator — 1-bar edge case",          test_evaluator_short_df),
]

if __name__ == "__main__":
    print("\n┌─ Simulation Tests (no API · no network · 0 tokens) ─────────────\n")
    for label, fn in TESTS:
        try:
            fn()
        except Exception as e:
            fail(label, str(e))
            traceback.print_exc()

    total = PASS + FAIL
    print(f"\n└─ {PASS}/{total} passed", "✓ ALL CLEAR" if FAIL == 0 else f"✗ {FAIL} FAILED")
    sys.exit(0 if FAIL == 0 else 1)
