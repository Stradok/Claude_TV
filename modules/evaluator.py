"""
evaluator.py
────────────
Checks every parsed condition against the latest bar of a stock's DataFrame.
All conditions must be True for a stock to match (AND logic).
"""
import pandas as pd

_OPS = {
    "<":  lambda a, b: a <  b,
    ">":  lambda a, b: a >  b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def evaluate_conditions(df: pd.DataFrame, conditions: list[dict]) -> bool:
    """
    Returns True only if ALL conditions hold on the latest completed bar.
    Returns False on any missing column or bad data (safe default).
    """
    if len(df) < 2:
        return False

    cur  = df.iloc[-1]   # latest bar
    prev = df.iloc[-2]   # previous bar (needed for crossover/crossunder)

    for cond in conditions:
        try:
            t = cond["type"]

            if t == "threshold":
                # e.g. rsi_14 < 30
                val = float(cur[cond["column"]])
                if not _OPS[cond["operator"]](val, float(cond["value"])):
                    return False

            elif t == "comparison":
                # e.g. close > sma_200
                left  = float(cur[cond["left"]])
                right = float(cur[cond["right"]])
                if not _OPS[cond["operator"]](left, right):
                    return False

            elif t == "crossover":
                # fast crossed ABOVE slow on the last bar
                f_now, s_now   = float(cur[cond["fast"]]),  float(cur[cond["slow"]])
                f_prev, s_prev = float(prev[cond["fast"]]), float(prev[cond["slow"]])
                if not (f_now > s_now and f_prev <= s_prev):
                    return False

            elif t == "crossunder":
                # fast crossed BELOW slow on the last bar
                f_now, s_now   = float(cur[cond["fast"]]),  float(cur[cond["slow"]])
                f_prev, s_prev = float(prev[cond["fast"]]), float(prev[cond["slow"]])
                if not (f_now < s_now and f_prev >= s_prev):
                    return False

        except (KeyError, TypeError, ValueError):
            return False  # missing data → conservatively skip

    return True