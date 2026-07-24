# Actigraphy Dashboard

A React/Vite and FastAPI application for importing actigraphy recordings, applying transparent preprocessing and file-specific cleaning, estimating an activity basis, classifying sleep/wake, analysing activity/light outcomes, reviewing quality diagnostics, and exporting results.

## Current ten-page workflow

1. Import Actigraphy Files
2. Pre-processing
3. Estimating Activity Metric / Magnitude of Acceleration
4. Activity Preview
5. Cleaning and Masking
6. Sleep-Wake Classification
7. Other Sensors
8. Analysis Setup
9. Generate Results
10. Export Outputs

After an actigraphy file is imported, pages 2–9 can be opened directly from the left workflow. Page 10 unlocks only after results are generated successfully.

Page 2 keeps the project standards active unless the user explicitly enables custom thresholds: 16 analyzable hours per valid day, two consecutive valid days for multi-day rhythm/SRI eligibility, and 80% minimum sleep-window coverage. Sleep-window coverage is the proportion of expected epochs inside a proposed sleep window that remain available and scorable after gaps, non-wear, and masks.

## Documentation

Start with the [documentation index](docs/README.md).

- [User guide](docs/USER_GUIDE.md)
- [Preprocessing validity rules](docs/PREPROCESSING_VALIDITY_RULES.md)
- [File formats](docs/FILE_FORMATS.md)
- [Activity processing](docs/ACTIVITY_PROCESSING.md)
- [Metrics and algorithms](docs/METRICS_AND_ALGORITHMS.md)
- [Diagnostics and troubleshooting](docs/DIAGNOSTICS_AND_TROUBLESHOOTING.md)
- [Validation and limitations](docs/VALIDATION_AND_LIMITATIONS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Documentation maintenance](docs/DOCUMENTATION_MAINTENANCE.md)
- [Change log](docs/CHANGELOG.md)

The in-app **Documentation** page searches full explanatory content as well as workflow labels, formats, algorithms, metrics, families, diagnostics, and developer guidance. It always displays a clickable GitHub documentation link. Configure the exact targets with:

```text
VITE_GITHUB_REPOSITORY_URL=https://github.com/owner/repository
VITE_GITHUB_DOCS_URL=https://github.com/owner/repository/tree/main/src/docs
```

## Core design principles

- Preserve file-level provenance and resolved settings in every analysis output.
- Keep activity-basis estimation explicit and show the resolved signal, engine, units, and epoch.
- Offer four activity choices: recommended/automatic, processed acceleration, MAD, and ENMO.
- Keep missing data, excluded non-wear, and manual masks as missing rather than zero activity.
- Report total valid days and the longest uninterrupted valid-day run.
- Exclude sleep windows below the configured coverage threshold rather than silently treating missing epochs as sleep or wake.
- Allow partial results when one metric fails while retaining structured diagnostics.
- Do not create fallback sleep windows when Crespo or Roenneberg returns no usable window.
- Inspect light capability from file content rather than extension alone; no-light files remain valid for activity analysis.
- Label temperature and generic sensor analysis as future functionality until calculations are implemented.
- Treat a completed computation and a scientifically validated result as separate questions.

## Version confirmation

After deployment, open:

```text
GET /api/version
```

Confirm the expected `app_version`, `git_commit`, and feature flags before testing large files.
