"""Project 4: dual-axis figures of the Baa-Treasury spread vs. the Treasury liquidity proxy.

Run from repository root after 01_clean.py: python code/02_figures.py
Requires pandas, matplotlib. Reads data/clean/panel_monthly_complete.csv.

Writes:
    output/fig_replication.png          (report figure: both panels below, stacked)
    output/fig_original_2006_2009.png   (Requirement 5: slide period, Jan 2006 - Oct 2009)
    output/fig_extended.png             (Requirement 6: longest available sample)

Liquidity proxy is the 10y one, SVENPY10 - DGS10 (bp): DGS10 is always based on the
newly issued (on-the-run) 10-year note, so the proxy is consistent over the whole
sample. The 20y proxy is a robustness check only (see 03_crisis_analysis.py).
Series are monthly averages of same-date daily observations (see 01_clean.py).
Left axis: credit spread (Baa - 20y Treasury) in percent. Right axis: proxy in bp.
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

# The slide's chart data run Jan 2006 - Oct 2009 (read from Ch 9 Bonds.pptx in 03).
START_ORIGINAL, END_ORIGINAL = "2006-01", "2009-10"
SPREAD, LIQ = "credit_spread_pct", "liquidity_proxy10_bp"
SPREAD_COLOR, LIQ_COLOR = "#111111", "#D62728"
SPREAD_LABEL = "Baa − 20y Treasury spread (left axis, %)"
LIQ_LABEL = "Liquidity proxy: fitted off-the-run − on-the-run CMT, 10y (right axis, bp)"
SOURCE = ("Sources: FRED (DBAA, DGS20, DGS10); Federal Reserve Gürkaynak-Sack-Wright "
          "yield curve (SVENPY10). Monthly averages of same-date daily data.")

m = pd.read_csv(CLEAN / "panel_monthly_complete.csv")
m["date"] = pd.PeriodIndex(m["month"], freq="M").to_timestamp()
m = m.set_index("date").sort_index()
# Reindex to every calendar month so any month without data shows as a gap
# in the line instead of being silently bridged.
m = m.reindex(pd.date_range(m.index.min(), m.index.max(), freq="MS"))


def draw(ax1, df, title, date_fmt, locator):
    """Dual-axis panel on ax1; returns (corr, n, first, last, line handles)."""
    pair = df[[SPREAD, LIQ]].dropna()
    corr = pair[SPREAD].corr(pair[LIQ])
    first, last = pair.index.min(), pair.index.max()

    ax2 = ax1.twinx()
    l1, = ax1.plot(df.index, df[SPREAD], color=SPREAD_COLOR, lw=2, label=SPREAD_LABEL)
    l2, = ax2.plot(df.index, df[LIQ], color=LIQ_COLOR, lw=2, ls="--", label=LIQ_LABEL)

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
                  f"{first:%b %Y}–{last:%b %Y})", fontsize=12, fontweight="bold")
    return corr, len(pair), first, last, [l1, l2]


def finish(fig, handles, path, legend_y, rect_bottom):
    # Legend below the plot area so it never covers either line.
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, legend_y))
    fig.text(0.01, 0.01, SOURCE, fontsize=7.5, color="#555555")
    fig.tight_layout(rect=(0, rect_bottom, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


PANELS = [
    (m.loc[START_ORIGINAL:END_ORIGINAL], "Slide period", "%m-%y",
     lambda: mdates.MonthLocator(bymonth=[1, 4, 7, 10]), OUTPUT / "fig_original_2006_2009.png"),
    (m, "Longest available sample", "%Y",
     lambda: mdates.YearLocator(base=3), OUTPUT / "fig_extended.png"),
]

# One figure per sample (Requirements 5 and 6).
for df, label, fmt, locator, path in PANELS:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    corr, n, first, last, handles = draw(
        ax, df, f"Baa−Treasury Yield Spread and Treasury Liquidity: {label}", fmt, locator())
    finish(fig, handles, path, legend_y=0.035, rect_bottom=0.08)
    print(f"{path.relative_to(ROOT)}: corr = {corr:.4f}, n = {n}, {first:%Y-%m} to {last:%Y-%m}")

# Both samples stacked in one figure, for the report.
fig, axes = plt.subplots(2, 1, figsize=(10, 9))
for ax, (df, label, fmt, locator, _) in zip(axes, PANELS):
    *_, handles = draw(ax, df, label, fmt, locator())
finish(fig, handles, OUTPUT / "fig_replication.png", legend_y=0.02, rect_bottom=0.05)
print("output/fig_replication.png: both panels above")
