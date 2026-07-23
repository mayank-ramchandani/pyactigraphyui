# User guide

## 1. Select files

Upload one or more actigraphy recordings. Optional files may define start/stop limits, masking/non-wear intervals, sleep diary windows, light data, or temperature data.

For initial validation, begin with one known-good file rather than a large batch.

## 2. Map generic tabular files

CSV or spreadsheet files may require timestamp and activity columns to be selected. Light, temperature, non-wear, and XYZ columns can also be mapped when present.

Confirm:

- timestamps parse correctly;
- timezone assumptions are known;
- activity units are known;
- rows are ordered and not duplicated;
- the epoch interval is plausible.

## 3. Preview activity

The preview is for visual inspection. It can display a different signal from the activity basis later selected for analysis.

For large raw files, the upload starts a background preview job. Keep the page
open while the interface polls the job; decoding may continue beyond the
hosting platform's ordinary HTTP request deadline.

Check:

- recording start and stop dates;
- obvious clock or timezone shifts;
- long gaps;
- all-zero or constant periods;
- implausible spikes;
- whether the selected file matches the file ID shown.

## 4. Preview light

Review available light channels and units. Light preview is optional and does
not affect activity metrics unless light metrics are explicitly selected.

Large light files are processed as background jobs. Choose **Load Light
Preview** to inspect the selected separate light file, or the selected
actigraphy file when no separate file is supplied.

- If usable light exists, the response includes the plot, channel list, units,
  and initial multichannel/RGB sample.
- If it does not, the page reports that inspection completed with no embedded
  light measurements and skips light plots and metrics.
- Activity preview and analysis continue in either case.

For current-format `.gt3x`, the light-only reader scans `log.bin` for official
type-`0x05` lux records without decoding raw acceleration. It exposes raw lux
as `LIGHT_LUX` and `log10(lux + 1)` as `LIGHT`. A GT9X Link file without a lux
sensor will therefore produce the expected no-light status, not a server error.

Selected light metrics run together in one background job after one content
inspection/load. Thresholds entered in lux are converted to the selected
channel scale automatically.

## 5. Start/stop intervals

Start/stop intervals define the effective recording period. They can be uploaded or selected manually for each file.

Intervals use full timestamps. An interval beginning at 23:00 and ending at 02:00 on the next calendar day is valid and crosses midnight correctly.

## 6. Cleaning and masking

Mask invalid periods, confirmed non-wear, device artefacts, or other intervals that should not contribute to analysis. Do not silently replace missing or masked data with zero activity.

The same page controls the shared data-quality rules. The project standards remain active unless **Modify the standard data-quality thresholds** is enabled:

- **Respect detected non-wear** uses a source/native/mapped mask when available;
- **Minimum valid hours per day** defaults to 16 h;
- **Minimum consecutive valid days for rhythm/SRI** defaults to 2 days;
- **Minimum sleep-window coverage** defaults to 0.80 (80%).

These rules run independently for every selected file. Uploaded and manual
intervals remain associated with their file ID.

## 7. Sleep diary

Diary windows can supply reported bedtimes, wake times, naps, or in-bed intervals. If diary windows are unavailable, Crespo or Roenneberg can be selected to estimate rest windows. The application does not generate a fallback window when detection fails.

## 8. Algorithms and analysis setup

Select:

- files to analyse;
- analysis activity basis;
- metrics or analysis families;
- sleep/rest algorithm;
- binarization and thresholds;
- full-file or selected analysis intervals;
- light metrics and channels.

For processed `acc`, MAD, or ENMO, begin with continuous non-binarized RA, IS, and IV. Count thresholds are not automatically valid for milligravity signals.

## 9. Generate results

The interface reports upload progress, the background-job state, current
backend stage, stage number, pipeline percentage, and raw-page/sample progress
where available. Keep the page open until the completed result is retrieved.

Review:

- results by file ID;
- QC warnings;
- per-file daily recording quality;
- sleep-window coverage and exclusion decisions;
- M10/L5 components for RA;
- detected sleep-window count;
- activity mapping and units;
- failed, warning, or skipped stages;
- memory and timing diagnostics.

## 10. Export

Exports should retain the source filename, requested and resolved activity mapping, units, epoch duration, algorithm, parameters, preprocessing intervals, results, warnings, and application version.

## Recommended validation workflow

1. Run a known-good small file.
2. Compare results with an independent reference workflow.
3. Run the same file locally, inside the deployed container, and through the public endpoint.
4. Add medium and large recordings.
5. Retain diagnostic JSON reports and exact build identifiers.
6. Confirm valid/invalid/completely missing days and sleep-window coverage.
7. Only then run a research batch.
