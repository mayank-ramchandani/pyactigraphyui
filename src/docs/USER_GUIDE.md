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

Review the recommended data-quality settings and the initial file-coverage QC:

- **16 analyzable hours** is the recommended threshold for a valid quality window;
- **calendar-day windows** (midnight to midnight) are the recommended default for day-level summaries;
- **recording-aligned 24-hour windows** are available as an explicit sensitivity option for partial first/last calendar dates;
- **2 consecutive valid windows** is the recommended minimum for multi-day rhythm metrics and SRI eligibility;
- **80% sleep-window coverage** is required for window-dependent sleep summaries;
- detected or mapped non-wear is respected by default.

Enable **Customize recommended data-quality settings** when the study protocol or a planned sensitivity analysis requires different thresholds or window alignment.

### Minimum sleep-window coverage

Coverage is the proportion of expected epochs inside a diary-defined or automatically estimated sleep window that remain recorded and scorable after:

- recording gaps;
- start/stop truncation;
- detected non-wear;
- manually selected masks.

A threshold of `0.8` means at least 80% of expected epochs must remain. A window below the threshold is excluded from TST, WASO, sleep efficiency, and other window-dependent summaries rather than filled or treated as zero activity.

## 3. Estimating Activity Metric / Magnitude of Acceleration

Choose one of six activity-basis options:

1. **Recommended source / processed `acc`**: source/device activity for files that supply it and epoch-level processed acceleration for raw `.bin`, `.cwa`, and `.gt3x` files. For `.cwa`, the server Oxford conversion currently supplies `acc`; other mappings require matching columns in an uploaded converted time-series.
2. **Processed acceleration (`acc`)**: an existing Oxford `acc` column or the bounded-memory filtered vector-magnitude pathway.
3. **ENMO**: epoch mean of positive Euclidean Norm Minus One.
4. **MAD**: mean absolute deviation of vector magnitude within each epoch.
5. **PIM**: integral of absolute dynamic vector magnitude within each epoch.
6. **ZCM**: dead-band zero-crossing count of dynamic vector magnitude within each epoch.

The selected series becomes the basis for pyActigraphy rest/activity metrics. The result and diagnostics retain the requested/resolved mapping, units, epoch duration, and raw-processing details.

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

Choose family-level or metric-level processing in either Standard or Custom mode, then configure shared or metric-specific parameters. Core families expand to their registered pyActigraphy metrics, and the Cosinor family runs a fixed 24-hour `pyActigraphy.analysis.Cosinor` model. This page only configures the analysis; it does not run it.

For processed `acc`, ENMO, MAD, PIM, or ZCM, choose continuous or binarized processing explicitly. Threshold values remain tied to the selected signal and units and are retained in the analysis configuration.

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

## Reproducible processing check

1. Confirm the detected reader, timestamp range, epoch duration, and resolved activity mapping in the preview.
2. Review daily gaps, non-wear, masks, valid-day decisions, and sleep-window coverage.
3. Confirm that selected files, family/metric settings, and algorithm parameters appear in the analysis configuration.
4. Retain result tables, QC warnings, structured diagnostics, application version, and Git commit with each batch.
5. Use the same stored configuration when processing additional files in the same analysis.


## Reviewing submitted feedback (administrators)

Configure `FEEDBACK_ADMIN_TOKEN` and open `/?feedback-admin=1` on the deployed frontend. The protected review screen supports full-text search, category filtering, complete report inspection, and CSV/JSONL download. Feedback remains stored in `${APP_DATA_DIR}/feedback.jsonl`; use persistent mounted storage in deployment.


## Terms of use

The persistent **Terms of Use** button and the Documentation section explain OBI hosting, CFA grant support, transient raw-file processing, technical metadata/feedback retention, de-identification expectations, acceptable use, and the research/educational nature of the tool. See [TERMS_OF_USE.md](TERMS_OF_USE.md).
