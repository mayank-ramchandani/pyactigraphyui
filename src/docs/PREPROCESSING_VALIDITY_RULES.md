# Preprocessing validity rules

## Where these settings are configured

Data-quality thresholds are configured on **page 2: Pre-processing**. Mask files and custom exclusion intervals are configured separately on **page 5: Cleaning and Masking**.

## Project-standard behaviour

Unless the analyst explicitly enables **Modify the standard data-quality thresholds**, the application uses:

- at least **16 analyzable hours** for a calendar day to be valid;
- a run of at least **2 consecutive valid calendar days** for multi-day rhythm metrics and SRI eligibility;
- at least **80% recorded and scorable coverage** for each sleep window used by TST, WASO, sleep efficiency, and other window-dependent summaries.

Missing timestamps, non-finite activity, start/stop truncation, respected detected non-wear, and manual masks remain missing. They are not converted to zero activity.

## Custom behaviour

When customization is enabled, the analyst may change:

- minimum valid hours per day: 1–24 hours;
- minimum consecutive valid days for rhythm/SRI: 1–365 days;
- minimum sleep-window coverage: 0–1.

The backend validates and resolves these values, then stores them in results, data-quality payloads, diagnostics, and exports. Turning customization off restores the project standards even when custom values remain visible in frontend state.

## Consecutive-day rule

The application reports:

- total valid calendar days; and
- the longest uninterrupted run of valid calendar days.

IS, IV, ISm, IVm, ISp, IVp, RAp, and SRI are gated by the longest consecutive run, not merely the total valid-day count. Valid Monday and Wednesday recordings do not satisfy a two-consecutive-day requirement when Tuesday is invalid or missing.

SRI additionally uses only valid scored epoch pairs exactly 24 hours apart. Two consecutive valid days are therefore necessary under the standard rule but may still produce no SRI when no usable 24-hour pairs remain.

## Minimum sleep-window coverage

For every diary-defined or automatically estimated sleep window:

1. determine the expected number of epochs from the window duration and epoch frequency;
2. identify epochs still recorded and scorable after gaps, start/stop truncation, non-wear, and manual masks;
3. calculate `available_scored_epochs / expected_epochs`;
4. compare the result with the configured coverage threshold.

At the default threshold of `0.80`, at least 80% of expected epochs must remain. A window below the threshold is excluded rather than imputed or treated as complete.

## Other preprocessing choices that affect results

The three threshold fields are not the only preprocessing decisions:

- **Respect detected non-wear** applies a source/native/mapped wear mask when available.
- **Start/stop intervals** define the effective recording period.
- **Uploaded and manual masks** exclude known invalid periods.
- **Sleep diary/custom windows** determine candidate sleep intervals.
- **Crespo_AoT/Roenneberg_AoT** may estimate a sleep/rest window when no diary is available.
- **Activity mapping** determines the scalar activity series used by metrics.
- Metric binarization, thresholds, resampling, and per-metric parameters may change final values.

## Outputs and reporting

Daily quality output should include expected, recorded, gap, non-wear, manual-mask, and analyzable durations; valid-day status; total valid days; longest consecutive run; and the resolved threshold values. Sleep-window QC should include expected epochs, available/scored epochs, coverage proportion, threshold, and inclusion/exclusion reason.
