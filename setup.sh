#!/bin/bash
# setup.sh — One-time setup for Claude × TradingView Scanner
set -e

echo "─────────────────────────────────────────────"
echo "  Claude × TradingView Scanner — Setup"
echo "─────────────────────────────────────────────"
echo ""

# ── 1. Python version check ────────────────────────────────────────────────────
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 not found. Install Python 3.10 or newer."
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
echo "✓ Found $PY_VERSION"

# ── 2. Create virtual environment ──────────────────────────────────────────────
# Required on Python 3.12+ (PEP 668 blocks system-wide pip installs)
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment (.venv)…"
    $PYTHON -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists (.venv)"
fi

# ── 3. Install dependencies ────────────────────────────────────────────────────
echo "→ Installing dependencies…"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# ── 4. Create cache directories ────────────────────────────────────────────────
mkdir -p .cache/data
echo "✓ Cache directories ready"

# ── 5. Run simulations (offline self-test) ─────────────────────────────────────
echo ""
echo "→ Running offline simulations (0 tokens, no API needed)…"
.venv/bin/python simulate.py
SIM_EXIT=$?
if [ $SIM_EXIT -ne 0 ]; then
    echo ""
    echo "ERROR: Simulations failed. Check output above before running live."
    exit 1
fi

# ── 6. API key reminder ────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────"
echo "  Setup complete!"
echo "─────────────────────────────────────────────"
echo ""
echo "NEXT STEP — Set your Anthropic API key:"
echo ""
echo "  Method 1 (recommended — session only):"
echo "    export ANTHROPIC_API_KEY=sk-ant-..."
echo ""
echo "  Method 2 (permanent — add to ~/.bashrc):"
echo "    echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.bashrc"
echo "    source ~/.bashrc"
echo ""
echo "Get a key at: https://console.anthropic.com → API Keys"
echo "Note: API credits are separate from a Claude Pro subscription."
echo ""
echo "Then run:"
echo "  .venv/bin/python main.py \"RSI 14 below 30 AND price above 200 SMA\""
echo ""
