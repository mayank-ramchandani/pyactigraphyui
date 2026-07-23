# Preprocessing validity rules

## Standard behaviour

The application uses the following project standards unless the analyst explicitly enables **Modify the standard data-quality thresholds** on **Pre-processing: Cleaning & Masking**:

- at least **16 analyzable hours** for a calendar day to be valid;
- a run of at least **2 consecutive valid calendar days** for multi-day rhythm metrics and SRI;
- at least **80% recorded/scored coverage** for a sleep window to contribute to TST, WASO, and sleep efficiency.

Missing timestamps, non-finite activity, respected detected non-wear, and manual mask intervals remain missing. They are not converted to zero activity.

## Custom behaviour

When customization is enabled, the analyst may change:

- minimum valid hours per day: 1–24 hours;
- minimum consecutive valid days for rhythm/SRI: 1–365 days;
- minimum sleep-window coverage: 0–1.

The resolved values are validated by the backend, stored in the data-quality payload, shown in results, and retained in diagnostics/exports. Turning customization off makes the backend use the project standards even if previously entered custom values remain in the form.

## Consecutive-day rule

The application reports both:

- total valid days; and
- the longest uninterrupted run of valid calendar days.

IS, IV, ISm, IVm, ISp, IVp, RAp, and SRI are gated by the longest consecutive run rather than the total count. For example, valid days on Monday and Wednesday do not satisfy the two-consecutive-day standard when Tuesday is invalid.

SRI additionally uses only scored epoch pairs exactly 24 hours apart. Therefore, two consecutive valid days are necessary under the project rule but may still yield no SRI if no valid 24-hour pairs remain after scoring and masking.

## Other preprocessing choices that affect results

The following are intentionally kept separate from the three threshold fields:

- **Respect detected non-wear** determines whether a source/native/mapped wear mask is applied.
- Uploaded or manually selected **mask intervals** exclude known invalid periods.
- **Start/stop intervals** define the effective recording range.
- **Sleep diary windows** or Crespo/Roenneberg determine which rest windows are summarized.
- Timezone, timestamp parsing, epoch construction, activity mapping, binarization, thresholds, and resampling frequencies can materially change metrics, but they are format- or metric-specific and should not be presented as generic valid-day rules.

Any custom setting should be justified in the study protocol and included in exported methods metadata.
