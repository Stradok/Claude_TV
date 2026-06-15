"""
strategy_parser.py
─────────────────
Converts plain-English trading strategies into structured JSON conditions
using the Claude API.  After the first parse, results are cached by MD5
hash of the strategy text — so repeat runs cost 0 tokens.
"""
import json
import hashlib
import os
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS

client = Anthropic(api_key=ANTHROPIC_API_KEY)

_CACHE_FILE = ".cache/strategy_parse.json"

# ── System prompt: concise = fewer tokens ───────────────────────────────────
_SYSTEM = """\
Parse a trading strategy to JSON only — no markdown, no preamble.

Return exactly this shape:
{
  "summary": "one-sentence description",
  "indicators": [
    {"name": "RSI",  "period": 14, "column": "rsi_14",  "source": "close"},
    {"name": "EMA",  "period": 20, "column": "ema_20",  "source": "close"},
    {"name": "SMA",  "period": 200,"column": "sma_200", "source": "close"}
  ],
  "conditions": [
    {"type":"threshold",  "column":"rsi_14",  "operator":"<", "value":30,      "label":"RSI(14) < 30"},
    {"type":"crossover",  "fast":"ema_20",    "slow":"sma_200",                "label":"EMA20 crosses SMA200"},
    {"type":"crossunder", "fast":"ema_20",    "slow":"sma_200",                "label":"EMA20 crosses under SMA200"},
    {"type":"comparison", "left":"close",     "operator":">", "right":"sma_200","label":"Price > SMA200"}
  ],
  "timeframe": "Daily",
  "lookback_bars": 50,
  "pine_script": "//@version=5\\nindicator('Strategy', overlay=true)\\n..."
}

Rules:
- condition types: threshold | crossover | crossunder | comparison
- operators: < > <= >= == !=
- source options: close open high low volume
- indicator names: RSI EMA SMA MACD BBANDS ATR STOCH VWAP
- for volume-based SMA use source:"volume"
- pine_script: complete, runnable Pine Script v5 for TradingView
"""


def parse_strategy(strategy_text: str) -> dict:
    """
    Parse natural language strategy → structured conditions dict.
    Caches result by strategy MD5 hash; repeat calls cost 0 tokens.
    """
    os.makedirs(".cache", exist_ok=True)
    strategy_hash = hashlib.md5(strategy_text.encode()).hexdigest()

    # ── Cache hit ────────────────────────────────────────────────────────────
    if os.path.exists(_CACHE_FILE):
        with open(_CACHE_FILE) as f:
            cached = json.load(f)
        if cached.get("hash") == strategy_hash:
            print("✓ Strategy loaded from cache (0 tokens used)")
            return cached["result"]

    # ── Call Claude ──────────────────────────────────────────────────────────
    print("→ Parsing strategy with Claude API…")
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_SYSTEM,
        messages=[{"role": "user", "content": strategy_text}],
    )

    raw_text = response.content[0].text.strip()
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    # Strip accidental markdown fences
    clean = raw_text.replace("```json", "").replace("```", "").strip()
    result = json.loads(clean)

    # ── Cache for next run ────────────────────────────────────────────────────
    with open(_CACHE_FILE, "w") as f:
        json.dump({"hash": strategy_hash, "result": result}, f, indent=2)

    print(f"✓ Parsed in {tokens_used} tokens — cached to {_CACHE_FILE}")
    return result