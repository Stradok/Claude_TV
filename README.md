# Claude_TV
A Claude integration with trading view. 
# Claude × TradingView Stock Scanner

Describe a trading strategy in plain English → Claude parses it into structured conditions → scans NYSE/NASDAQ stocks → returns only the ones that match.

---

## How It Works

```
"RSI 14 below 30 AND close above 200 SMA"
              │
              ▼
   [strategy_parser.py]      Claude API — 1 call, result cached by MD5 hash
              │  JSON conditions + indicator list
              ▼
   [screener.py]             TradingView screener → NYSE/NASDAQ universe (~300 stocks)
              │  symbol list
              ▼
   [data_fetcher.py]         yfinance batch download, cached as parquet (6-hour TTL)
              │  OHLCV DataFrames
              ▼
   [indicator_engine.py]     `ta` library — only calculates what the strategy needs
              │  RSI, SMA, EMA, MACD, Bollinger, Stochastic, VWAP, OBV, ATR
              ▼
   [evaluator.py]            Condition check on latest bar (8 parallel threads)
              │  matching stocks
              ▼
   [reporter.py]             Terminal table + timestamped CSV saved to disk
```

---

## Prerequisites

- Python 3.10 or newer (tested on 3.14)
- Internet connection (for stock data download and Claude API)
- An Anthropic API key with credits loaded

> **Important:** Claude Pro (the chat subscription at claude.ai) and the Anthropic API are billed separately. Even with a Pro account you need to add API credits at console.anthropic.com → Plans & Billing. A single scan costs roughly $0.01.

---

## Setup (First Time)

```bash
# Clone or download the project, then:
cd claude_TV

# Run the setup script — creates venv, installs deps, runs offline tests
bash setup.sh
```

The setup script:
1. Checks your Python version
2. Creates a virtual environment at `.venv/` (required on Python 3.12+ due to PEP 668)
3. Installs all dependencies inside the venv
4. Runs 12 offline simulation tests (zero tokens, no API needed)
5. Prints next steps

### Manual setup (if you prefer step by step)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run offline simulations to verify everything works
python simulate.py
```

---

## API Key Setup

### Step 1 — Get a key

1. Go to **https://console.anthropic.com**
2. Click **API Keys** → **Create Key**
3. Copy the key (starts with `sk-ant-`)

### Step 2 — Add API credits

Even with Claude Pro, the API needs its own credit balance:

1. Go to **console.anthropic.com → Plans & Billing**
2. Click **Add Credits** — minimum $5 is enough for hundreds of scans

### Step 3 — Set the key (choose one method)

**Session only** (key is gone when terminal closes):
```bash
export ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
```

**Permanent** (survives terminal restarts):
```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE' >> ~/.bashrc
source ~/.bashrc
```

**Verify it's set:**
```bash
echo $ANTHROPIC_API_KEY
```

> Never hardcode the key directly in `config.py` — if you share the file or commit it to git, the key will be exposed.

---

## Running the Scanner

Always use `.venv/bin/python` (not `python3`) so you get the installed packages:

```bash
# Basic run — full universe (~300 stocks)
.venv/bin/python main.py "RSI 14 below 30 AND close above 200 SMA"

# Interactive mode — prompts you to type the strategy
.venv/bin/python main.py

# Limit stock count (faster, cheaper for testing)
.venv/bin/python main.py "RSI below 30" --limit 50

# Load strategy from a text file
.venv/bin/python main.py strategy.txt
```

If you activated the venv with `source .venv/bin/activate`, you can drop `.venv/bin/` and just use `python`:

```bash
source .venv/bin/activate
python main.py "RSI 14 below 30 AND close above 200 SMA"
```

---

## Running Offline Simulations (No API Required)

Before spending any tokens, verify the entire pipeline works with synthetic data:

```bash
.venv/bin/python simulate.py
```

Expected output:
```
┌─ Simulation Tests (no API · no network · 0 tokens) ─────────────

  ✓  indicator_engine — RSI=61.4, SMA200=112.95
  ✓  evaluator — forced match returns True
  ✓  evaluator — RSI=60 correctly returns False
  ✓  evaluator — crossover detected correctly
  ✓  evaluator — no crossover correctly returns False
  ✓  strategy_parser — cache hit returns correct structure (0 tokens)
  ✓  reporter — formats 3 matches without error
  ✓  reporter — handles empty results without error
  ✓  data_fetcher — _unpack returned 2 symbols with lowercase columns
  ✓  full pipeline dry-run — correctly found 2 matches: ['AAPL', 'TSLA']
  ✓  indicator_engine — MACD, Bollinger Bands, Stochastic all calculated
  ✓  evaluator — 1-bar DataFrame safely returns False

└─ 12/12 passed ✓ ALL CLEAR
```

All 12 must pass before running live.

---

## Strategy Examples

```bash
# Oversold stocks in an uptrend
.venv/bin/python main.py "RSI 14 below 30 AND close above 200 SMA"

# MACD bullish crossover
.venv/bin/python main.py "MACD line crosses above signal line AND RSI below 60"

# EMA crossover with VWAP confirmation
.venv/bin/python main.py "EMA 12 crosses above EMA 26 AND close above VWAP"

# Bollinger Band breakout
.venv/bin/python main.py "Close above upper Bollinger Band AND RSI below 80"

# Stochastic oversold
.venv/bin/python main.py "Stochastic K below 20 AND close above 50 SMA"

# Quick test — only 50 stocks
.venv/bin/python main.py "RSI below 30" --limit 50
```

**Supported indicators:** RSI, SMA, EMA, MACD, Bollinger Bands, Stochastic, VWAP, OBV, ATR

**Supported condition types:**
- `threshold` — indicator vs. number (e.g. RSI < 30)
- `comparison` — indicator vs. indicator (e.g. close > SMA200)
- `crossover` — fast line crossed above slow (e.g. EMA12 > EMA26, was below)
- `crossunder` — fast line crossed below slow

---

## Token Cost

| Action | Tokens |
|--------|--------|
| First run (strategy parse) | ~300–500 |
| Same strategy, any subsequent run | **0** (cache hit) |
| Data download / indicator calc / screening | **0** (all local) |

The strategy is cached by MD5 hash in `.cache/strategy_parse.json`. Running the same strategy twice costs nothing after the first call.

---

## Output

Results are printed to terminal and saved as a CSV:

```
══════════════════════════════════════════════════════════
  SCAN RESULTS  ·  2026-06-15 14:30
  Strategy : RSI 14 below 30 AND price above 200-day SMA
══════════════════════════════════════════════════════════

  ✓  3 stock(s) matched:

  symbol   close     volume
  AAPL    185.50   72000000
  MSFT    415.20   24000000
  TSLA    265.00  110000000

  Saved → results_20260615_143012.csv
```

---

## Project Structure

```
claude_TV/
├── main.py                    # Pipeline orchestrator — run this
├── simulate.py                # Offline tests — run before live
├── config.py                  # All settings (model, limits, cache)
├── setup.sh                   # One-time setup script
├── requirements.txt           # Python dependencies
├── .venv/                     # Virtual environment (created by setup.sh)
├── .cache/
│   ├── strategy_parse.json    # Cached Claude strategy parses
│   └── data/                  # Cached yfinance OHLCV parquet files
└── modules/
    ├── strategy_parser.py     # NL → JSON via Claude API
    ├── screener.py            # TradingView stock universe
    ├── data_fetcher.py        # yfinance OHLCV download + cache
    ├── indicator_engine.py    # Technical indicators (ta library)
    ├── evaluator.py           # Condition evaluation on latest bar
    └── reporter.py            # Terminal output + CSV export
```

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL` | `claude-sonnet-4-6` | Claude model for strategy parsing |
| `MAX_TOKENS` | `1000` | Max tokens for strategy parse response |
| `MIN_MARKET_CAP` | `$1B` | Filters out micro-caps |
| `MIN_VOLUME` | `500,000` | Daily volume floor |
| `MAX_STOCKS` | `300` | Max stocks in universe |
| `CACHE_HOURS` | `6` | Hours before market data is re-fetched |
| `PARALLEL_WORKERS` | `8` | Threads for parallel scanning |

---

## Troubleshooting

**`externally-managed-environment` error when running pip**
> Python 3.12+ blocks system-wide pip installs. Use the venv:
> ```bash
> python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
> ```

**`credit balance is too low` error**
> API credits are separate from Claude Pro. Add credits at:
> console.anthropic.com → Plans & Billing → Add Credits

**`ANTHROPIC_API_KEY` not set**
> Run: `export ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE`
> Or add it permanently to `~/.bashrc`

**Strategy cache returning stale results**
> Delete the cache file and re-run:
> ```bash
> rm .cache/strategy_parse.json
> ```

**No stocks matched**
> - Try `--limit 50` to confirm the pipeline runs end to end
> - Relax the strategy conditions (e.g. `RSI below 40` instead of `below 30`)
> - Market data is cached — delete `.cache/data/` to force a fresh download

**Simulations fail**
> Check that dependencies are installed inside the venv:
> ```bash
> .venv/bin/pip install -r requirements.txt
> ```
