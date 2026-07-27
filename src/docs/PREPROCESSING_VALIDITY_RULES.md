# Preprocessing validity rules

## Where these settings are configured

Data-quality settings are configured on **page 2: Pre-processing**. The page first runs an initial per-file coverage inspection, then lets the analyst select the quality-window basis and either retain or customize the recommended thresholds. Mask files and custom exclusion intervals are configured separately on **page 5: Cleaning and Masking**.

## Initial data-coverage QC

After a recording is loaded, the application reports for each candidate 24-hour quality window:

- recorded hours;
- recording-gap hours;
- detected or mapped non-wear hours, when available;
- effective hours used for the current validity decision; and
- whether the window reaches the selected minimum-hours threshold.

This initial table is descriptive and occurs before uploaded/manual masks and start/stop limits. Final QC is recalculated during analysis after all preprocessing choices have been applied.

## Recommended settings

Unless the analyst explicitly enables **Customize the recommended data-quality thresholds**, the application uses:

- at least **16 analyzable hours** for a quality window to be valid;
- a run of at least **2 consecutive valid quality windows** for multi-window rhythm metrics and SRI eligibility; and
- at least **80% recorded and scorable coverage** for each sleep window used by TST, WASO, sleep efficiency, and other window-dependent summaries.

These values are configurable starting points rather than mandatory criteria for every protocol. Missing timestamps, non-finite activity, start/stop truncation, respected detected non-wear, and manual masks remain missing. They are not converted to zero activity.

## Quality-window basis

### Calendar day — recommended default

A calendar day is defined from midnight to midnight. This basis preserves clock-day interpretation for daily summaries and circadian timing outputs.

For a complete recording from 4 PM on day 1 to 4 PM on day 2, calendar-day QC produces:

- 8 recorded hours on the first date; and
- 16 recorded hours on the second date.

At a 16-hour threshold, the second date is valid; both dates are not automatically lost.

### Recording-aligned 24-hour windows — sensitivity option

Recording-aligned windows begin at the first retained timestamp and continue in consecutive 24-hour blocks. The same 4 PM-to-4 PM example produces one complete 24-hour quality window. This option can be useful for short recordings or protocols intentionally anchored to deployment time, but outputs should be interpreted as recording-aligned quality windows rather than clock-calendar days.

The selected basis is retained in result payloads, diagnostics, and exports.

## Customized settings

When customization is enabled, the analyst may change:

- recommended minimum valid hours per quality window: 1–24 hours;
- recommended minimum consecutive valid windows for rhythm/SRI: 1–365 windows; and
- recommended minimum sleep-window coverage: 0–1.

The backend validates and resolves these values, then stores them in results, data-quality payloads, diagnostics, and exports. Turning customization off restores the recommended numeric values even when custom values remain visible in frontend state.

## Consecutive-window rule

The application reports:

- total valid quality windows; and
- the longest uninterrupted run of valid quality windows.

IS, IV, ISm, IVm, ISp, IVp, RAp, and SRI are gated by the longest consecutive run, not merely the total valid-window count. Valid windows separated by an invalid or missing window do not satisfy a two-consecutive-window requirement.

SRI additionally uses only valid scored epoch pairs exactly 24 hours apart. Two consecutive valid windows are therefore necessary under the recommended rule but may still produce no SRI when no usable 24-hour pairs remain.

## Recommended minimum sleep-window coverage

For every diary-defined or automatically estimated sleep window:

1. determine the expected number of epochs from the window duration and epoch frequency;
2. identify epochs still recorded and scorable after gaps, start/stop truncation, non-wear, and manual masks;
3. calculate `available_scored_epochs / expected_epochs`; and
4. compare the result with the configured coverage threshold.

At the recommended threshold of `0.80`, at least 80% of expected epochs must remain. A window below the configured threshold is excluded rather than imputed or treated as complete.

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

Quality output includes the selected window basis, window start/stop, expected, recorded, gap, non-wear, manual-mask, and analyzable durations; validity status; total valid windows; longest consecutive run; and resolved recommended/customized thresholds. Sleep-window QC includes expected epochs, available/scored epochs, coverage proportion, configured threshold, and inclusion/exclusion reason.

## Method rationale and related software

The recommended calendar-day basis follows a common actigraphy convention rather than implying that every study must use the same border. GGIR defines `includedaycrit` as the minimum valid hours in a **calendar day** and uses 16 hours by default; its standard full-day segment `qwindow = c(0, 24)` runs from midnight to the following midnight. GGIR also exposes other protocol/window strategies, which supports treating recording-aligned processing as an explicit alternative rather than silently redefining a calendar day.

pyActigraphy provides the common timestamped data/mask interface used by this application. Its documentation emphasizes that masks alter downstream rest–activity metrics and should be reviewed carefully. The UI therefore reports gaps, non-wear, masks, the selected window basis, and resolved thresholds instead of converting missing or excluded epochs to zero.

Official references:

- [GGIR configuration parameters](https://wadpac.github.io/GGIR/articles/GGIRParameters.html)
- [GGIR day-segment analyses](https://wadpac.github.io/GGIR/articles/TutorialDaySegmentAnalyses.html)
- [pyActigraphy data masking](https://ghammad.github.io/pyActigraphy/pyActigraphy-Masking.html)
- [pyActigraphy BaseRaw data and mask behaviour](https://ghammad.github.io/pyActigraphy/BaseRaw.html)
