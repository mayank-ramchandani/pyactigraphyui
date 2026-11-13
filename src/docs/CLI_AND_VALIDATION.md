# ActiLab command-line processing, high-priority metrics, and GGIR validation

**Status: research/testing release — not a validated equivalent of GGIR.** This guide describes the *actual scripts in this source package*. Native GGIR and pyActigraphy have different readers, non-wear, sleep, and metric conventions. Never label unlike quantities as interchangeable solely because their column names match.

## 1. Set up on Linux, macOS, or WSL

Use **Python 3.10** for the backend's pinned older scientific packages. A fresh Python 3.12 environment is not guaranteed to satisfy all the pinned dependencies.

```bash
cd src
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m validation.actilab_cli --help
```

For statistical comparisons only, `pip install numpy pandas scipy` is sufficient; these scripts do not require the full ActiLab backend. For the existing HTTP-based benchmark, additionally `pip install requests` and, if running GGIR, install R and `install.packages('GGIR')` from inside R. No ActiLab server is required for `validation.actilab_cli` or `validation.pyactigraphy_reference`; the HTTP benchmark needs a reachable backend URL.

Your source upload provides **`src/` only**, not the original root `package.json` / deployment files. The supplied update is therefore a replacement `src/` directory, not a guaranteed one-command full-stack deployment package.

## 2. Run processing locally: the stages

The Linux shortcut and Python entrypoint are equivalent:

```bash
# From src/: local batch and raw GENEActiv streaming QC; no server upload
./validation/run_actilab_linux.sh '/data/actigraphy/*.bin' \
  --stage qc --activity enmo --epoch 30 --out results/qc

# Full activity, sleep, light and final CSV/JSON exports
python -m validation.actilab_cli '/data/actigraphy/sample.bin' \
  --stage all --activity enmo --epoch 30 --sleep-algorithm roenneberg \
  --min-valid-hours 16 --min-consecutive-days 2 --out results/full

# Restrict to high-priority pyActigraphy rhythm metrics
python -m validation.actilab_cli '/data/actigraphy/sample.bin' \
  --stage rhythm --metrics is,iv,ra,l5,m10,kra,kar \
  --binarize --activity-threshold 4 --out results/rhythm_binary

# Sleep scoring: Rest/sleep classification, NOT wear/non-wear detection
python -m validation.actilab_cli '/data/actigraphy/sample.bin' \
  --stage sleep --sleep-algorithm crespo \
  --sleep-windows /data/sleep_windows.csv --out results/sleep

# Light only; will explicitly report unavailable when light channel absent
python -m validation.actilab_cli '/data/actigraphy/sample.bin' \
  --stage light --light-threshold 500 --out results/light
```

A folder path is accepted. Quoted globs expand in Python. Individual files, folders, and file patterns are processed separately (the CLI does **not** concatenate different devices or participants). Each input gets a unique folder and `batch_status.csv` gives errors without stopping the other files, unless `--fail-fast` is set. For clinical data, run the CLI on encrypted/approved storage and avoid uploading to a cloud server if your governance requires local processing.

| Stage | Execution | Key outputs |
|---|---|---|
| **Import** | Detect/parse file and select activity basis (`auto`, `enmo`, `mad`, etc.). `.bin` and `.gt3x` use the ActiLab loaders. | Reader identified in `initial_qc.json` |
| **Initial QC** | Report recording gaps, existing native masks, GGIR-*inspired* raw-triaxial non-wear, native sample rate, 24-hour coverage | `initial_qc.json`, `initial_qc_calendar_day.csv`, `initial_qc_recording_anchored.csv` |
| **Final QC** | Apply configured valid-hours/day, non-wear, manual restrictions, and minimum valid-day criteria; missing ≠ zero | `final_qc.json`, `qc_daily.csv`, `cleaned_epochs.csv` |
| **Rhythm** | Direct pyActigraphy metric calls via the same ActiLab analysis dispatcher as web UI | `metrics_full.json`, `metric_availability.csv` |
| **Sleep** | Choose Crespo, Roenneberg, Cole–Kripke, etc.; only compute when compatible with reader/scoring | `metrics_full.json`, `daily.csv` when valid nights exist |
| **Light** | Available native light channels and pyActigraphy light functions, user lux threshold | `light_full.json` or an `issues.json` entry |
| **Export** | Actual QC-based daily and aggregated results and complete settings/provenance | `daily.csv`, `aggregated.csv`, `release_metadata.json`, `run_config.json` |

**Export interpretation:** `daily.csv` is primarily the 24-hour QC-window and activity summary. Do not assume period-series/profile metrics were magically transformed into valid daily numbers; period results remain in JSON. `aggregated.csv` contains true recording-level scalars only. A value's omission is not a zero. Check `metric_availability.csv` and diagnostic JSON.

### Main terminal options

| Option | Meaning / default |
|---|---|
| `--stage` | `qc`, `rhythm`, `sleep`, `light`, `all` (default `all`) |
| `--activity` | `auto`, `original`, `accelerometer`, `enmo`, `mad`, `pim`, `zcm`, `tat` (default `auto`) |
| `--epoch` | Analytical epoch in seconds: 5, 10, 15, 30, or 60 (default 30). Not the original sampling rate. |
| `--min-valid-hours` | Per QC day/24-h window, default 16 hours after exclusions |
| `--day-mode` | `calendar_day` or `recording_anchored` (default calendar) |
| `--min-consecutive-days` | Minimum valid QC windows for rhythm/SRI; default 2 |
| `--ignore-nonwear` | Opt out of automatic detected non-wear masking; detection metadata remains visible |
| `--sleep-algorithm` | `roenneberg`, `crespo`, `cole_kripke`, `sadeh`, `oakley`, `scripps` (default Roenneberg) |
| `--sleep-windows` | Optional CSV with `start,stop` timestamps. Use source timezone consistently. |
| `--sleep-metrics` | Comma-separated IDs e.g. `sri,sleep_midpoint,tst,waso,sleep_efficiency` |
| `--metrics` | Comma-separated rest/activity IDs, e.g. `ra,is,iv,l5,m10,l5p,m10p,rap,pra,par,kra,kar` |
| `--binarize` / `--activity-threshold` | Convert for binary activity state, optionally threshold=4 in source units. Avoid applying count threshold=4 to ENMO mg without a substantive reason. |
| `--metric-freq` | pyActigraphy resampling bin e.g. `1min`, `1h` (default `1min`) |
| `--period` | Consecutive period duration for periodic metrics (default `7D`) |
| `--light-threshold` / `--light-channel` | Lux input (default 500), optional channel selector |
| `--config` | Optional settings JSON; see below |
| `--out` | Output root folder; default `actilab_cli_results` |
| `--fail-fast` | Stop processing the batch on the first exception |

`--help` is the complete, version-matched option reference. For original XYX CSV data, the timestamp and calibrated three-axis columns must be mapped (units must be known; **do not** guess units). For example create `config.json`:

```json
{
  "csv_mapping": {
    "timestamp_col": "timestamp",
    "x_col": "x_g",
    "y_col": "y_g",
    "z_col": "z_g",
    "acceleration_unit": "g"
  },
  "sleep_window_settings": { "estimateWithoutDiary": false },
  "sleep_algorithm_params": {}
}
```

Then: `python -m validation.actilab_cli /data/accelerometer_xyz.csv --config config.json --stage qc --out qc_xyz`.

## 3. Non-wear detection is not rest/sleep detection

The new `backend/nonwear.py` streams **native calibrated X/Y/Z acceleration in g** during supported GENEActiv `.bin`, ActiGraph `.gt3x`, and mapped XYZ CSV import. It groups native samples in 15-minute blocks, evaluates rolling **60-minute** windows using **at least two axes** with a low standard deviation (<0.013 g) **and** range (<0.05 g), requires ≥90% of expected native samples, and marks the central 15 minutes of a qualifying window. It records detected intervals and `windows_checked` in the QC JSON. This is a **conservative GGIR-inspired screen**, not a GGIR code port or proof of identical results. GGIR's precise calibration, alternative 2013/2023 choices, neighboring-epoch refinement, and handling can differ. The thresholds/method are fixed for this first release; inspect `nonwear_detection` in exported QC and avoid claiming it is equivalent to the chosen GGIR non-wear version.

**Crespo and Roenneberg classify activity/rest or sleep; they are not non-wear algorithms**. They remain selectable for *sleep* downstream. A stationary watch on a sleeping person's wrist is not sufficient to classify non-wear by itself. For count-only data or short raw recordings with no testable 60-minute window, automatic raw non-wear status is **unavailable**. Non-wear and recording gaps are separately reported. The default QC threshold is 16 analyzable hours; this is configurable for final QC. A flat acceleration file may yield false non-wear; always inspect known non-wear episodes and agreement against GGIR.

**High-priority GGIR-style QC fields currently available:** `samplefreq` when native sampling frequency is known; `N_valid_hours` per QC window; `nonwear_perc_day` for detected non-wear divided by recorded time (a **different possible denominator than GGIR**); `Nvaliddays`, `Nvaliddays_WD`, `Nvaliddays_WE`. The uploaded catalog's sleep-period fields `nonwear_perc_spt` and `nonwear_perc_day_spt` are **not yet calculated**, as they require a validated SPT definition and alignment. Do not equate them to the current `nonwear_perc_day`.

## 4. High-priority metric catalog and method provenance

The audit of **all 118 rows** of the supplied `METRIC_CATALOG.xlsx` is `docs/METRIC_CATALOG_IMPLEMENTATION_STATUS.csv`. Of its **42 High-priority rows**, **30 have implemented pathways (subject to reader/valid-data conditions)**, **one is partial** and **11 remain pending**. This is an *implementation* inventory, **not validation of numerical equivalence**.

- **pyActigraphy high-priority**: daily activity profile; IS/ISm/ISp; IV/IVm/IVp; L5/L5p; M10/M10p; RA/RAp; pRA/pAR/kRA/kAR; SRI; SleepMidPoint; and the listed eight light metrics. Rhythm methods call pyActigraphy methods directly when supplied by the input raw object. Outputs respect recorded data/masks and eligibility. Periodic and profile results are not incorrectly averaged to scalars.
- **GGIR high-priority QC**: sample frequency, valid-hours/day, non-wear percent/day and valid-day counts are exposed as described, but GGIR numerical parity has not been established.
- **GGIR standard and extended cosinor (11 metrics)**: **pending**. The app's existing `pyActigraphy.analysis.Cosinor` family is **not** GGIR's log-transformed standard/ActCR extended fitting. These metrics must be calculated using actual GGIR/ActCR on a matched valid input, or a carefully validated port, before ActiLab outputs can receive GGIR names such as `cosinorExt_alpha` or `cosinor_R2`.

The catalog is authoritative for metric selection; the generated implementation-status CSV preserves all original columns plus code location and a limitation note. Non-High items remain candidates, not promised work.

## 5. Independent native pyActigraphy method comparison

`validation/pyactigraphy_reference.py` calls **pyActigraphy methods directly** instead of calling ActiLab's metric dispatcher. For `.bin` and `.gt3x`, it can run on a **shared ActiLab cleaned epoch input** so you can assess whether ActiLab's metric wrappers and pyActigraphy's direct methods agree for the *same data*. This is **not an independent raw-reader/preprocessing pipeline** — an important limitation in any three-way figure or paper.

```bash
# Use the exact folder produced by the ActiLab CLI, and the original recording filename:
python -m validation.pyactigraphy_reference \
  --epochs 'results/full/sample.bin_a1b2c3d4/cleaned_epochs.csv' \
  --source-name 'sample.bin' \
  --metrics RA,IS,IV,L5,M10,kRA,kAR \
  --freq 1min --out results/pyactigraphy_reference

# For native pyActigraphy reader-supported formats:
python -m validation.pyactigraphy_reference \
  --native '/data/subject.agd' --source-name 'subject.agd' \
  --out results/reference_agd
```

The hashed subfolder name above is **illustrative**; use the actual folder named in your `batch_status.csv`. This tool exports `pyactigraphy_aggregated.csv`, `pyactigraphy_metric_status.csv`, `method_config.json`. Scalar results only go into the wide aggregated table. The metric-status table explicitly identifies unavailable methods, profiles and arrays. It does not silently average L5p/M10p/ISp distributions.

## 6. GGIR benchmark, separately from pyActigraphy

ActiLab includes the earlier `validation/benchmark_ggir.py` (HTTP benchmark) and `validation/run_ggir_benchmark.R`:

```bash
# R library: install.packages('GGIR')
python validation/benchmark_ggir.py \
  --file '/data/sample.bin' --actilab-url 'http://127.0.0.1:8000' \
  --activity-mapping enmo --epoch 5 --timezone UTC \
  --run-ggir --ggir-parts 1,2 --out results/benchmark

# Re-use already-generated GGIR files (for example part 2 daily summaries)
python validation/benchmark_ggir.py \
  --file '/data/sample.bin' --actilab-url 'http://127.0.0.1:8000' \
  --ggir-existing '/data/GGIR_output' --out results/benchmark_existing
```

ActiLab's local CLI works without the API; GGIR R operates independently on the raw file. See [GGIR comparison protocol](GGIR_COMPARISON_PROTOCOL.md) for matching coverage, time, native calibration, and GGIR output folder discovery. A local CLI versus GGIR R *timing comparison* needs separate timing collection; HTTP benchmark timing includes network upload/queue and cannot be treated as same-machine CPU comparisons.

## 7. Statistical agreement: pairwise and three-way

For *categorical* outcomes (e.g. day valid yes/no or aligned epoch sleep/wake), report Cohen's **kappa**, observed agreement, confusion counts and sensitivity/specificity/F1 when binary. For ordinal scores, also use quadratic-weighted kappa. For *continuous* metrics, report paired N, missing N, mean signed bias, MAE, RMSE, Pearson/Spearman, **Lin's concordance coefficient**, two-way absolute-agreement ICC(A,1), and **Bland–Altman bias/95% limits of agreement**. These have distinct interpretations. Cohen's kappa on continuous acceleration is not appropriate. Agreement is not evidence that scoring or calibration are scientifically equivalent. With very few matched points, estimates may be undefined.

All inputs must have a **unique matching key** in each tool. Rename/crosswalk source columns to the same `source_file` / `date` identifiers first. Timezone, clock/day boundaries, epoch size, units, native input and validity criteria must match. If you have only one recording-level aggregate, most correlations and agreement intervals are uninformative; compare multiple files, days, or aligned epochs.

```bash
# Example: daily non-wear/coverage comparison; alter GGIR column names to real names.
python validation/compare_outputs.py \
  'results/actilab_daily_aligned.csv' 'results/ggir_daily_aligned.csv' \
  --keys source_file,date \
  --metrics 'N_valid_hours:valid_hours,nonwear_perc_day:nonwear_perc_day' \
  --categorical 'valid_day:valid_day' \
  --positive True --output results/ggir_agreement.csv \
  --matched-output results/paired_daily_rows.csv

# Native pyActigraphy vs ActiLab on same input (per recording)
python validation/compare_outputs.py \
  'results/actilab_aggregated_aligned.csv' 'results/pyactigraphy_aggregated_aligned.csv' \
  --keys source_file --left-name actilab --right-name pyactigraphy \
  --metrics 'ra:RA,is:IS,iv:IV' --output results/pyactigraphy_agreement.csv
```

Commands use **illustrative** GGIR keys/metric fields; read actual files first. The script fails rather than silently joining on ambiguous rows. The signed bias is always **left minus right**.

For all three at once, create `mapping.json` containing the actual per-tool column names:

```json
{
  "continuous": {
    "RA": ["ra", "RA", "RA"],
    "IS": ["is", "IS", "IS"]
  },
  "categorical": {
    "valid_day": ["valid_day", "valid_day", "valid_day"]
  }
}
```

```bash
python validation/compare_three.py \
  --actilab results/actilab_aligned.csv \
  --ggir results/ggir_aligned.csv \
  --pyactigraphy results/pyactigraphy_aligned.csv \
  --keys source_file,date --mapping mapping.json --out results/three_way
```

Three outputs: `three_way_pairwise.csv` (three sets of kappa / agreement summaries using **each pair's** matched rows), `three_way_three_way.csv` (only rows matched by **all three**), and `three_way_matched_rows.csv` (audit trail). **Do not mix day-level GGIR fields with recording-level pyActigraphy summaries** — aggregate all to recording level or calculate matched per-day values separately. The included reference pyActigraphy exporter is recording-level, so its natural triple key is **`source_file`**, not `source_file,date`, unless you independently construct and validate per-day values.

## 8. Tests and methodological review checklist

From `src/`:

```bash
python -m unittest backend.tests.test_data_quality backend.tests.test_nonwear_screening validation.test_compare_statistics validation.test_benchmark_ggir -v
```

Before drawing scientific conclusions, run a matched set of real, de-identified `.bin` and `.gt3x` files, including known removed-watch periods and sleep windows. Compare raw timestamps, native rate, gap handling, ENMO calibration, wear episodes, valid hours, RA/IS/IV, and paired sleep classifications **at the same resolution**. Record GGIR version/parameters, pyActigraphy version, ActiLab commit, units, epoch/timezone and exclusions. Confirm any threshold for 'acceptable agreement' with the investigators **per metric**, not as one global tolerance.

**References:** [GGIR quality assessment](https://wadpac.github.io/GGIR/articles/chapter3_QualityAssessment.html), [GGIR metric processing](https://wadpac.github.io/GGIR/articles/chapter4_AccMetrics.html), [GGIR circadian/cosinor analysis](https://wadpac.github.io/GGIR/articles/chapter13_CircadianRhythm.html), [pyActigraphy metrics](https://ghammad.github.io/pyActigraphy/MetricsMixin.html), [pyActigraphy sleep algorithms](https://ghammad.github.io/pyActigraphy/pyActigraphy-Sleep-Algorithms.html).
