# ActiLab user documentation

![ActiLab logo](../assets/actilab-logo.png)

This directory contains the public documentation for researchers and analysts using ActiLab. It focuses on completing the workflow, choosing appropriate settings, understanding outputs, and resolving common user-level problems.

## Start here

1. Read the [User guide](USER_GUIDE.md) for the complete ten-step workflow.
2. Review [Preprocessing and data-quality settings](PREPROCESSING_VALIDITY_RULES.md) before changing the recommended Analysis settings in Step 8.
3. Check [Supported file formats](FILE_FORMATS.md) and [Choosing an activity measure](ACTIVITY_PROCESSING.md) when preparing data.
4. Use [Metrics and algorithms](METRICS_AND_ALGORITHMS.md) to understand the available analyses.
5. Use [Troubleshooting](DIAGNOSTICS_AND_TROUBLESHOOTING.md) when a result is missing or a run fails.

## Documentation by task

| I need to… | Read… |
|---|---|
| Complete an analysis from upload to export | [User guide](USER_GUIDE.md) |
| Decide whether to keep or change the recommended quality thresholds | [Preprocessing and data-quality settings](PREPROCESSING_VALIDITY_RULES.md) |
| Confirm whether a recording or CSV layout is supported | [Supported file formats](FILE_FORMATS.md) |
| Choose between processed acceleration, ENMO, MAD, PIM, ZCM, or source counts | [Choosing an activity measure](ACTIVITY_PROCESSING.md) |
| Join recordings collected at different native sampling rates | [Choosing an activity measure](ACTIVITY_PROCESSING.md#joining-recordings-with-different-native-sampling-rates) |
| Understand RA, IS, IV, SRI, sleep metrics, fragmentation, or Cosinor | [Metrics and algorithms](METRICS_AND_ALGORITHMS.md) |
| Understand how preprocessing choices are recorded | [Methods and reproducibility](PREPROCESSING_AND_PROVENANCE.md) |
| Resolve warnings, unavailable metrics, upload errors, or missing sleep windows | [Troubleshooting](DIAGNOSTICS_AND_TROUBLESHOOTING.md) |
| Review privacy, data handling, and acceptable use | [Terms of use](TERMS_OF_USE.md) |
| See recent user-visible changes | [What’s new](CHANGELOG.md) |

## Workflow

1. Importing Actigraphy Files
2. Pre-processing
3. Estimating Activity Metric
4. Activity Preview
5. Cleaning and Masking
6. Sleep-wake Classification
7. Other Sensors
8. Analysis Set-up
9. Generate Results
10. Export Outputs

After at least one actigraphy file is uploaded, Steps 2–9 can be opened directly from the left workflow. Export unlocks after results are generated successfully.

## Key terms

- **Activity measure:** the one-dimensional epoch-level series used for actigraphy calculations, such as device counts, processed acceleration, ENMO, MAD, PIM, or ZCM.
- **Analytical epoch:** the common epoch duration used after raw processing (for example, 30 seconds); this is different from the device's native sampling rate in Hz.
- **Analyzable time:** recorded time that remains after gaps, non-wear, start/stop limits, and masks are applied.
- **Valid quality window:** a calendar day or recording-aligned 24-hour window that meets the selected minimum analyzable-hours threshold.
- **Sleep-window coverage:** the proportion of expected epochs inside a sleep window that remain available and scorable.
- **Unavailable result:** a metric that could not be calculated because required data, valid windows, sleep windows, or supported signals were not available.
- **Warning:** processing continued, but the result or data quality requires review.

Last updated: **2026-09-10**.
