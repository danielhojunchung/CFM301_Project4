"""Project 4: construct daily and monthly credit spread / Treasury liquidity panels.

Run from repository root: python code/01_clean.py
Requires pandas and numpy; input files in data/:
    DBAA.csv, DGS20.csv, DGS10.csv, VIXCLS.csv, yieldcurve.csv

Writes:
    data/clean/panel_daily.csv
    data/clean/panel_monthly.csv
    data/clean/panel_monthly_complete.csv
    data/clean/panel_original_2006_2009.csv
    output/cleaning_log.csv
    output/extreme_values.csv
    output/data_dictionary.csv

Yields/spreads are in PERCENTAGE POINTS (not decimals), except *_bp in basis points.
VIX is in index points. The credit loss assumption is 0.124 percentage points/yr.

IMPORTANT: SVENPY20 is a FITTED OFF-THE-RUN 20-year par yield; DGS20 is a
20-year CONSTANT-MATURITY Treasury benchmark, NOT the individual on-the-run
20-year security. Their difference is only a proxy for the on/off-the-run
liquidity premium. Do not label it an exact security-paired on/off spread.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CLEAN = DATA / "clean"
OUTPUT = ROOT / "output"
CLEAN.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)

START_ORIGINAL, END_ORIGINAL = "2006-01", "2009-12"
EXPECTED_BAA_LOSS_PCT = 0.124  # lecture historical annual credit loss, percent
EXTREME_COUNT = 5
LOG = []


def log(step, series, affected, detail=""):
    record = dict(step=step, series=series, rows_affected=int(affected), detail=str(detail))
    LOG.append(record)
    print(f"{step:<17} {series:<24} {int(affected):>7} {detail}")


def read_series(filename, column, date_col, skiprows=0):
    path = DATA / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; put all five CSV files in data/")
    raw = pd.read_csv(path, skiprows=skiprows, low_memory=False)
    if date_col not in raw or column not in raw:
        raise ValueError(f"{filename} lacks {date_col} or {column}; columns: {list(raw.columns)[:15]}")
    log("load", column, len(raw), filename)
    dates = pd.to_datetime(raw[date_col], errors="coerce")
    nums = pd.to_numeric(raw[column].replace({".": np.nan, "NA": np.nan, "": np.nan}), errors="coerce")
    bad_date = int(dates.isna().sum())
    log("invalid_dates", column, bad_date, "removed; cannot align")
    tmp = pd.DataFrame({"date": dates, column: nums}).dropna(subset=["date"])
    duplicates = int(tmp.duplicated("date").sum())
    # Repeated identical dates are deduplicated deterministically, keeping last row.
    log("duplicate_dates", column, duplicates, "keep last for duplicate date")
    tmp = tmp.drop_duplicates("date", keep="last").sort_values("date")
    log("missing_values", column, int(tmp[column].isna().sum()), "left NaN; never interpolated")
    if tmp[column].notna().any():
        log("valid_range", column, int(tmp[column].notna().sum()),
            f"{tmp.loc[tmp[column].notna(),'date'].min():%Y-%m-%d} to "
            f"{tmp.loc[tmp[column].notna(),'date'].max():%Y-%m-%d}")
    return tmp.set_index("date")[column]


# Fed's spreadsheet includes 9 metadata/preamble rows before header 'Date'.
baa = read_series("DBAA.csv", "DBAA", "observation_date")
treasury = read_series("DGS20.csv", "DGS20", "observation_date")
vix = read_series("VIXCLS.csv", "VIXCLS", "observation_date")
offrun = read_series("yieldcurve.csv", "SVENPY20", "Date", skiprows=9)
# Robustness proxy at 10y: the 10-year note was issued continuously, so DGS10 is
# always based on a genuine on-the-run note (no 2020 reissue break as at 20y).
treasury10 = read_series("DGS10.csv", "DGS10", "observation_date")
offrun10 = read_series("yieldcurve.csv", "SVENPY10", "Date", skiprows=9)

# Daily OUTER merge preserves dates and makes missingness explicit. Do not fill
# holidays and do not align a yield to the previous/next trading date.
d = pd.concat([baa, treasury, vix, offrun, treasury10, offrun10], axis=1, join="outer").sort_index()
d.index.name = "date"
log("align_daily", "calendar_union", len(d), f"{d.index.min():%Y-%m-%d} to {d.index.max():%Y-%m-%d}")
for col in ["DBAA", "DGS20", "VIXCLS", "SVENPY20", "DGS10", "SVENPY10"]:
    log("align_missing", col, int(d[col].isna().sum()), "missing within merged trading-date union")

# Spread is BBB/Baa index minus 20-year CMT (percent points).
d["credit_spread_pct"] = d["DBAA"] - d["DGS20"]
d["credit_spread_bp"] = 100 * d["credit_spread_pct"]
# Proxy (off-the-run par yield - Treasury constant-maturity benchmark).
d["liquidity_proxy_pct"] = d["SVENPY20"] - d["DGS20"]
d["liquidity_proxy_bp"] = 100 * d["liquidity_proxy_pct"]
d["vix"] = d["VIXCLS"]
# Robustness: 10y fitted off-the-run par yield minus 10y CMT (on-the-run based), bp.
d["liquidity_proxy10_bp"] = 100 * (d["SVENPY10"] - d["DGS10"])
d["expected_default_loss_pct"] = EXPECTED_BAA_LOSS_PCT
d["residual_after_default_pct"] = d["credit_spread_pct"] - EXPECTED_BAA_LOSS_PCT

# A daily observation for a specific regression/plot requires simultaneous data.
d["pair_credit_liquidity"] = d[["credit_spread_pct", "liquidity_proxy_bp"]].notna().all(axis=1)
d["pair_credit_vix"] = d[["credit_spread_pct", "vix"]].notna().all(axis=1)
d["complete_all"] = d[["credit_spread_pct", "liquidity_proxy_bp", "vix"]].notna().all(axis=1)
for flag in ["pair_credit_liquidity", "pair_credit_vix", "complete_all"]:
    log("daily_complete", flag, int(d[flag].sum()), "available daily rows; missing rows retained in daily CSV")

# MONTHLY AVERAGES OF SAME-DATE DAILY OBSERVATIONS. To avoid mixing dates,
# compute each month's means from dates where ALL FOUR raw inputs exist.
# Also include raw per-series means for diagnostics and counts for transparency.
d["month"] = d.index.to_period("M")
g = d.groupby("month", sort=True)
m = pd.DataFrame(index=g.size().index)
m["n_calendar_rows"] = g.size()
for source in ["DBAA", "DGS20", "VIXCLS", "SVENPY20"]:
    m[f"n_{source.lower()}"] = g[source].count()
    m[f"raw_mean_{source.lower()}"] = g[source].mean()

same = d.loc[d["complete_all"]].copy()
mg = same.groupby("month")
m["n_complete_days"] = mg.size()
m["n_complete_days"] = m["n_complete_days"].fillna(0).astype(int)
for col in ["DBAA", "DGS20", "SVENPY20", "VIXCLS", "credit_spread_pct", "liquidity_proxy_pct",
            "credit_spread_bp", "liquidity_proxy_bp", "vix", "residual_after_default_pct",
            "DGS10", "SVENPY10", "liquidity_proxy10_bp"]:
    m[col] = mg[col].mean()
m["expected_default_loss_pct"] = EXPECTED_BAA_LOSS_PCT

# Monthly first differences in LEVELS, not percentage growth rates.
# Do not bridge over a missing monthly observation.
for col in ["credit_spread_pct", "liquidity_proxy_bp", "vix", "liquidity_proxy10_bp"]:
    m[f"d_{col}"] = m[col].diff()

for series in ["credit_spread_pct", "liquidity_proxy_bp", "vix"]:
    log("monthly_available", series, int(m[series].notna().sum()), "based on same-date complete daily rows")
log("monthly_empty", "all_variables", int((m["n_complete_days"] == 0).sum()), "no common valid trading days")

# No winsorization: removing crisis spikes would erase the event under study.
# Inspect extremes, but do not automatically drop legitimate peaks or troughs.
extremes = []
for series in ["credit_spread_pct", "liquidity_proxy_bp", "vix"]:
    for label, values in [("lowest", m[series].nsmallest(EXTREME_COUNT)),
                          ("highest", m[series].nlargest(EXTREME_COUNT))]:
        for month, value in values.items():
            extremes.append(dict(series=series, tail=label, month=str(month), value=value))
    log("winsorized", series, 0, "none: crisis spikes are the signal; raw extremes saved")

# Simple controls: a negative liquidity proxy is possible (and is not missing).
# Flag extreme observations for inspection; do not clip based on an arbitrary bound.
for series in ["DBAA", "DGS20", "SVENPY20", "VIXCLS"]:
    n = int((d[series].notna() & (d[series] <= 0)).sum())
    log("nonpositive", series, n, "flagged for manual review; not automatically removed")

m.index = m.index.astype(str)
m.index.name = "month"
monthly_full = m.reset_index()
monthly_complete = monthly_full.loc[monthly_full["n_complete_days"] > 0].copy()
original = monthly_complete.loc[monthly_complete["month"].between(START_ORIGINAL, END_ORIGINAL)].copy()

# Output. Keep a complete-case monthly sample for correlations and regressions,
# plus full month panel for missingness audit.
d.drop(columns=["month"]).reset_index().to_csv(CLEAN / "panel_daily.csv", index=False, float_format="%.8f")
monthly_full.to_csv(CLEAN / "panel_monthly.csv", index=False, float_format="%.8f")
monthly_complete.to_csv(CLEAN / "panel_monthly_complete.csv", index=False, float_format="%.8f")
original.to_csv(CLEAN / "panel_original_2006_2009.csv", index=False, float_format="%.8f")
pd.DataFrame(LOG).to_csv(OUTPUT / "cleaning_log.csv", index=False)
pd.DataFrame(extremes).to_csv(OUTPUT / "extreme_values.csv", index=False)

DIC = {
    "month": "Calendar month YYYY-MM",
    "date": "Daily observation date",
    "DBAA": "Moody's seasoned Baa corporate yield, percent per annum",
    "DGS20": "20-year Treasury constant maturity rate, percent per annum",
    "SVENPY20": "Fed fitted off-the-run 20-year PAR yield, percent per annum",
    "VIXCLS": "CBOE VIX index points",
    "credit_spread_pct": "DBAA minus DGS20, percentage points",
    "credit_spread_bp": "100 times credit_spread_pct, basis points",
    "liquidity_proxy_pct": "SVENPY20 minus DGS20, percentage points (approximate proxy)",
    "liquidity_proxy_bp": "100 times liquidity_proxy_pct, basis points (approximate proxy)",
    "vix": "VIX index points, unscaled",
    "DGS10": "10-year Treasury constant maturity rate (on-the-run based), percent per annum",
    "SVENPY10": "Fed fitted off-the-run 10-year PAR yield, percent per annum",
    "liquidity_proxy10_bp": "100 x (SVENPY10 - DGS10), basis points; robustness liquidity proxy. "
                            "Monthly mean over the same complete_all days (10y inputs rarely missing)",
    "expected_default_loss_pct": "0.124 annual percentage points based on lecture Baa loss-rate benchmark",
    "residual_after_default_pct": "Credit spread less assumed annual expected default loss, percentage points",
    "d_credit_spread_pct": "Monthly first difference in credit spread, percentage points",
    "d_liquidity_proxy_bp": "Monthly first difference in liquidity proxy, basis points",
    "d_vix": "Monthly first difference in VIX index points",
    "n_complete_days": "Number of within-month days on which all four inputs are nonmissing",
}
pd.DataFrame([{"variable": k, "meaning": v} for k, v in DIC.items()]).to_csv(OUTPUT / "data_dictionary.csv", index=False)
log("save", "original_months", len(original), f"{START_ORIGINAL} through {END_ORIGINAL}")
print("\nSaved all 4 panels, cleaning log, extreme values, and data dictionary.")
print("NOTE: liquidity_proxy_bp is NOT a directly observed security-paired on/off-the-run spread.")
