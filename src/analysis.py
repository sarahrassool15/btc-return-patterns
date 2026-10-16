"""
S1: BTC stylized facts
Do Bitcoin returns show the same statistical patterns as other markets?
Testing three of the following patterns on BTC/USDT from Binance US:
  1. Returns are (almost) uncorrelated  
  2. Volatility clusters                
  3. Fat tails                          


Note to self: fact 2 is important for us to see  WHY realized vol dominated my TML crypto paper.
Recall: Current volatility predicts future volatility because volatility clusters! 
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.tsa.stattools import acf

# how long one candle should be at each frequency
# (I use this to spot missing candles)
step = {"1m": "1min", "1h": "1h", "1d": "1D"}

results = {}

for interval in ["1m", "1h", "1d"]:
    df = pd.read_csv(f"data/btcusdt_{interval}.csv", index_col="open_time", parse_dates=True)

    # log returns: ln(P_t / P_t-1)
    # I use logs because they add up over time and are the standard in finance
    returns = np.log(df["close"]).diff()

    # NOTE: Binance US has a few missing candles (exchange downtime / no trades).
    # If 10:04 is missing, the 10:03 -> 10:05 move would look like ONE return
    # and inflate the tails. So I only keep returns where the time gap is exactly one candle.
    gap_ok = df.index.to_series().diff() == pd.Timedelta(step[interval])
    returns = returns[gap_ok].dropna()

    # summary stats
    # kurtosis = 3 for a normal distribution, so anything well above 3 = fat tails (fact 3)
    # fisher=False gives "regular" kurtosis (default would subtract 3)
    results[interval] = {
        "n": len(returns),
        "dropped_gaps": int((~gap_ok).sum()) - 1,  # -1 because the first row has no previous candle
        "mean": returns.mean(),
        "std": returns.std(),
        "skew": stats.skew(returns),
        "kurtosis": stats.kurtosis(returns, fisher=False),
    }

    # I only make the plots with hourly data:
    # enough points for a clean picture, without the noise of 1-minute data
    if interval == "1h":
        hourly = returns

# ---------- fig 1: autocorrelation (facts 1 and 2) ----------
lags = 100
acf_returns = acf(hourly, nlags=lags)[1:]        # [1:] skips lag 0, which is always 1
acf_abs = acf(hourly.abs(), nlags=lags)[1:]      # absolute returns = size of the move

# 95% band: if there were NO autocorrelation, values should stay inside +/- 1.96/sqrt(n)
band = 1.96 / np.sqrt(len(hourly))

fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
axes[0].bar(range(1, lags + 1), acf_returns)
axes[0].set_title("Returns (1h)")
axes[1].bar(range(1, lags + 1), acf_abs)
axes[1].set_title("Absolute returns (1h)")
for ax in axes:
    ax.axhline(band, color="grey", linestyle="--")
    ax.axhline(-band, color="grey", linestyle="--")
    ax.set_xlabel("Lag (hours)")
axes[0].set_ylabel("Autocorrelation")
fig.suptitle("Returns are uncorrelated, but their size is not")
fig.tight_layout()
fig.savefig("figures/acf_1h.png", dpi=150)

# ---------- fig 2: fat tails (fact 3) ----------
# standardize so the returns have mean 0, std 1 -> directly comparable to a standard normal
z = (hourly - hourly.mean()) / hourly.std()
x = np.linspace(-8, 8, 400)

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(z, bins=200, range=(-8, 8), density=True, alpha=0.6, label="BTC (1h)")
axes[0].plot(x, stats.norm.pdf(x), label="Normal")
axes[0].set_yscale("log")    # NOTE: log scale is the trick, otherwise the tails are invisible
axes[0].set_ylim(1e-5, 1)
axes[0].set_xlabel("Standardized return")
axes[0].legend()
axes[0].set_title("Density (log scale)")

# QQ plot: if returns were normal, the dots would sit on the straight line
# dots bending away at both ends = fat tails
stats.probplot(z, dist="norm", plot=axes[1])
axes[1].set_title("QQ plot vs normal")
fig.suptitle("Extreme moves are far more common than a normal distribution predicts")
fig.tight_layout()
fig.savefig("figures/tails_1h.png", dpi=150)

# ---------- Table: summary stats at all three frequencies ----------
# bonus fact: kurtosis should FALL from 1m -> 1h -> 1d (aggregational Gaussianity)
table = pd.DataFrame(results).T
table.to_csv("figures/summary_stats.csv")
print(table.round(6))