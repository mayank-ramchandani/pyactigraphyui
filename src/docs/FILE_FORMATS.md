# File formats and signal availability

Page 1 imports **actigraphy files only**. Optional start/stop and masking files are added on page 5, sleep diaries on page 6, and separate light or future temperature/other-sensor files on page 7. Support depends on both the extension and the actual columns or channels available in the file.


| Format | Typical content | Default analysis basis | Optional mappings | Important notes |
|---|---|---|---|---|
| GENEActiv `.bin` | Raw X/Y/Z and embedded light/temperature | Processed `acc` | MAD, custom ENMO | Large files use streamed decoding. Light preview exposes `LIGHT` (`log10(lux + 1)`) and `LIGHT_LUX` (lux) when available. |
| Axivity `.cwa` | Raw X/Y/Z | Processed `acc` through supported conversion | Mapping availability depends on output | Java and Oxford `accelerometer` dependencies may be required. |
| ActiGraph `.gt3x` | Raw calibrated X/Y/Z; optional timestamped lux records | Processed `acc` | MAD, custom ENMO, 30 Hz ActiGraph-style counts | `log.bin` activity is streamed directly to epochs. Official type-`0x05` lux records are inspected and streamed separately when present; no-light files skip light outputs without affecting activity. |
| ActiGraph `.agd` | Device count/activity series | Source/device activity | Normally none | Preferred when the analysis is intended to remain on the ActiGraph count scale. |
| Actiwatch `.awd` and other native pyActigraphy formats | Device activity | Source/device activity | Normally none | Reader and metric availability depend on the corresponding pyActigraphy class. |
| Oxford `*timeSeries.csv(.gz)` | Epoch-level `acc` and related columns | Existing `acc` column | Existing compatible columns | Use when exact output from a chosen `accProcess` version is required. |
| Generic CSV/TSV | User-defined timestamp/activity or XYZ | Source activity when supplied | Derived mapping only from valid XYZ | Timestamp and activity columns may need manual mapping. |
| Excel/ODS | Tabular activity or XYZ | Source activity when supplied | Conditional | Very large spreadsheets are not recommended for raw high-frequency data. |

All formats enter the same downstream missingness, mask, valid-day, and
sleep-window coverage stage once a scalar activity series is available. The
signal basis differs by format; the validity rules do not.

| Input path | Recording gaps | Automatic/mapped non-wear |
|---|---|---|
| Raw GT3X streaming | Missing epochs preserved | Not inferred from low activity |
| Direct GENEActiv BIN streaming | Missing epochs preserved | Not inferred from low activity |
| Converted BIN/CWA or Oxford time-series | Missing timestamps/values preserved | Used only when supplied by the series/reader |
| Native pyActigraphy formats | Missing values preserved | Existing reader mask respected when available and enabled |
| Mapped tabular input | Missing values preserved | `nonwear`/`mask`/`offwrist`: 1 means excluded; `wear`/`worn`: 1 means worn |

## Raw X/Y/Z is not a pyActigraphy activity series

Most pyActigraphy metrics operate on one timestamp-indexed activity series. Three raw axes must first be converted into a scalar epoch-level signal such as processed `acc`, MAD, ENMO, vector magnitude, or validated device counts.

## Units and calibration

For XYZ-derived calculations, the application must know or correctly infer:

- acceleration units;
- calibration or scale factors;
- sampling frequency;
- timestamp alignment;
- epoch duration;
- gaps and incomplete epochs.

A generic CSV containing arbitrary X/Y/Z values should not be treated as calibrated acceleration without explicit metadata.

## Large GT3X recordings

The backend does not construct a whole-recording raw Pandas DataFrame. It keeps
only a bounded X/Y/Z chunk and the epoch-level output. Diagnostics include raw
samples reduced, events read, checksum failures, impossible timestamps skipped,
missing output epochs, calibration method, and requested/resolved mapping.

Large recordings are submitted as background preview/analysis jobs. The server
returns a job ID after receiving the upload, and the frontend polls for progress
and the final result while decoding and metrics continue outside the original
HTTP request. The browser-to-server upload itself must still complete within the
hosting platform's ingress deadline.

## Light source routing

Light capability is determined from file contents and reader channels, not the
extension alone. When no separate light file is selected, the selected
actigraphy file is inspected:

- current-format GT3X archives are scanned for checksum-valid `log.bin` record
  type `0x05`, defined by ActiGraph as a two-byte little-endian lux value;
- GENEActiv `.bin` and native pyActigraphy readers expose their available
  embedded channels;
- files without usable light return `light_detection.status = not_present`,
  and light preview/metrics are skipped while activity processing continues.

GT3X lux values are averaged into 30-second epochs by default and exposed as
`LIGHT_LUX` (lux) and `LIGHT` (`log10(lux + 1)`). Real gaps remain missing.
Light-only GT3X inspection never decodes X/Y/Z activity payloads.

Large light preview, channel discovery, and batch light analysis use background
jobs. One preview load returns the standard plot, available channels, and the
initial multichannel/RGB preview. All selected light metrics are calculated
from one loaded recording in one background job rather than one upload/decode
per metric.

Legacy GT3X archives containing `activity.bin`/`lux.bin` instead of `log.bin`
remain outside this streaming reader.

Format references:

- [ActiGraph current GT3X log-record format](https://github.com/actigraph/GT3X-File-Format)
- [ActiGraph legacy NHANES GT3X format](https://github.com/actigraph/NHANES-GT3X-File-Format)

## Exact Oxford processing

The direct memory-safe pathway is designed to approximate the documented processed-acceleration sequence without materializing the entire raw recording in memory. It may not be byte-identical to every Oxford `accProcess` release because complete autocalibration and interpolation details can differ.

For release-specific reproducibility:

```text
raw .bin/.cwa/.gt3x
→ selected accProcess release
→ *timeSeries.csv.gz
→ upload generated file
```
