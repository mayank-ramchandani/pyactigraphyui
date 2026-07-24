# Processed acceleration activity basis

Processed acceleration is one of the six choices on page 3. The maintained documentation is [docs/ACTIVITY_PROCESSING.md](docs/ACTIVITY_PROCESSING.md).

## Current behaviour

- `auto` selects source/device activity for compatible native/count files and processed epoch-level acceleration for supported raw X/Y/Z files.
- `accelerometer` explicitly requests processed `acc`.
- `enmo`, `mad`, `pim`, and `zcm` are distinct alternative scalar mappings.
- Page 4 previews the activity series; page 8 selects metric- or family-level processing; page 9 generates results.

## Large raw files

The direct GENEActiv and GT3X readers reduce calibrated raw samples into epochs without constructing a complete high-frequency X/Y/Z DataFrame. GT3X device-local timestamps, filter state, epoch state, and genuine recording gaps are preserved. Oxford `*timeSeries.csv.gz` uploads use their existing epoch-level columns directly.

## Provenance and interpretation

Results and diagnostics record the requested and resolved activity basis, source/engine, units, epoch duration, filtering, and mapping-specific parameters. Thresholds remain explicit and tied to the selected signal scale.
