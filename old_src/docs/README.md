# Documentation index

This directory is the long-form GitHub documentation for the Actigraphy Dashboard. The in-app Documentation page provides a searchable operational reference and links directly to this directory.

| Document | Audience | Purpose |
|---|---|---|
| [User guide](USER_GUIDE.md) | Analysts and researchers | Current ten-page workflow, direct navigation, and interpretation checks |
| [Preprocessing validity rules](PREPROCESSING_VALIDITY_RULES.md) | Analysts and researchers | Valid-day hours, consecutive-day requirements, sleep-window coverage, missingness, and related choices |
| [File formats](FILE_FORMATS.md) | Analysts and developers | Supported signals, readers, embedded light, and format-specific behaviour |
| [Activity processing](ACTIVITY_PROCESSING.md) | Researchers and developers | Four activity-basis options, processed `acc`, MAD, ENMO, epochs, and units |
| [Metrics and algorithms](METRICS_AND_ALGORITHMS.md) | Researchers | Analysis families, individual metrics, sleep/rest algorithms, parameters, and outputs |
| [Diagnostics and troubleshooting](DIAGNOSTICS_AND_TROUBLESHOOTING.md) | Analysts and operators | Progress, background jobs, QC, transport failures, logs, and debugging |
| [Validation and limitations](VALIDATION_AND_LIMITATIONS.md) | Researchers and reviewers | Scientific validation expectations and known limitations |
| [Architecture](ARCHITECTURE.md) | Developers | Frontend/backend modules, current workflow components, registries, and API endpoints |
| [Deployment](DEPLOYMENT.md) | Operators | Environment variables, GitHub documentation link, Azure/proxy concerns, storage, and release checks |
| [Documentation maintenance](DOCUMENTATION_MAINTENANCE.md) | Maintainers | Synchronizing in-app full-content search and GitHub documentation |
| [Change log](CHANGELOG.md) | Everyone | User-visible method and application changes |

## Current application workflow

1. Importing Actigraphy Files
2. Pre-processing
3. Estimating Activity Metric / Magnitude of Acceleration
4. Activity Preview
5. Cleaning and Masking
6. Sleep-wake Classification
7. Other Sensors
8. Analysis Set-up
9. Generate Results
10. Export Outputs

After actigraphy files are imported, pages 2–9 are directly clickable in the left workflow. Export unlocks after results are generated.

## Documentation conventions

- **Source/device activity** means an activity or count series supplied by the source file.
- **Raw acceleration** means high-frequency X/Y/Z measurements and is not itself a single pyActigraphy activity series.
- **Processed `acc`** means epoch-level, gravity-adjusted acceleration produced by Oxford `accProcess` or the compatible memory-safe pathway recorded in diagnostics.
- **Activity mapping** means the scalar activity basis supplied to rest/activity metrics.
- **Valid day** means a calendar day meeting the configured analyzable-hours threshold.
- **Consecutive valid days** means one uninterrupted calendar-day run.
- **Sleep-window coverage** means the proportion of expected epochs inside a sleep window that remain recorded and scorable after gaps, non-wear, and masks.
- **Window** means a full-timestamp rest/sleep interval; no heuristic fallback window is inserted.

Last consolidated: **2026-07-23**.
