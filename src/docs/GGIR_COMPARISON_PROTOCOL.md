# Validation plan: ActiLab versus GGIR

**Status 5 November 2026:** Runnable ActiLab-versus-GGIR benchmark scripts added; *no* paired GGIR/ActiLab raw-device benchmark results have been produced from this uploaded source alone. GGIR HDCZA/SIB sleep parity is not currently implemented in ActiLab.

## Pre-registration for each test case

Record participant de-identified code, exact raw file checksum, device type/model/firmware, wrist placement, raw rate (Hz), timezone, sensor unit, selected activity representation, epoch length, calibration options, non-wear rules, gap/imputation rules, start/stop, valid-day rule, time window, algorithm name/settings, and exact GGIR/R package and ActiLab backend commit versions.

### Required comparison tiers

1. **Input matching**: run an unmodified recording through each reader. Verify native sample timestamps, number of decoded samples, timezone, data loss and clipping status. Report separately when a modality is unsupported.
2. **Activity**: align ENMO in mg, short epoch, matching calibration and non-wear logic. Compare unmasked epoch series (when available) and masked daily and recording means. Also MAD/other metrics only when mathematically and algorithmically equivalent.
3. **Quality**: compare valid-day acceptance, recording gaps, wear/non-wear and masking. Never assume GGIR and ActiLab default quality thresholds are the same.
4. **Sleep**: compare diary-anchored sleep windows first, then automatic guider/inactivity bouts only after equivalent GGIR HDCZA/SIB implementation is supplied. **Do not** compare unrelated Cole–Kripke results and HDCZA/SIB as a pass/fail parity test.
5. **Circadian**: compare RA, L5, M10, IS, IV with the same epoch, thresholding, invalid-data treatment and timezone. PyActigraphy and GGIR may implement similarly named metrics differently.
6. **Robustness**: recordings with truncated deployment, daylight-saving shifts, interleaved gaps, non-wear, multiple devices, different sample rates and zero-variance axes; no silent imputations.

### Metrics to report

Per aligned numeric metric, report matched N, unpaired/missing N, bias (ActiLab − GGIR), MAE, RMSE, maximum absolute difference, and Pearson r when variance permits. Preset tolerances must be approved **per metric** and per scientific use; a shared single tolerance is not meaningful for sleep minutes, ENMO mg and dimensionless rhythms. Review Bland–Altman and individual discrepancies for higher-stakes research uses.

## Command-line comparison

`python validation/compare_outputs.py actilab_daily.csv ggir_matched_daily.csv --keys participant,date --metrics activity_mean_valid_epochs:ACC_day_mg --output validation_report.csv`

Replace column keys and metric mappings with the **actual** GGIR column names. The script only measures numerical agreement after matching; it does not align definitions, reproduce preprocessing, or verify scientific equivalence. Empty/no matched rows is an explicit error. Do not label this as validation until results are reviewed and published.

GGIR reference docs: https://wadpac.github.io/GGIR/articles/GGIRParameters.html ; https://wadpac.github.io/GGIR/articles/chapter4_AccMetrics.html

## Runnable ActiLab + GGIR benchmark (added 5 November 2026)

The package includes two scripts that can be run on **one de-identified raw device file**:

- `validation/benchmark_ggir.py`: sends the file to ActiLab's **Step 2 initial QC** and (unless `--qc-only`) **full analysis** endpoints, measures wall-clock time including file upload and background-job polling, and saves QC JSON/CSV, final daily and aggregated CSV, analysis JSON, configuration, SHA-256 and timings.
- `validation/run_ggir_benchmark.R`: called by Python only when `--run-ggir` is set; independently runs **GGIR Part 1 then Part 2** (or selected sequential parts through 5/6) using the original file, records elapsed time for **each** part and preserves GGIR CSV reports and logs.

### Installation (run locally on your computer)

In a Python environment: `python -m pip install requests pandas`. In **R**, install with `install.packages("GGIR")`. `Rscript` must be available on the system PATH. Start the ActiLab **backend** on `http://127.0.0.1:8000` using the deployment's pinned Python packages, or replace the URL with your own reachable ActiLab API. **The uploaded ZIP contains `src/` only, not the root web build manifest or your deployment configuration.** Run the benchmark against an already deployed/working ActiLab backend.

With a local ActiLab server and a GENEActiv `.bin` (or ActiGraph `.gt3x`) sample:

```bash
python validation/benchmark_ggir.py \
  --file "/path/to/deidentified_sample.bin" \
  --actilab-url http://127.0.0.1:8000 \
  --activity-mapping enmo --epoch 5 \
  --timezone UTC \
  --run-ggir --ggir-parts 1,2 \
  --out validation/benchmark_results
```

This will write:

| File | Contents |
|---|---|
| `actilab_initial_qc.csv` / `.json` | Step 2 coverage by calendar day, **before final masks** |
| `actilab_final_daily.csv` / `actilab_aggregated.csv` | QC and numeric outputs **after** ActiLab final masks, if analysis succeeds |
| `actilab_analysis.json` / `actilab_final_qc.json` | Results, warnings and complete final QC |
| `ggir_part2_summary.csv`, `ggir_part2_daysummary.csv`, `ggir_file_quality.csv` | Discovered GGIR Part 2 files where generated (includes auto-calibration/quality indicators not necessarily in ActiLab) |
| `benchmark_timings.csv`, `ggir_run/ggir_timing.csv` | ActiLab end-to-end wall times, GGIR Part 1/2 (and any other parts) wall times |
| `qc_overview_comparison.csv` | Recording duration and gap fields side by side; marked **not scientifically equivalent** |
| `ggir_output_manifest.json` | Which GGIR files and column names were actually found |
| `benchmark_config.json` | Input SHA-256, epoch/mapping, selected options, timezone and analysis configuration |
| `ggir_stdout.log` / `ggir_run/ggir_configuration.txt` | GGIR execution logs and version/configuration |

To run the **ActiLab QC-only speed** test, add `--qc-only`. To compare against an **existing GGIR results folder** (without re-running GGIR), use `--ggir-existing /path/to/previous_GGIR_output` instead of `--run-ggir`.

For an exploratory **full GGIR pipeline** runtime, use `--ggir-parts 1,2,3,4,5` (or include part 6 when needed). The default ActiLab benchmark intentionally requests **RA, IS and IV** with binarization off, and **no sleep**; therefore Part 1/2 runtime or GGIR Part 1–5 runtime **is not directly comparable as an identical workload**. Export a custom ActiLab configuration and pass its JSON using `--analysis-config path/to/config.json` if you want additional metrics. Do not assume ActiLab classic sleep scoring reproduces GGIR's HDCZA/SIB.

### Numeric agreement / QA

After running, inspect the GGIR CSV column names in `ggir_output_manifest.json` and ActiLab CSV headers. Use explicit crosswalks; the benchmark never guesses GGIR field names or claims scientific equivalence. Two optional comparison commands are supported:

```bash
# Example only: replace metric names with real columns in your exported CSVs.
python validation/benchmark_ggir.py \
  --file "/path/to/deidentified_sample.bin" \
  --ggir-existing "/path/to/GGIR/results-parent" \
  --summary-pairs "is:IS,iv:IV" \
  --out validation/benchmark_results
```

`--summary-pairs` uses actual ActiLab aggregated keys and GGIR Part 2 summary column names, and writes `metric_pairs_summary.csv` containing paired values and ActiLab-minus-GGIR deltas. **The example key names must be checked**: version and metric definitions may differ. For a day-level coverage comparison, supply `--ggir-date-column` and `--ggir-hours-column` together, pointing to the real GGIR Part 2 daily CSV columns. The script then writes `qc_daily_pairs.csv`, aligned on calendar date, with unpaired days retained.

For a more rigorous aligned numeric series comparison, use the existing `validation/compare_outputs.py` tool and its explicit `--keys`/`--metrics` mappings after matching timestamp/units and preprocessing. This computes bias, MAE, RMSE and correlations across many paired rows; one participant-level summary cannot provide correlation.

### Interpreting the benchmark fairly

1. **ActiLab Step 2 QC is not GGIR Part 1+2**: ActiLab's metric-specific reader must first decode/epoch-reduce the file, but QC checks timestamped epoch coverage with available non-wear masks. GGIR Part 1+2 also performs raw calibration, non-wear detection and its own QC metrics. Compare both runtimes as *workflow costs*, not as identical algorithms.
2. ActiLab `--epoch 5 --activity-mapping enmo` approximates the choice of a GGIR 5-second ENMO metric; **GGIR's default `do.cal=TRUE` is different** from ActiLab's native header/device calibration. You may run `--no-ggir-calibrate` for an additional sensitivity comparison, but this still does not guarantee equivalence.
3. GGIR uses imputation/masking and diurnal-normalization for some summary acceleration values; ActiLab daily/aggregated values are calculated from **valid observed epochs**. Do not compare similarly labeled means without proving matching definitions.
4. Initial QC and final QC have different masks. Choose which question you want to answer and use the corresponding ActiLab CSV. For partial first/last days, ActiLab calendar window gaps include non-recording hours within the full 24-hour window.
5. **Performance**: ActiLab times include HTTP upload, queue and network transfer (and are sensitive to connection bandwidth). GGIR part times are **local processing** (including R startup and disk I/O). For a closer CPU-oriented comparison, deploy ActiLab locally on the *same machine and disk* as GGIR, avoid concurrent jobs and repeat runs with warm/cold caches documented. Avoid interpreting timing differences as algorithmic advantages otherwise.
6. Date, device placement, time zones, firmware, masks, native rates and processing versions must be reported; a real research validation requires more than one file and prespecified error tolerances.

**Test status:** The code's CSV handling and paired comparison logic have automated unit tests; **GGIR itself and real ActiLab–GGIR paired raw-data results were not executed in the provided source-only session**. The scripts are a runnable protocol, not a validation result.
