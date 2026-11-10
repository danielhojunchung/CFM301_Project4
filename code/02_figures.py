"""Project 4: dual-axis figures of the Baa-Treasury spread vs. the Treasury liquidity proxy.

Run from repository root after 01_clean.py: python code/02_figures.py
Requires pandas, numpy, matplotlib. Reads data/clean/panel_monthly_complete.csv.

Writes:
    output/fig_original_2006_2009.png   (Requirement 5: slide 59 period)
    output/fig_extended.png             (Requirement 6: longest available sample)
  10y proxy (SVENPY10 - DGS10), the main proxy in the report:
    output/fig_original_2006_2009_10y.png   (slide's exact months, Jan 2006 - Oct 2009)
    output/fig_extended_10y.png             (longest available sample)
    output/fig_replication.png              (both 10y panels stacked; Figure 1 in the report)

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


# ---------------------------------------------------------------- 10y proxy figures
# Same layout as above, for the 10y proxy SVENPY10 - DGS10 (main proxy in the report).
# DGS10 is always based on the newly issued (on-the-run) 10-year note, so this proxy
# has no 2020 reissue break. The slide's chart data run Jan 2006 - Oct 2009.
END_SLIDE = "2009-10"
LIQ10 = "liquidity_proxy10_bp"
LIQ10_LABEL = "Liquidity proxy: fitted off-the-run − on-the-run CMT, 10y (right axis, bp)"
SOURCE10 = ("Sources: FRED (DBAA, DGS20, DGS10); Federal Reserve Gürkaynak-Sack-Wright "
            "yield curve (SVENPY10). Monthly averages of same-date daily data.")


def draw10(ax1, df, title, date_fmt, locator):
    """Dual-axis panel of the spread vs the 10y proxy; returns (corr, n, first, last, handles)."""
    pair = df[[SPREAD, LIQ10]].dropna()
    corr = pair[SPREAD].corr(pair[LIQ10])
    first, last = pair.index.min(), pair.index.max()

    ax2 = ax1.twinx()
    l1, = ax1.plot(df.index, df[SPREAD], color=SPREAD_COLOR, lw=2,
                   label="Baa − 20y Treasury spread (left axis, %)")
    l2, = ax2.plot(df.index, df[LIQ10], color=LIQ_COLOR, lw=2, ls="--", label=LIQ10_LABEL)

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


def finish10(fig, handles, path, legend_y, rect_bottom):
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=9, bbox_to_anchor=(0.5, legend_y))
    fig.text(0.01, 0.01, SOURCE10, fontsize=7.5, color="#555555")
    fig.tight_layout(rect=(0, rect_bottom, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


PANELS10 = [
    (m.loc[START_ORIGINAL:END_SLIDE], "Slide period", "%m-%y",
     lambda: mdates.MonthLocator(bymonth=[1, 4, 7, 10]), OUTPUT / "fig_original_2006_2009_10y.png"),
    (m, "Longest available sample", "%Y",
     lambda: mdates.YearLocator(base=3), OUTPUT / "fig_extended_10y.png"),
]

for df, label, fmt, locator, path in PANELS10:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    corr, n, first, last, handles = draw10(
        ax, df, f"Baa−Treasury Yield Spread and Treasury Liquidity (10y proxy): {label}",
        fmt, locator())
    finish10(fig, handles, path, legend_y=0.035, rect_bottom=0.08)
    print(f"{path.relative_to(ROOT)}: corr = {corr:.4f}, n = {n}, {first:%Y-%m} to {last:%Y-%m}")

# Both 10y samples stacked in one figure (Figure 1 in the report).
fig, axes = plt.subplots(2, 1, figsize=(10, 9))
for ax, (df, label, fmt, locator, _) in zip(axes, PANELS10):
    *_, handles = draw10(ax, df, label, fmt, locator())
finish10(fig, handles, OUTPUT / "fig_replication.png", legend_y=0.02, rect_bottom=0.05)
print("output/fig_replication.png: both 10y panels above")
