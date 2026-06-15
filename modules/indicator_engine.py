"""
indicator_engine.py
────────────────────
Calculates technical indicators using the `ta` library (Python 3.14 compatible).
Replaces pandas-ta which is broken on Python 3.12+.
"""
import pandas as pd
import ta


def calculate_indicators(df: pd.DataFrame, indicators: list[dict]) -> pd.DataFrame:
    """
    Attach indicator columns to df based on parsed strategy indicators list.
    Only calculates what the strategy actually needs — no wasted compute.
    """
    for ind in indicators:
        name   = ind["name"].upper().replace("-", "").replace("_", "").replace(" ", "")
        col    = ind["column"]
        p      = ind.get("period", 14)
        source = ind.get("source", "close")
        series = df[source]  # use the specified price source

        try:
            if name == "RSI":
                df[col] = ta.momentum.RSIIndicator(series, window=p).rsi()

            elif name == "EMA":
                df[col] = ta.trend.EMAIndicator(series, window=p).ema_indicator()

            elif name == "SMA":
                df[col] = ta.trend.SMAIndicator(series, window=p).sma_indicator()

            elif name == "ATR":
                df[col] = ta.volatility.AverageTrueRange(
                    df["high"], df["low"], df["close"], window=p
                ).average_true_range()

            elif name in ("MACD",):
                m = ta.trend.MACD(series)
                df["macd"]        = m.macd()
                df["macd_signal"] = m.macd_signal()
                df["macd_hist"]   = m.macd_diff()

            elif name in ("BBANDS", "BB", "BOLLINGER"):
                bb = ta.volatility.BollingerBands(series, window=p)
                df["bb_upper"] = bb.bollinger_hband()
                df["bb_mid"]   = bb.bollinger_mavg()
                df["bb_lower"] = bb.bollinger_lband()

            elif name in ("STOCH", "STOCHASTIC"):
                st = ta.momentum.StochasticOscillator(
                    df["high"], df["low"], df["close"], window=p
                )
                df["stoch_k"] = st.stoch()
                df["stoch_d"] = st.stoch_signal()

            elif name == "VWAP":
                df[col] = ta.volume.VolumeWeightedAveragePrice(
                    df["high"], df["low"], df["close"], df["volume"]
                ).volume_weighted_average_price()

            elif name in ("OBV",):
                df[col] = ta.volume.OnBalanceVolumeIndicator(
                    series, df["volume"]
                ).on_balance_volume()

        except Exception as e:
            print(f"  ⚠ Indicator {name}({p}) failed for this stock: {e}")

    return df