# User guide

The current interface uses a ten-page workflow. After at least one actigraphy file is imported, pages 2–9 are directly clickable in the left workflow. Page 10 remains locked until results are generated.

## 1. Importing Actigraphy Files

Upload one or more **actigraphy recordings only** on this page. Multiple files are supported when they use the same extension.

Optional inputs are deliberately moved to the page where they are used:

- start/stop and masking files: page 5;
- sleep diaries: page 6;
- separate light, temperature, and other sensor files: page 7.

Generic CSV files are inspected automatically. Enable manual column mapping on this page only when timestamp and activity detection is incorrect. The mapping panel can inspect timestamp, separate time, activity, light, temperature, and non-wear columns.

Localized Philips Actiware/RPX CSV exports in English, French, or German are parsed directly, including UTF-8 and Windows-1252 files. Metadata rows before the epoch table are skipped automatically, decimal-comma values are converted safely, and embedded white/RGB light channels are retained.

`PAXHR_H.csv` from NHANES is not one actigraphy recording: it contains hourly summaries for many participants and has no standalone timestamp column. The app now identifies it and explains that one `SEQN` must be selected, `PAXFDAY`/`PAXFTIME` merged from `PAXHD_H`, and a participant-relative time index constructed from `PAXSSNHP` before `PAXMTSH` can be mapped. The public files do not disclose the actual calendar date, so any synthetic anchor date must be documented.

## 2. Pre-processing

Review the project-standard data-quality rules:

- **16 analyzable hours** are required for a valid calendar day;
- **2 consecutive valid calendar days** are required for multi-day rhythm metrics and SRI eligibility;
- **80% sleep-window coverage** is required for window-dependent sleep summaries;
- detected or mapped non-wear is respected by default.

Enable **Modify the standard data-quality thresholds** only when a protocol or sensitivity analysis requires different values.

### Minimum sleep-window coverage

Coverage is the proportion of expected epochs inside a diary-defined or automatically estimated sleep window that remain recorded and scorable after:

- recording gaps;
- start/stop truncation;
- detected non-wear;
- manually selected masks.

A threshold of `0.8` means at least 80% of expected epochs must remain. A window below the threshold is excluded from TST, WASO, sleep efficiency, and other window-dependent summaries rather than filled or treated as zero activity.

## 3. Estimating Activity Metric / Magnitude of Acceleration

Choose one of four activity-basis options:

1. **Recommended source / processed `acc`**: source/device activity for count-based files and epoch-level processed acceleration for raw `.bin`, `.cwa`, and `.gt3x` files.
2. **Processed acceleration (`acc`)**: Oxford `acc` when available, or the documented compatible memory-safe path.
3. **MAD**: mean amplitude deviation of vector magnitude within each epoch.
4. **Custom ENMO (legacy)**: retained for comparison with earlier analyses.

The selected series becomes the basis for rest/activity metrics. Counts, processed mg, MAD, and ENMO are not interchangeable; report the selected mapping and units.

## 4. Activity Preview

Preview is optional but recommended. It is required for later plot-based interval selection.

Check:

- recording start and stop dates;
- clock or timezone shifts;
- long gaps;
- constant or all-zero periods;
- implausible spikes;
- whether the selected file name matches the intended recording.

Large raw recordings use background preview jobs so decoding can continue beyond ordinary request timeouts.

## 5. Cleaning and Masking

This page contains two related sections.

### Recording Start / Stop

Upload start/stop files or create per-file intervals using timestamp fields and the activity plot. These intervals define the effective recording period before masks and sleep windows are applied.

Full timestamps are used. An interval beginning at 23:00 and ending at 02:00 on the next calendar date crosses midnight correctly.

### Masking and Non-wear

Upload exclusion files, respect detected non-wear, or create per-file masks using the activity plot. File IDs are retained so one recording’s interval is not applied to another.

Missing, non-wear, and masked epochs remain unavailable. They are never converted to zero activity.

## 6. Sleep-wake Classification

### Sleep diary and custom windows

Upload diary windows or create per-file bedtime/wake-time intervals using timestamps and the activity plot. Diary windows may represent night sleep, naps, time in bed, lights-off/rise time, or other supported states.

### Sleep/rest algorithms

Choose the classification algorithm on this page. Available algorithms and their parameters are defined in `config/algorithmRegistry.json`.

When no diary window is available, the app can use pyActigraphy `Crespo_AoT` or `Roenneberg_AoT` to estimate the main rest window. No lowest-activity fallback window is inserted. If the selected method returns no usable window, window-dependent sleep metrics are reported as unavailable.

## 7. Other Sensors

### Light

Use light embedded in the selected actigraphy file or upload a separate light file. The page supports:

- light-channel inspection;
- light preview;
- multichannel/RGB preview where available;
- light-metric selection and settings.

Selected light metrics run when page 9 generates the main results. A file with no usable light still proceeds through activity analysis; light outputs are skipped with a diagnostic message.

### Temperature and additional sensors

Temperature and other sensor files can be attached for future workflow development. Their filenames and basic file metadata are retained in the exported analysis configuration, but the current version does **not** calculate temperature or generic sensor metrics and labels these uploads as future analysis.

## 8. Analysis Set-up

Choose analysis families or individual metrics and configure shared or metric-specific parameters. This page only configures the analysis; it does not run it.

For processed `acc`, MAD, or ENMO, begin with continuous non-binarized RA, IS, and IV unless the study protocol specifies a validated threshold for that signal and unit.

Use **Next** or click **Generate Results** in the left workflow to continue to page 9.

## 9. Generate Results

This page contains the only **Generate Results** action. Select the uploaded files to analyse, then run the pipeline.

The page displays:

- upload and background-job progress;
- file-level status;
- summary values and plots;
- multi-file tables;
- daily recording-quality information;
- total valid days and longest consecutive valid-day run;
- sleep-window coverage and exclusion decisions;
- QC warnings;
- requested and resolved activity mapping;
- structured diagnostics;
- light results when supported.

Results remain on page 9 for review. Successful generation unlocks page 10.

## 10. Export Outputs

Download configured outputs such as result summaries, CSV-compatible tables, JSON analysis configuration, QC information, and diagnostic reports. Exports should retain:

- source filename/file ID;
- requested and resolved activity mapping;
- units and epoch duration;
- selected sleep/rest algorithm;
- metric and algorithm parameters;
- preprocessing thresholds and intervals;
- result values and warnings;
- application/build version.

## Recommended validation workflow

1. Run one known-good small recording.
2. Compare it with an independent reference workflow.
3. Confirm valid/invalid days, gaps, non-wear, masks, and sleep-window coverage.
4. Test a medium and large file through the deployed endpoint.
5. Test an embedded-light file and a no-light file.
6. Retain diagnostic JSON and exact build identifiers.
7. Only then run a research batch.
