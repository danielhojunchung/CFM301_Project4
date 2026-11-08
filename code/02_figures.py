"""Project 4: dual-axis figures of the Baa-Treasury spread vs. the Treasury liquidity proxy.

Run from repository root after 01_clean.py: python code/02_figures.py
Requires pandas, numpy, matplotlib. Reads data/clean/panel_monthly_complete.csv.

Writes:
    output/fig_original_2006_2009.png   (Requirement 5: slide 59 period)
    output/fig_extended.png             (Requirement 6: longest available sample)

Series are monthly averages of same-date daily observations (see 01_clean.py).
Left axis: credit spread in percent. Right axis: liquidity proxy in basis points.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # no display needed; makes the script run headless
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

START_ORIGINAL, END_ORIGINAL = "2006-01", "2009-12"
SPREAD, LIQ = "credit_spread_pct", "liquidity_proxy_bp"
SPREAD_COLOR, LIQ_COLOR = "#111111", "#D62728"

m = pd.read_csv(CLEAN / "panel_monthly_complete.csv")
m["date"] = pd.PeriodIndex(m["month"], freq="M").to_timestamp()
m = m.set_index("date").sort_index()
# Reindex to every calendar month so any month without data shows as a gap
# in the line instead of being silently bridged.
m = m.reindex(pd.date_range(m.index.min(), m.index.max(), freq="MS"))


def dual_axis_plot(df, title, path, date_fmt, locator):
    pair = df[[SPREAD, LIQ]].dropna()
    corr = pair[SPREAD].corr(pair[LIQ])
    first, last = pair.index.min(), pair.index.max()

    fig, ax1 = plt.subplots(figsize=(10, 5.2))
    ax2 = ax1.twinx()
    l1, = ax1.plot(df.index, df[SPREAD], color=SPREAD_COLOR, lw=2,
                   label="Baa − 20y Treasury spread (left axis, %)")
    l2, = ax2.plot(df.index, df[LIQ], color=LIQ_COLOR, lw=2, ls="--",
                   label="Liquidity proxy: off-the-run fitted − CMT 20y (right axis, bp)")

    ax1.set_ylabel("Baa − Treasury spread (%)", color=SPREAD_COLOR)
    ax2.set_ylabel("Liquidity proxy (bp)", color=LIQ_COLOR)
    ax1.tick_params(axis="y", colors=SPREAD_COLOR)
    ax2.tick_params(axis="y", colors=LIQ_COLOR)
    ax2.spines["right"].set_color(LIQ_COLOR)
    for ax in (ax1, ax2):
        ax.spines["top"].set_visible(False)
    ax1.grid(axis="y", color="#DDDDDD", lw=0.8)
    ax1.set_axisbelow(True)
    ax1.xaxis.set_major_locator(locator)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
    ax1.set_xlim(df.index.min(), df.index.max())

    ax1.set_title(f"{title}\nCorr = {corr:.2f}  (monthly, n = {len(pair)}, "
                  f"{first:%b %Y}–{last:%b %Y})", fontsize=13, fontweight="bold")
    # Legend below the plot area so it never covers either line.
    fig.legend(handles=[l1, l2], loc="lower center", ncol=2, frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, 0.035))
    fig.text(0.01, 0.01, "Sources: FRED (DBAA, DGS20); Federal Reserve Gürkaynak-Sack-Wright "
             "yield curve (SVENPY20). Monthly averages of same-date daily data.",
             fontsize=7.5, color="#555555")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"{path.relative_to(ROOT)}: corr = {corr:.4f}, n = {len(pair)}, "
          f"{first:%Y-%m} to {last:%Y-%m}")
    return corr


original = m.loc[START_ORIGINAL:END_ORIGINAL]
dual_axis_plot(original, "Baa−Treasury Yield Spread and Treasury Liquidity, 2006–2009",
               OUTPUT / "fig_original_2006_2009.png",
               "%m-%y", mdates.MonthLocator(bymonth=[1, 4, 7, 10]))

dual_axis_plot(m, "Baa−Treasury Yield Spread and Treasury Liquidity, Full Sample",
               OUTPUT / "fig_extended.png",
               "%Y", mdates.YearLocator(base=3))
