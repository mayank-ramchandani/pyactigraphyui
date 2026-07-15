# ENMO and MAD activity mapping

The web tool now accepts an `activityMapping` value of:

- `original` — preserve the reader/device activity signal.
- `enmo` — Euclidean Norm Minus One, averaged into 30-second epochs and reported in mg.
- `mad` — mean amplitude deviation of vector magnitude within each 30-second epoch, reported in mg.

## Supported inputs

- Raw GENEActiv `.bin`: ENMO and MAD are calculated by the direct streaming reader from calibrated X/Y/Z samples.
- Raw ActiGraph `.gt3x`: ENMO and MAD are calculated from calibrated X/Y/Z samples exposed by `pygt3x`.
- Oxford accelerometer `*timeSeries.csv(.gz)`: ENMO is read from an ENMO/`acc` column. MAD is accepted only when the file already contains a MAD column.
- Counts-only/native pyActigraphy files: use `original`; ENMO and MAD cannot be reconstructed after raw axes have been discarded.

Unsupported selections return a clear file-level error. The backend does not silently substitute another activity mapping.

## Interpretation

ENMO and MAD are expressed in mg. pyActigraphy circadian/non-parametric metrics can use these epoch-level series, but sleep algorithms and threshold-based metrics originally validated with device counts may not have equivalent thresholds. The selected and resolved mapping is included in previews, result tables, saved-run metadata, and diagnostic JSON.

## Quality-control behavior

QC checks are advisory and non-fatal. Periodic metrics may return arrays or Pandas objects; emptiness is checked using collection length rather than comparison with `[]`. Any unexpected QC exception is retained as a suppressed diagnostic while calculated metric results are preserved.
