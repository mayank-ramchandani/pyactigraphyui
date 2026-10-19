# Validation plan: ActiLab versus GGIR

**Status 19 October 2026:** Comparison harness included; *no* paired GGIR/ActiLab raw-device benchmark results have been produced from this uploaded source alone. GGIR HDCZA/SIB sleep parity is not currently implemented in ActiLab.

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
