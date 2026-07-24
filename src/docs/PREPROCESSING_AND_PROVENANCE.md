# Preprocessing, provenance, and interpretation

## Computational foundation

The application uses **pyActigraphy** as the computational basis for native actigraphy readers, non-parametric rest–activity metrics, sleep/rest procedures, and advanced analysis components such as Cosinor. The web interface adds file ingestion, bounded-memory raw-accelerometer reduction, explicit preprocessing, per-file interval handling, diagnostics, and export around those calculations.

Primary references:

- pyActigraphy documentation: https://ghammad.github.io/pyActigraphy/
- pyActigraphy source: https://github.com/ghammad/pyActigraphy
- Hammad G, Reyt M, Beliy N, et al. *pyActigraphy: Open-source python package for actigraphy data visualization and analysis*. PLOS Computational Biology. 2021;17(10):e1009514. https://doi.org/10.1371/journal.pcbi.1009514

Where the source format has a native pyActigraphy reader, the application calls that reader and retains the file-provided activity scale. Raw `.bin`, `.cwa`, and `.gt3x` recordings first require a scalar epoch-level activity series; the selected mapping and its processing details are attached to the raw object before pyActigraphy metrics are called.

## Preprocessing sequence

The analysis pipeline records and applies the following stages in order:

1. **Reader and encoding detection** — identify the native reader, raw accelerometer path, localized RPX table, Oxford time-series, or mapped tabular input.
2. **Timestamp parsing** — preserve the stored clock time/timezone where present, sort records, remove duplicate timestamps, and infer the epoch interval.
3. **Calibration and scalar activity construction** — use a source activity channel or derive processed `acc`, ENMO, MAD, PIM, or ZCM from calibrated tri-axial samples.
4. **Epoch regularization** — align the scalar series to its detected epoch grid. Missing timestamps remain missing rather than becoming zero activity.
5. **Start/stop limits** — apply uploaded or manually selected per-file recording bounds.
6. **Non-wear and masks** — combine reader-provided or mapped non-wear with uploaded/manual exclusion intervals when enabled.
7. **Daily data-quality accounting** — calculate expected, recorded, gap, non-wear, masked, and analyzable hours for each calendar day.
8. **Valid-day masking** — exclude days below the configured analyzable-hours threshold and retain invalid days on the time axis.
9. **Sleep-window preparation** — apply diary/custom windows or pyActigraphy Crespo_AoT/Roenneberg_AoT windows and enforce minimum window coverage.
10. **Metric/family execution** — call the selected pyActigraphy-backed metrics or analysis families on the cleaned activity series.
11. **QC, diagnostics, and export** — retain resolved settings, warnings, file identifiers, software versions, and intermediate quality summaries.

## Activity mappings

| Mapping | Raw-sample definition or source | Units |
|---|---|---|
| Recommended source / processed `acc` | Existing device/source activity when supplied; otherwise filtered, gravity-adjusted epoch mean for raw XYZ | Source-dependent or mg |
| Processed acceleration (`acc`) | Existing Oxford `acc` column or the memory-safe filtered vector-magnitude path | mg |
| ENMO | Mean positive Euclidean Norm Minus One within the epoch | mg |
| MAD | Mean absolute deviation of vector magnitude within the epoch | mg |
| PIM | Integral of absolute dynamic vector magnitude within the epoch | mg·s/epoch |
| ZCM | Dead-band sign changes of dynamic vector magnitude within the epoch | crossings/epoch |

For raw GT3X and GENEActiv data, PIM and ZCM use streaming accumulators. Filter state, epoch state, and sign continuity are retained across contiguous chunks; continuity is reset across genuine recording gaps. The ZCM dead band defaults to 4 mg and can be configured with `ACTIVITY_ZCM_THRESHOLD_MG`.

For Actiwatch ATR inputs, explicit PIM and ZCM selections are passed to pyActigraphy's native ATR reader modes. For generic mapped tabular input, the selected activity column is treated as the requested mapping as supplied; raw-sample reconstruction is not attempted.

## Missing data, non-wear, and valid days

Absent samples, excluded non-wear, and manual masks remain unavailable. Recorded zeros remain valid observations. This distinction is retained through resampling, daily summaries, sleep-window scoring, and rest–activity metrics.

The default preprocessing thresholds are:

- at least 16 analyzable hours for a valid calendar day;
- at least 2 consecutive valid calendar days for multi-day rhythm/SRI eligibility;
- at least 80% available/scorable epochs within each sleep window.

Each threshold is configurable on the Pre-processing page and is stored in the analysis configuration and diagnostics.

## Sleep/rest processing

Diary/custom windows are used when available. Otherwise, the selected pyActigraphy `Crespo_AoT` or `Roenneberg_AoT` procedure can estimate rest windows. No additional fallback window is inserted. Window-dependent summaries retain the source, method, parameters, expected epochs, available epochs, coverage, and exclusion reason.

## Family-level analysis

Family-level processing is available from the Analysis Set-up page in both Standard and Custom modes. Core families expand to their registered pyActigraphy-backed metrics. The Cosinor family calls `pyActigraphy.analysis.Cosinor` using a fixed 24-hour single-component model and reports mesor, amplitude, acrophase, derived peak clock time, BIC, reduced chi-square, valid epochs, and epoch frequency.

## Provenance retained with results

Each file-level result should retain:

- source filename and file ID;
- reader/file format and processing engine;
- requested and resolved activity mapping;
- activity units, sample rate, and epoch duration;
- filtering/calibration details for raw accelerometer inputs;
- start/stop, non-wear, mask, valid-day, and sleep-window settings;
- selected metric/family and algorithm parameters;
- application version, Git commit, and relevant dependency versions;
- QC warnings and structured diagnostic stages.

These fields make the exported result self-describing and allow the same preprocessing configuration to be applied consistently across files and deployments.
