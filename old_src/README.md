# ActiLab

![ActiLab logo](assets/actilab-logo.png)

A web application for importing actigraphy recordings, reviewing data quality, selecting transparent preprocessing and activity measures, classifying sleep/wake, calculating activity and light outcomes, and exporting reproducible results.

## User workflow

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

After an actigraphy file is uploaded, Steps 2–9 can be opened directly from the left workflow. Export unlocks after results are generated successfully.

## User documentation

Start with the [ActiLab user documentation](docs/README.md).

- [User guide](docs/USER_GUIDE.md)
- [Preprocessing and data-quality settings](docs/PREPROCESSING_VALIDITY_RULES.md)
- [Supported file formats](docs/FILE_FORMATS.md)
- [Choosing an activity measure](docs/ACTIVITY_PROCESSING.md)
- [Metrics and algorithms](docs/METRICS_AND_ALGORITHMS.md)
- [Methods and reproducibility](docs/PREPROCESSING_AND_PROVENANCE.md)
- [Troubleshooting](docs/DIAGNOSTICS_AND_TROUBLESHOOTING.md)
- [Terms of use](docs/TERMS_OF_USE.md)
- [What’s new](docs/CHANGELOG.md)


## Recommended first analysis

- Use de-identified files.
- Keep the recommended preprocessing settings unless the study protocol requires different criteria.
- Use the recommended source / processed acc activity measure unless a specific signal is required.
- Preview every recording before analysis.
- Review all warnings, missing metrics, valid-window decisions, and sleep-window exclusions.
- Save the exported configuration and quality-control information with the result tables.

## Scientific basis

The application uses pyActigraphy for native readers and downstream actigraphy methods. Raw accelerometer files are first converted to the selected epoch-level activity measure. Missing data, non-wear, and masks remain unavailable rather than being converted to zero activity.

See the [Methods and reproducibility guide](docs/PREPROCESSING_AND_PROVENANCE.md) for details.

## Contributions and code ownership

ActiLab accepts suggestions and pull requests, but proposed changes do not modify the protected production branch automatically. Repository protection should require maintainer/Code Owner approval before merge. See `CONTRIBUTING.md` and `GITHUB_PROTECTION_SETUP.md` at the repository root.
