"""Project 4: was the March 2020 'dash for cash' a liquidity crisis like 2008?

Run from repository root after 01_clean.py: python code/03_crisis_analysis.py
Requires pandas, numpy, matplotlib, statsmodels.
Reads data/clean/panel_monthly_complete.csv, data/clean/panel_daily.csv and
'Ch 9 Bonds.pptx' (to extract the data behind the slide-43 chart for comparison).

Every table is computed for TWO liquidity proxies (column 'proxy'):
    20y: SVENPY20 - DGS20  (team's original construction)
    10y: SVENPY10 - DGS10  (robustness; DGS10 is always a genuine on-the-run note)

Writes (all in output/):
    tab_slide_comparison.csv    our series vs the slide's own chart data (Requirement 7)
    tab_crisis_comparison.csv   peaks, rises, correlations for GFC vs COVID
    tab_regressions.csv         spread on liquidity / VIX / both, Newey-West t (Requirement 8)
    tab_vix_correlation.csv     spread-VIX correlation vs slide 36's 0.64 (Requirement 8)
    tab_puzzle.csv              expected default loss vs average spread (Requirement 9)
    tab_sensitivity.csv         correlation under alternative assumptions (Requirement 10)
    tab_event_mar23.csv         daily path around the Fed's 23-Mar-2020 corporate bond facility
    fig_crisis_comparison.png   2008 vs 2020, aligned on each crisis's spread peak

DATA BREAK (20y proxy only): on 2020-05-20 the US Treasury reissued the 20-year bond,
and DGS20 from then on is that new (thinly traded, cheap) bond, so SVENPY20 - DGS20
drops mechanically. COVID statistics therefore use a window ending 2020-05-19 (daily) /
2020-05 (monthly) for both proxies, so they are comparable; the full-2020 window is
kept as a sensitivity check.
"""
from pathlib import Path
import re
import zipfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

S, V = "credit_spread_pct", "vix"
PROXIES = {"20y": "liquidity_proxy_bp", "10y": "liquidity_proxy10_bp"}
REISSUE = pd.Timestamp("2020-05-20")    # 20-year bond reissued; DGS20 changes nature
FED_SMCCF = pd.Timestamp("2020-03-23")  # Fed announces PMCCF/SMCCF corporate bond buying
HAC_LAGS = 6                            # Newey-West lags for monthly data

GFC, COVID = "GFC 2006-01..2009-12", "COVID 2019-07..2020-05"
WINDOWS = {GFC: ("2006-01", "2009-12", "2009-12-31"),
           COVID: ("2019-07", "2020-05", "2020-05-19")}   # (month from, month to, last daily date)
BASELINE = {GFC: ("2006-01", "2007-06"), COVID: ("2019-07", "2020-01")}

m = pd.read_csv(CLEAN / "panel_monthly_complete.csv")
m["date"] = pd.PeriodIndex(m["month"], freq="M").to_timestamp()
m = m.set_index("date").sort_index()
dall = pd.read_csv(CLEAN / "panel_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
d = dall.loc[dall["complete_all"]]


def chg(df, cols, freq=None):
    """First differences. Monthly: reindex to every month first so a change never
    bridges a missing month (e.g. the 1987-1993 DGS20 gap)."""
    x = df[cols]
    if freq:
        x = x.reindex(pd.date_range(x.index.min(), x.index.max(), freq=freq))
    return x.diff()


def corr(df, a, b):
    x = df[[a, b]].dropna()
    return x[a].corr(x[b]), len(x)


def ols(df, xs):
    x = df[[S] + xs].dropna()
    return sm.OLS(x[S], sm.add_constant(x[xs])).fit(
        cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS}), len(x)


# ---------------------------------------------------------------- 0. slide comparison
# The slide-43 chart embeds its data (Baa-Tsy %, on/off-the-run bp, Jan 2006 - Oct 2009).
with zipfile.ZipFile(ROOT / "Ch 9 Bonds.pptx") as z:
    xml = z.read("ppt/charts/chart4.xml").decode()
slide = {}
for ser in re.findall(r"<c:ser>(.*?)</c:ser>", xml, re.S):
    vals = re.findall(r"<c:v>([^<]*)</c:v>", ser)
    n = (len(vals) - 1) // 2                      # name, n dates (Excel serials), n values
    dates = pd.to_datetime([int(float(v)) for v in vals[1:1 + n]], unit="D", origin="1899-12-30")
    slide[vals[0]] = pd.Series([float(v) for v in vals[1 + n:]], index=dates.to_period("M").to_timestamp())
slide = pd.DataFrame(slide)
slide.columns = ["slide_spread_pct", "slide_liq_bp"]
j = slide.join(m)
comp = [{"comparison": "Slide: spread vs its liquidity measure",
         "corr": j["slide_spread_pct"].corr(j["slide_liq_bp"]), "n": len(j)},
        {"comparison": "Our Baa-20y spread vs slide's spread",
         "corr": j[S].corr(j["slide_spread_pct"]), "n": len(j)},
        {"comparison": "Mean level gap: our spread minus slide's spread (pct pts)",
         "corr": (j[S] - j["slide_spread_pct"]).mean(), "n": len(j)}]
for p, L in PROXIES.items():
    comp += [{"comparison": f"Our spread vs our {p} proxy (slide months)", "corr": j[S].corr(j[L]), "n": len(j)},
             {"comparison": f"Our {p} proxy vs slide's liquidity measure", "corr": j[L].corr(j["slide_liq_bp"]), "n": len(j)},
             {"comparison": f"Our {p} proxy: min / max (bp); slide: "
                            f"{j['slide_liq_bp'].min():.1f} / {j['slide_liq_bp'].max():.1f}",
              "corr": np.nan, "n": f"{j[L].min():.1f} / {j[L].max():.1f}"}]
comp = pd.DataFrame(comp).rename(columns={"corr": "value"})
comp.to_csv(OUTPUT / "tab_slide_comparison.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- 1. crisis comparison
rows = []
for p, L in PROXIES.items():
    for name, (a, b, dend) in WINDOWS.items():
        w = m.loc[a:b]
        base = m.loc[BASELINE[name][0]:BASELINE[name][1]]
        dw = d.loc[a:dend]
        peak_s, peak_l = dw[S].idxmax(), dw[L].idxmax()
        rows.append({
            "proxy": p, "window": name,
            "corr_levels_monthly": corr(w, S, L)[0], "n_months": corr(w, S, L)[1],
            "corr_changes_monthly": corr(chg(w, [S, L], "MS"), S, L)[0],
            "corr_levels_daily": corr(dw, S, L)[0], "n_days": corr(dw, S, L)[1],
            "corr_spread_vix_monthly": corr(w, S, V)[0],
            "baseline_spread_pct": base[S].mean(), "peak_spread_pct_daily": dw[S].max(),
            "rise_spread_pct": dw[S].max() - base[S].mean(),
            "baseline_liq_bp": base[L].mean(), "peak_liq_bp_daily": dw[L].max(),
            "rise_liq_bp": dw[L].max() - base[L].mean(),
            "peak_vix_daily": dw[V].max(),
            "date_peak_spread": f"{peak_s:%Y-%m-%d}", "date_peak_liq": f"{peak_l:%Y-%m-%d}",
            "liq_peak_days_after_spread_peak": (peak_l - peak_s).days,
        })
crisis = pd.DataFrame(rows)
crisis.to_csv(OUTPUT / "tab_crisis_comparison.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- 2. regressions
samples = {"Full 1993-10..2026-10": m, GFC: m.loc["2006-01":"2009-12"], COVID: m.loc["2019-07":"2020-05"]}
reg_rows = []
for p, L in PROXIES.items():
    for sname, df in samples.items():
        for spec in ([L], [V], [L, V]):
            if spec == [V] and p != "20y":
                continue  # VIX-only regression does not depend on the proxy
            res, n = ols(df, spec)
            reg_rows.append({"proxy": p if L in spec else "-", "sample": sname,
                             "spec": " + ".join("liquidity" if s == L else s for s in spec),
                             "n": n, "r2": res.rsquared,
                             "b_liquidity": res.params.get(L, np.nan), "t_liquidity": res.tvalues.get(L, np.nan),
                             "b_vix": res.params.get(V, np.nan), "t_vix": res.tvalues.get(V, np.nan)})
regs = pd.DataFrame(reg_rows)
regs.to_csv(OUTPUT / "tab_regressions.csv", index=False, float_format="%.4f")

# Spread-VIX correlation vs slide 36 (Corr 0.64, 1986-2013). DGS20 is missing 1987-1993,
# so our closest comparable window is 1993-10..2013-12.
vixc = pd.DataFrame([{"sample": s, "corr_spread_vix": corr(df, S, V)[0], "n": corr(df, S, V)[1]}
                     for s, df in {"Full 1993-10..2026-10": m,
                                   "Slide-36-like 1993-10..2013-12": m.loc[:"2013-12"],
                                   "Post-2014 2014-01..2026-10": m.loc["2014-01":]}.items()])
vixc.to_csv(OUTPUT / "tab_vix_correlation.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- 3. credit spread puzzle
# Expected loss = default prob x (1 - recovery). Two lecture benchmarks.
LOSS = {"Moody's Baa loss rate 1982-2008 (slide 39)": 0.124,
        "Giesecke et al.: 1.5% default x 50% LGD (slide 41)": 1.5 * 0.5}
puz = []
for p, L in PROXIES.items():
    beta = ols(m, [L, V])[0].params[L]   # full-sample beta, controlling for VIX (pct pts per bp)
    for sname, df in samples.items():
        avg_s = df[S].mean()
        # Liquidity-attributable part = beta x average proxy level in that sample.
        liq_part = beta * df[L].mean()
        for lname, loss in LOSS.items():
            resid = avg_s - loss
            puz.append({"proxy": p, "sample": sname, "loss_assumption": lname,
                        "avg_spread_pct": avg_s, "expected_loss_pct": loss,
                        "loss_share_of_spread": loss / avg_s, "residual_pct": resid,
                        "liquidity_part_pct": liq_part, "liquidity_share_of_residual": liq_part / resid})
puz = pd.DataFrame(puz)
puz.to_csv(OUTPUT / "tab_puzzle.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- 4. sensitivity table
calm = m.drop(m.loc["2007-07":"2009-12"].index).drop(m.loc["2020-02":"2020-12"].index)
eom = d.groupby(d.index.to_period("M")).last()
cases = [
    ("Baseline: monthly levels, full sample 1993-10..2026-10", m, False),
    ("Monthly levels, slide window 2006-01..2009-12", m.loc["2006-01":"2009-12"], False),
    ("Monthly levels, slide's exact months 2006-01..2009-10", m.loc["2006-01":"2009-10"], False),
    ("Monthly levels, COVID 2019-07..2020-05", m.loc["2019-07":"2020-05"], False),
    ("Monthly levels, COVID 2019-07..2020-12 (crosses 20y reissue)", m.loc["2019-07":"2020-12"], False),
    ("Monthly levels, before 20y reissue 1993-10..2020-04", m.loc[:"2020-04"], False),
    ("Monthly levels, after 20y reissue 2020-06..2026-10", m.loc["2020-06":], False),
    ("Monthly levels, calm years (ex 2007-07..2009-12, 2020-02..12)", calm, False),
    ("Monthly changes, full sample", m, "MS"),
    ("Monthly changes, GFC 2006-01..2009-12", m.loc["2006-01":"2009-12"], "MS"),
    ("Monthly changes, COVID 2019-07..2020-05", m.loc["2019-07":"2020-05"], "MS"),
    ("Daily levels, full sample", d, False),
    ("Daily levels, GFC 2006..2009", d.loc["2006":"2009"], False),
    ("Daily levels, COVID 2019-07-01..2020-05-19", d.loc["2019-07-01":"2020-05-19"], False),
    ("Daily changes, COVID 2019-07-01..2020-05-19", d.loc["2019-07-01":"2020-05-19"], "D"),
    ("End-of-month levels instead of averages, full sample", eom, False),
]
sens = []
for label, df, diff in cases:
    row = {"assumption": label}
    for p, L in PROXIES.items():
        x = chg(df, [S, L], "MS" if diff == "MS" else None) if diff else df
        row[f"corr_{p}"], row["n"] = corr(x, S, L)
    sens.append(row)
sens = pd.DataFrame(sens)[["assumption", "corr_20y", "corr_10y", "n"]]
sens.to_csv(OUTPUT / "tab_sensitivity.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- 5. Fed event, 23 Mar 2020
ev = d.loc["2020-03-09":"2020-04-09", [S] + list(PROXIES.values()) + [V]].copy()
ev["trading_days_from_mar23"] = np.arange(len(ev)) - ev.index.get_loc(FED_SMCCF)
ev.to_csv(OUTPUT / "tab_event_mar23.csv", float_format="%.4f")

# ---------------------------------------------------------------- 6. figure
# Small multiples, no dual axis: rows = series, colour = crisis. Each crisis is aligned
# on its own daily spread-peak date (day 0); x in months from that peak.
INK, MUTED, GRID = "#1F2328", "#6E7781", "#E5E7EB"
GFC_C, COVID_C = "#2E5EAA", "#C2571A"
gfc_peak = pd.Timestamp(crisis.query("proxy == '20y' and window == @GFC")["date_peak_spread"].iloc[0])
cov_peak = pd.Timestamp(crisis.query("proxy == '20y' and window == @COVID")["date_peak_spread"].iloc[0])
panels = [(S, "Baa − 20y Treasury spread (%)", True),
          (PROXIES["10y"], "Liquidity proxy, 10y: fitted off-the-run − on-the-run CMT (bp)", False),
          (PROXIES["20y"], "Liquidity proxy, 20y: fitted off-the-run − 20y CMT (bp)", True),
          (V, "VIX (index points)", False)]

fig, axes = plt.subplots(len(panels), 1, figsize=(9, 11), sharex=True)
for ax, (col, ylab, has_break) in zip(axes, panels):
    for peak, color, cut in [(gfc_peak, GFC_C, None), (cov_peak, COVID_C, REISSUE if has_break else None)]:
        w = dall.loc[peak - pd.DateOffset(months=12):peak + pd.DateOffset(months=12), col].dropna()
        x = (w.index - peak).days / 30.44
        y = w.rolling(5, min_periods=1).mean()
        if cut is not None:   # 20y-based series change nature at the reissue
            keep = w.index < cut
            ax.plot(x[keep], y[keep], color=color, lw=2)
            ax.plot(x[~keep], y[~keep], color=color, lw=1.2, ls=":", alpha=0.8)
        else:
            ax.plot(x, y, color=color, lw=2)
    ax.axvline(0, color=MUTED, lw=1, ls="--")
    ax.set_title(ylab, loc="left", fontsize=10, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)
axes[-1].set_xlabel(f"Months from each crisis's peak Baa spread (GFC: {gfc_peak:%Y-%m-%d}; "
                    f"COVID: {cov_peak:%Y-%m-%d}, the day the Fed announced corporate bond purchases)",
                    fontsize=8.5, color=MUTED)
handles = [plt.Line2D([], [], color=GFC_C, lw=2, label="2008 crisis (GFC)"),
           plt.Line2D([], [], color=COVID_C, lw=2, label="2020 dash for cash"),
           plt.Line2D([], [], color=COVID_C, lw=1.2, ls=":", label="2020 after 20y reissue (20y data change)")]
fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, fontsize=9,
           bbox_to_anchor=(0.5, 0.965))
fig.suptitle("Was March 2020 a liquidity crisis like 2008?", fontsize=13,
             fontweight="bold", color=INK, y=0.99)
fig.text(0.01, 0.005, "Daily data, 5-day moving average. Sources: FRED (DBAA, DGS20, DGS10, VIXCLS); "
         "Fed Gürkaynak-Sack-Wright curve (SVENPY10, SVENPY20).", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.02, 1, 0.95))
fig.savefig(OUTPUT / "fig_crisis_comparison.png", dpi=200)
plt.close(fig)

pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_colwidth", 70)
for title, t in [("SLIDE COMPARISON", comp), ("CRISIS COMPARISON", crisis.set_index(["proxy", "window"]).T),
                 ("REGRESSIONS", regs), ("VIX CORRELATION", vixc), ("PUZZLE", puz),
                 ("SENSITIVITY", sens), ("EVENT 23-MAR-2020", ev)]:
    print(f"\n=== {title}\n{t.round(3).to_string()}")
