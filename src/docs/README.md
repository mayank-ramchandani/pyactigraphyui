# Documentation index

This directory is the long-form source of truth for the Actigraphy Dashboard. The in-app Documentation page is a concise operational reference generated partly from the application registries.

| Document | Audience | Purpose |
|---|---|---|
| [User guide](USER_GUIDE.md) | Analysts and researchers | End-to-end workflow and interpretation checks |
| [File formats](FILE_FORMATS.md) | Analysts and developers | Supported signals, readers, and format-specific behaviour |
| [Activity processing](ACTIVITY_PROCESSING.md) | Researchers and developers | Source activity, processed `acc`, MAD, ENMO, epochs, and thresholds |
| [Preprocessing validity rules](PREPROCESSING_VALIDITY_RULES.md) | Analysts and researchers | Standard/custom valid-day, consecutive-day, sleep-window, and missingness rules |
| [Metrics and algorithms](METRICS_AND_ALGORITHMS.md) | Researchers | pyActigraphy metrics, sleep/rest algorithms, parameters, and outputs |
| [Diagnostics and troubleshooting](DIAGNOSTICS_AND_TROUBLESHOOTING.md) | Analysts and operators | Stage reports, progress, transport failures, logs, and debugging |
| [Validation and limitations](VALIDATION_AND_LIMITATIONS.md) | Researchers and reviewers | Scientific validation expectations and known limitations |
| [Architecture](ARCHITECTURE.md) | Developers | Frontend/backend modules, data flow, registries, and API endpoints |
| [Deployment](DEPLOYMENT.md) | Operators | Environment variables, Azure/proxy concerns, storage, and release checks |
| [Documentation maintenance](DOCUMENTATION_MAINTENANCE.md) | Maintainers | How to keep in-app and GitHub documentation synchronized |
| [Change log](CHANGELOG.md) | Everyone | User-visible method and application changes |

## Documentation conventions

- **Source/device activity** means an activity or count series supplied by the source file.
- **Raw acceleration** means high-frequency X/Y/Z measurements and is not itself a single pyActigraphy activity series.
- **Processed `acc`** means epoch-level, gravity-adjusted acceleration produced by Oxford `accProcess` or the compatible memory-safe pathway recorded in diagnostics.
- **Mapping** means the scalar activity basis supplied to pyActigraphy metrics.
- **Window** means a timestamped rest or sleep-analysis interval; no heuristic fallback window is inserted.

Last consolidated: **2026-07-23**.
