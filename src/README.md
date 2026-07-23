# Actigraphy Dashboard

A React/Vite and FastAPI application for loading actigraphy files, previewing activity and light data, applying file-specific preprocessing intervals, calculating pyActigraphy metrics, detecting rest windows, reviewing diagnostics, and exporting results.

## Documentation

Start with the [documentation index](docs/README.md).

- [User guide](docs/USER_GUIDE.md)
- [File formats](docs/FILE_FORMATS.md)
- [Activity processing](docs/ACTIVITY_PROCESSING.md)
- [Metrics and algorithms](docs/METRICS_AND_ALGORITHMS.md)
- [Diagnostics and troubleshooting](docs/DIAGNOSTICS_AND_TROUBLESHOOTING.md)
- [Validation and limitations](docs/VALIDATION_AND_LIMITATIONS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Documentation maintenance](docs/DOCUMENTATION_MAINTENANCE.md)
- [Change log](docs/CHANGELOG.md)

The web interface also contains a searchable **Documentation** section. Set `VITE_GITHUB_REPOSITORY_URL` to the repository URL to expose a direct GitHub documentation link in the application.

## Core design principles

- Preserve file-level provenance and settings in every analysis output.
- Keep preview selection separate from the analysis activity basis.
- Use source/device activity for count-based files and processed epoch-level acceleration for compatible raw recordings.
- Allow partial results when one metric fails, while retaining structured diagnostics.
- Do not create fallback sleep windows when Crespo or Roenneberg returns no usable window.
- Treat a completed computation and a scientifically validated result as separate questions.
- Review daily QC: gaps, non-wear, and manual masks are never treated as zero activity, and days below 16 analyzable hours are excluded by default.
- Inspect light capability from file content rather than extension alone.
  GT3X `log.bin` lux records, GENEActiv light, and native reader channels use
  background preview/analysis jobs; files without light finish as an explicit
  skip while activity processing remains available.

## Version confirmation

After deployment, open:

```text
GET /api/version
```

Confirm the expected `app_version`, `git_commit`, and feature flags before testing large files.
