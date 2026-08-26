# Preprocessing and data-quality settings

These settings are configured on **Step 2: Pre-processing**. Start/stop limits and masks are configured later on **Step 5: Cleaning and Masking**.

## Recommended starting settings

Unless customization is enabled, the application uses:

- at least **16 analyzable hours** for a quality window to be valid;
- at least **2 consecutive valid quality windows** for multi-day rhythm metrics and SRI eligibility;
- at least **80% available and scorable coverage** for a sleep window to be included in sleep summaries;
- detected or mapped non-wear when it is available from the file or selected mapping.

These values are starting points. A study protocol may require different criteria.

## Initial and final quality checks

The initial table on Step 2 summarizes each candidate quality window before manual start/stop limits and masks are applied. It shows recorded time, gaps, detected or mapped non-wear, effective analyzable time, and whether the minimum-hours threshold is met.

Final quality is recalculated during analysis after all selected preprocessing choices have been applied.

## Calendar day or recording-aligned 24-hour window

### Calendar day — recommended default

A calendar day runs from midnight to midnight. This keeps daily summaries and circadian timing aligned with clock dates.

For a recording from 4 PM on Day 1 to 4 PM on Day 2, calendar-day quality control reports 8 hours on the first date and 16 hours on the second date. At a 16-hour threshold, the second date is valid; both dates are not automatically lost.

### Recording-aligned 24-hour windows

These windows begin at the first retained timestamp and continue in 24-hour blocks. The same 4 PM-to-4 PM recording produces one complete 24-hour window.

This option can be useful for short recordings or deployment-anchored protocols. Interpret and report the outputs as recording-aligned windows rather than calendar days.

## Consecutive valid windows

The application reports both:

- the total number of valid quality windows; and
- the longest uninterrupted run of valid quality windows.

Multi-day rhythm metrics and SRI eligibility use the longest consecutive run. Two valid windows separated by an invalid or missing window do not satisfy a two-consecutive-window requirement.

SRI also requires valid scored epoch pairs exactly 24 hours apart. Meeting the consecutive-window rule does not guarantee that an SRI value can be calculated.

## Sleep-window coverage

For each diary-defined or automatically estimated sleep window, the application:

1. calculates the expected number of epochs from the window duration;
2. identifies epochs still available after gaps, start/stop limits, non-wear, and masks;
3. divides available scorable epochs by expected epochs; and
4. compares the result with the selected threshold.

At the recommended threshold of `0.80`, at least 80% of the expected epochs must remain. A lower-coverage window is excluded from TST, WASO, sleep efficiency, and other window-dependent summaries rather than filled or treated as complete.

## Other choices that affect validity and results

- **Respect detected non-wear:** applies an available wear/non-wear indicator.
- **Start/stop intervals:** define the effective recording period.
- **Masks:** exclude known invalid intervals.
- **Sleep windows:** define the intervals used for sleep summaries.
- **Activity measure:** determines the signal used by the metrics.
- **Binarization and thresholds:** can change results and must match the selected signal units.
- **Metric-specific parameters:** may change eligibility or output interpretation.

## What to report

Retain and report:

- the selected quality-window basis;
- the minimum analyzable-hours threshold;
- the minimum consecutive valid-window requirement;
- the sleep-window coverage threshold;
- whether detected non-wear was respected;
- start/stop and mask rules;
- total valid windows and longest consecutive run;
- excluded sleep windows and reasons.

## Related documentation

- [GGIR configuration parameters](https://wadpac.github.io/GGIR/articles/GGIRParameters.html)
- [GGIR day-segment analyses](https://wadpac.github.io/GGIR/articles/TutorialDaySegmentAnalyses.html)
- [pyActigraphy data masking](https://ghammad.github.io/pyActigraphy/pyActigraphy-Masking.html)
- [pyActigraphy BaseRaw data and mask behaviour](https://ghammad.github.io/pyActigraphy/BaseRaw.html)
