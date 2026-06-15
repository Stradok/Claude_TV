"""
reporter.py
───────────
Formats scan results to terminal and saves a timestamped CSV.
"""
import pandas as pd
from datetime import datetime


def format_results(matches: list[dict], strategy_summary: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("\n" + "═" * 58)
    print(f"  SCAN RESULTS  ·  {ts}")
    print(f"  Strategy : {strategy_summary}")
    print("═" * 58)

    if not matches:
        print("\n  ✗  No stocks matched the strategy conditions.\n")
        return

    df = (
        pd.DataFrame(matches)
        .sort_values("close", ascending=False)
        .reset_index(drop=True)
    )
    df.index += 1

    print(f"\n  ✓  {len(matches)} stock(s) matched:\n")
    print(df.to_string())

    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"\n  💾 Saved → {filename}\n")