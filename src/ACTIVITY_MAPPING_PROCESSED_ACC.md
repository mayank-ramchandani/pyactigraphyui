# Processed acceleration activity basis

Processed acceleration is one of the four choices on page 3. The maintained documentation is [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md).

## Current behaviour

- `auto` selects a suitable source/device series for compatible native/count files and processed epoch-level acceleration for supported raw X/Y/Z files.
- `accelerometer` explicitly requests processed `acc`.
- `mad` and `enmo` remain available as distinct alternatives.
- Page 4 previews the activity series; page 8 selects metrics; page 9 generates results.

## Large raw files

The direct GENEActiv and GT3X readers reduce calibrated raw samples into epochs without constructing a complete high-frequency X/Y/Z DataFrame. GT3X device-local timestamps and real gaps are preserved. For exact equivalence with a particular Oxford `accProcess` release, generate and upload that release's `*timeSeries.csv.gz` output.

## Provenance and interpretation

Results and diagnostics record the requested and resolved activity basis, source/engine, units, and epoch duration. Count cut-points are not automatically valid for mg-scale processed acceleration, MAD, or ENMO.
