# ENMO and MAD activity mapping

The activity-analysis workflow now accepts an `activityMapping` form field with:

- `original`: use the reader/device's existing activity signal.
- `enmo`: calculate or select Euclidean Norm Minus One and report epoch values in mg.
- `mad`: calculate mean amplitude deviation of vector magnitude and report epoch values in mg.

## Supported inputs

| Input | Original | ENMO | MAD |
|---|---:|---:|---:|
| Raw GENEActiv `.bin` | Yes (currently resolves to ENMO) | Yes | Yes |
| Raw ActiGraph `.gt3x` | Yes (ActiLife-style counts when available) | Yes | Yes |
| Oxford `*timeSeries.csv(.gz)` | Yes | Yes when an `acc`/ENMO column is present | Yes only when a MAD column is present |
| Raw `.cwa` or non-GENEActiv `.bin` through `accProcess` | Yes | Yes when `accProcess` returns its ENMO/`acc` column | Not reconstructed from epoch ENMO |
| Counts-only pyActigraphy formats such as `.agd`/`.awd` | Yes | No | No |

Unsupported combinations return a clear file-level error. The backend does not silently substitute another mapping.

## Calculations

For calibrated raw axes in g:

- `VM = sqrt(x^2 + y^2 + z^2)`
- `ENMO_mg = mean(max(VM - 1, 0)) * 1000` within each epoch
- `MAD_mg = mean(abs(VM - mean(VM))) * 1000` within each epoch

GENEActiv MAD is accumulated page-by-page into 30-second epochs, avoiding a full high-frequency recording DataFrame in memory. GT3X currently uses the existing pygt3x DataFrame path.

## Interpretation warning

ENMO and MAD are continuous acceleration mappings in mg. Sleep-scoring and activity-threshold parameters validated for proprietary/device counts may not be directly transferable. The UI and QC diagnostics display a warning when a sleep algorithm is used with ENMO or MAD.

## Quality-control correction

Periodic metrics such as ISP, IVP, and RAP may return NumPy arrays or Pandas Series. QC now checks emptiness using `len(value) == 0`; it no longer compares these objects to `[]`, which previously caused errors such as:

`('Lengths must match to compare', (3,), (0,))`
