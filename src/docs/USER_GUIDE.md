# User guide

This guide follows the ten pages in the application. For a standard first analysis, keep the recommended preprocessing and activity settings, preview every recording, review warnings, and export the configuration with the results.

## Before you begin

- Upload only data that you are authorized to process.
- Remove names, health-card numbers, dates of birth, and other direct identifiers from filenames and support files.
- Prepare one or more actigraphy recordings in a supported format.
- Use the same file extension when uploading multiple files together.
- On the Results page, multiple selected files can be analyzed separately (default) or explicitly joined as one participant timeline when they all belong to the same participant. Joined analysis preserves original timestamps and gaps, removes duplicate boundary timestamps, and requires compatible sampling intervals. Light metrics remain file-level and should be run separately.
- Keep sleep diaries, start/stop files, masks, and separate sensor files ready if they are part of the study protocol.

## 1. Importing Actigraphy Files

Upload one or more actigraphy recordings. Supporting files are added later, beside the setting they affect:

- start/stop files and masks: Step 5;
- sleep diaries: Step 6;
- separate light or other sensor files: Step 7.

For CSV or TXT files, the application attempts to detect timestamp, activity, light, temperature, and non-wear columns. Enable manual mapping only when the detected columns are incorrect.

After upload, confirm that each file appears in the list and that duplicate filenames can be distinguished by their file ID.

## 2. Pre-processing

Review the initial recording-coverage table and the recommended settings:

- at least **16 analyzable hours** for a valid quality window;
- **calendar-day windows** as the recommended default;
- at least **2 consecutive valid quality windows** for multi-day rhythm metrics and SRI eligibility;
- at least **80% sleep-window coverage** for sleep summaries;
- detected or mapped non-wear respected when available.

Choose recording-aligned 24-hour windows only when the study is intentionally organized around deployment time or when you are performing a sensitivity analysis for short recordings.

Customize the recommended thresholds only when your protocol or analysis plan specifies different values.

## 3. Estimating Activity Metric

For most analyses, choose **Recommended source / processed acc**. It uses the file’s existing activity series when available and produces processed epoch-level acceleration for supported raw accelerometer files.

Other choices are:

- **Processed acceleration (acc):** gravity-adjusted epoch-level acceleration;
- **ENMO:** positive Euclidean Norm Minus One;
- **MAD:** mean amplitude deviation;
- **PIM:** integrated dynamic movement intensity within each epoch;
- **ZCM:** movement-frequency measure based on zero crossings.

The selected measure becomes the activity basis for the chosen rest-activity metrics. Thresholds must match the selected units.

## 4. Activity Preview

Preview each recording before analysis. Check:

- recording start and stop dates;
- expected recording duration;
- long gaps or missing periods;
- constant or all-zero sections;
- implausible spikes;
- clock or timezone shifts;
- whether the selected file and activity measure are correct.

The preview is also needed for plot-based interval selection in later steps.

## 5. Cleaning and Masking

### Recording start and stop

Use start/stop intervals to define the effective recording period for each file. Intervals can be uploaded or selected from the activity plot. Full timestamps are supported, including intervals that cross midnight.

### Masks and non-wear

Use masks to exclude known invalid or non-wear periods. Confirm that each interval is assigned to the correct file ID.

Missing, masked, and non-wear epochs remain unavailable. They are not converted to zero activity.

## 6. Sleep-wake Classification

Upload a sleep diary or create file-specific bedtime and wake-time windows when available.

Choose the sleep/rest classification method required by the protocol. When no diary window is available, Crespo_AoT or Roenneberg_AoT can estimate a main rest window. The application does not create a lowest-activity fallback window if the selected method finds no usable interval.

A sleep result may be unavailable when:

- no sleep window was supplied or detected;
- the classification method could not score the signal;
- the window did not meet the configured coverage threshold.

## 7. Other Sensors

### Light

Use light embedded in a supported actigraphy file or upload a separate light file. Review the available channels and preview the signal before selecting light metrics.

A file with no usable light still proceeds through activity analysis. Only the light outputs are skipped.

### Temperature and additional sensors

Temperature and other sensor files can be attached for record-keeping, but the current version does not calculate temperature or generic sensor metrics. These files are labelled as not yet analysed.

## 8. Analysis Set-up

Use **Standard mode** for common analysis groups and recommended starting parameters. Use **Custom mode** when individual metrics or protocol-specific settings are required.

Available families include:

- amplitude;
- rhythm;
- sleep;
- fragmentation;
- Cosinor.

Step 8 configures the analysis. It does not run it.

## 9. Generate Results

Select the files to analyse and choose **Generate Results**.

Review:

- file-level status;
- summary values and plots;
- daily recording-quality information;
- total valid windows and longest consecutive valid-window run;
- sleep-window coverage and exclusions;
- warnings and unavailable metrics;
- requested and resolved activity measure;
- light results when supported.

A warning means processing continued but something requires review. A failed status means the affected stage could not produce a usable result. Other successful outputs may still be available.

## 10. Export Outputs

Download the outputs needed for analysis and reporting. Keep the exported configuration and quality-control information with the result tables.

Exports can include:

- result summaries and CSV-ready tables;
- plots;
- selected files and file IDs;
- activity measure, units, and epoch duration;
- preprocessing thresholds and intervals;
- sleep/rest algorithms and parameters;
- warnings and unavailable-result explanations;
- application version and reproducibility information.

## Final review checklist

Before using the results:

1. Confirm the correct files and recording dates were analysed.
2. Review gaps, non-wear, masks, and valid-window decisions.
3. Review sleep-window coverage and any excluded windows.
4. Confirm that the activity measure and thresholds match the study plan.
5. Review every warning, failed stage, and unavailable metric.
6. Save the result tables, configuration, quality-control outputs, and version information together.

## Getting help

Use the feedback form when a problem cannot be resolved from the troubleshooting guide. Include the workflow step, affected filename, file format, selected activity measure, request ID, and exact visible message. Do not include participant identifiers or raw measurements in the feedback text.
