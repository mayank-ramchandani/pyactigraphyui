# Activity basis and ENMO/MAD alternatives

The web tool accepts an `activityMapping` value of:

- `auto` — recommended. Use source/device activity when it exists; otherwise use processed epoch-level acceleration (`acc`) for raw X/Y/Z files.
- `accelerometer` — explicitly require the processed `acc` basis in mg.
- `original` — prefer the file's source/device activity series.
- `mad` — calculate or select mean amplitude deviation in mg.
- `enmo` — retain the direct/custom ENMO mapping for backwards-compatible comparisons.

## Supported inputs

| Input | Recommended `auto` | Processed `acc` | Source activity | MAD | Custom ENMO |
|---|---|---|---|---|---|
| Raw GENEActiv `.bin` | Processed `acc` | Yes | No native count channel | Yes | Yes |
| Raw Axivity `.cwa` | Oxford `accProcess` `acc` | Yes | No native count channel | Only if supplied | Only if supplied |
| Raw ActiGraph `.gt3x` | Processed `acc` | Yes | ActiGraph-style counts when available | Yes | Yes |
| Oxford `*timeSeries.csv(.gz)` | `acc` column | Yes | If supplied | If supplied | If supplied |
| Counts-only pyActigraphy formats | Source activity | No | Yes | No | No |

For large GENEActiv and GT3X files, direct readers stream calibrated raw data into epochs without building a whole-recording X/Y/Z DataFrame. GT3X device-local timestamps and real gaps are preserved. To reproduce a particular Oxford `accProcess` release exactly, upload that release's generated `*timeSeries.csv.gz`; the app uses its `acc` column directly.

Preview mapping and analysis mapping are independent. The resolved mapping, source/engine, units, and epoch are returned in previews, results, and diagnostics.

Count thresholds are not automatically equivalent to mg thresholds. Continuous non-binarized analysis should be considered when processed acceleration, MAD, or custom ENMO is used.
