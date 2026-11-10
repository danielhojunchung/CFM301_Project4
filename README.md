# CFM 301 Project 4: Credit Spreads and Treasury Liquidity

Reproduces the Ch. 9 (Bonds) figure "Baa-Tsy Yield Spreads and Liquidity, Corr = 0.96", extends it to 2026, and asks: **was the March 2020 "dash for cash" a Treasury liquidity crisis like 2008?**

## Requirements

- **Language:** Python 3.13.9
- **Packages:** pandas 2.3.3, numpy 2.3.5, matplotlib 3.10.6, statsmodels 0.14.5

```bash
pip install pandas==2.3.3 numpy==2.3.5 matplotlib==3.10.6 statsmodels==0.14.5
```

No internet connection, WRDS login or manual steps are needed. All paths are relative to the repository root.

## How to run

Run from the repository root, in this order:

```bash
python code/01_clean.py            # build cleaned daily and monthly panels
python code/02_figures.py          # dual-axis replication figures
python code/03_crisis_analysis.py  # slide comparison, regressions, puzzle, sensitivity, 2008 vs 2020
```

Each script prints its key numbers to the console. A full run takes under a minute.

## Files

### Input data (`data/`)

| File | Series | Source | Units, frequency |
|---|---|---|---|
| `DBAA.csv` | Moody's seasoned Baa corporate bond yield | FRED (DBAA) | % p.a., daily |
| `DGS20.csv` | 20-year Treasury constant-maturity yield | FRED (DGS20) | % p.a., daily |
| `DGS10.csv` | 10-year Treasury constant-maturity yield | FRED (DGS10) | % p.a., daily |
| `VIXCLS.csv` | CBOE VIX | FRED (VIXCLS) | index points, daily |
| `yieldcurve.csv` | Fitted off-the-run par yields; we use `SVENPY10` and `SVENPY20` | Federal Reserve, Gürkaynak-Sack-Wright (2007) yield curve | % p.a., daily |

The FRED files were downloaded on 2026-11-08/09 and run through 2026-11-05.

### Code (`code/`)

| Script | Does | Writes |
|---|---|---|
| `01_clean.py` | Loads, cleans and aligns all series. Builds the spread and liquidity proxies. Averages daily data to monthly. | `data/clean/*.csv`; `output/cleaning_log.csv`, `extreme_values.csv`, `data_dictionary.csv` |
| `02_figures.py` | Dual-axis figures: spread vs liquidity proxy, for 2006–2009 and the full sample. 20y proxy: 2006-01 to 2009-12. 10y proxy (main proxy in the report): the slide's exact months, 2006-01 to 2009-10 | 20y: `output/fig_original_2006_2009.png`, `output/fig_extended.png`; 10y: `output/fig_original_2006_2009_10y.png`, `output/fig_extended_10y.png`, `output/fig_replication.png` (both 10y panels; Figure 1 in the report) |
| `03_crisis_analysis.py` | Everything below, for both liquidity proxies | `output/tab_*.csv`, `output/fig_crisis_comparison.png` |

What `03_crisis_analysis.py` covers:

- comparison with the slide's own chart data, read from `Ch 9 Bonds.pptx`
- regressions of the spread on liquidity, on VIX, and on both
- correlation of the spread with VIX, compared with the slide's 0.64
- credit spread puzzle decomposition
- sensitivity table
- 2008 vs 2020 crisis comparison
- the Fed's 23 March 2020 announcement

### Outputs (`output/`), by brief requirement

| Requirement | File |
|---|---|
| 4. Cleaning (counts per step) | `cleaning_log.csv`, `extreme_values.csv` |
| 5–6. Figure and correlation, original and extended sample | `fig_replication.png` (report Figure 1), `fig_original_2006_2009_10y.png`, `fig_extended_10y.png`; 20y versions: `fig_original_2006_2009.png`, `fig_extended.png` |
| 7. Comparison to the slide | `tab_slide_comparison.csv` |
| 8. Liquidity vs default risk | `tab_regressions.csv`, `tab_vix_correlation.csv` |
| 9. Credit spread puzzle | `tab_puzzle.csv` |
| 10. Sensitivity | `tab_sensitivity.csv` |
| Economic question: 2008 vs 2020 | `fig_crisis_comparison.png`, `tab_crisis_comparison.csv`, `tab_event_mar23.csv` |

Column definitions are in `output/data_dictionary.csv`.

## Construction notes

- **Credit spread** = DBAA − DGS20, in percentage points. The 20-year Treasury is the closest match to the long maturity of Moody's Baa index.
- **Liquidity proxies** (fitted off-the-run yield minus the benchmark yield, in basis points):
  - **10y (main proxy in the report):** `SVENPY10 − DGS10`. DGS10 is always based on the newly issued (on-the-run) 10-year note, so this proxy is consistent over the whole sample.
  - **20y (robustness check):** `SVENPY20 − DGS20`. The Treasury did not issue 20-year bonds from 1986 until it reissued them on 2020-05-20. Before that date DGS20 is itself interpolated; after it, DGS20 tracks the new, thinly traded 20-year bond. This proxy therefore has a structural break, and COVID-window statistics end at 2020-05-19.
- **Frequency:** monthly averages of daily data. Only days on which all of DBAA, DGS20, VIX and SVENPY20 are available are used, so the series are always measured on the same dates. The sensitivity table also reports daily data and end-of-month values.
- **Cleaning:**
  - FRED blanks (holidays) are left missing and never interpolated.
  - Duplicate dates keep the last observation.
  - Every step's count is logged in `cleaning_log.csv`.
- **Winsorizing:** none. The crisis spikes are the signal under study. The extreme values are listed in `extreme_values.csv` instead.
- **Sample:**
  - DGS20 is missing from 1987-01 to 1993-09, and VIX starts in 1990.
  - The longest monthly sample is therefore 1993-10 to 2026-10 (397 months).
- **Regression standard errors:** t-statistics use Newey-West standard errors with 6 lags, because monthly spreads are strongly autocorrelated.
- **Expected default loss:** two benchmarks from the lecture:
  - 0.124%/yr: Moody's Baa loss rate 1982–2008 (slide 39)
  - 0.75%/yr: 1.5% default rate × 50% loss given default (Giesecke et al., slide 41)

## Slide numbering

The project brief cites slides 59 (liquidity figure), 48–51 (Merton model), 51 (VIX, corr 0.64), 54 (puzzle) and 55–58 (default losses).

In the `Ch 9 Bonds.pptx` copy included here, the same content is on slides 43, 33–36, 36, 38 and 39–42.
