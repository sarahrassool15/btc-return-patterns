"""Download BTC/USDT candlestick data from the Binance US public API."""

import time
from datetime import datetime, timezone

import pandas as pd
import requests

URL = "https://api.binance.us/api/v3/klines"
COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "n_trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def fetch_klines(symbol, interval, start, end):
    """Fetch all candles between start and end, 1,000 at a time."""
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    rows = []

    while start_ms < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1000,
        }
        response = requests.get(URL, params=params, timeout=10)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        start_ms = batch[-1][0] + 1  # next request starts after the last candle
        time.sleep(0.2)              # stay well under the API rate limit

    df = pd.DataFrame(rows, columns=COLUMNS)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    numeric = ["open", "high", "low", "close", "volume",
               "quote_volume", "taker_buy_base", "taker_buy_quote"]
    df[numeric] = df[numeric].astype(float)
    df["n_trades"] = df["n_trades"].astype(int)
    df = (df.drop(columns=["close_time", "ignore"])
            .drop_duplicates("open_time")
            .set_index("open_time"))
    return df


if __name__ == "__main__":
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    windows = {
        "1m": datetime(2026, 7, 3, tzinfo=timezone.utc),   # ~90 days
        "1h": datetime(2024, 10, 1, tzinfo=timezone.utc),  # 2 years
        "1d": datetime(2024, 10, 1, tzinfo=timezone.utc),  # 2 years
    }
    for interval, start in windows.items():
        df = fetch_klines("BTCUSDT", interval, start, end)
        df.to_csv(f"data/btcusdt_{interval}.csv")
        print(f"{interval}: {len(df):,} rows, {df.index.min()} to {df.index.max()}")