# Activity processing and mapping

Activity mapping is configured on **page 3: Estimating Activity Metric / Magnitude of Acceleration**. The selected mapping becomes the initial setting for **page 4: Activity Preview** and the basis supplied to selected rest/activity metrics.

## Terminology

### Source/device activity

An existing one-dimensional activity or count series supplied by the recording format, such as ActiGraph `.agd` counts or native Actiwatch activity.

### Raw XYZ acceleration

High-frequency X/Y/Z samples, usually expressed in gravitational units after calibration. The three axes cannot be supplied unchanged to metrics that require one activity value per epoch.

### Processed `acc`

The recommended raw-acceleration basis. Uploaded Oxford time-series files use their existing `acc` column. The compatible direct pathway follows this sequence where supported:

1. obtain calibrated X/Y/Z samples;
2. calculate vector magnitude;
3. apply a fourth-order 20 Hz low-pass filter;
4. subtract 1 g;
5. truncate negative values to zero;
6. average into the selected epochs;
7. express the result in milligravity.

Diagnostics identify the exact engine, for example `accelerometer_timeseries`, `streaming_calibrated_filtered_vm_acc`, or `pygt3x_low_level_streaming_epoch_aggregation`.

### MAD

Mean amplitude deviation of vector magnitude within each epoch. It represents within-epoch movement variability and is expressed in mg in this application.

### Custom ENMO

A legacy direct calculation based on positive vector magnitude above 1 g. It is retained for comparison but is not the recommended default when processed `acc` is available.

## Four user-facing options

| Option | Resolution behaviour |
|---|---|
| Recommended source / processed `acc` | Uses source/device activity when it exists; raw `.bin`, `.cwa`, and `.gt3x` use epoch-level processed `acc`. |
| Processed acceleration (`acc`) | Explicitly requests Oxford `acc` or the compatible memory-safe processed-acceleration path. |
| MAD | Uses or derives mean amplitude deviation when valid XYZ or a MAD column is available. |
| Custom ENMO (legacy) | Uses or derives the legacy ENMO mapping for comparison. |

The backend may record a requested and resolved mapping when a requested signal is unavailable and a documented compatible fallback is required.

## GT3X bounded-memory processing

GT3X `log.bin` activity events are decoded in bounded chunks. Calibrated X/Y/Z samples are immediately reduced into the requested epoch-level processed `acc`, MAD, ENMO, or supported count basis, then released. The loader does not call `FileReader.to_pandas()` for the full recording.

Event timestamps use the fixed timezone recorded in `info.txt`. Real gaps remain missing epochs; they are not compressed or converted to zero. Checksum failures and timestamps outside the metadata-defined range are skipped and counted in diagnostics.

Streaming ActiGraph-style counts are supported for compatible 30 Hz recordings. When an exact count pathway is not supported, the reason and resolved mapping are reported.

## Epoch processing

Chunked processing must preserve filter and epoch state between chunks. An unfinished epoch at a chunk boundary continues with the next samples. Diagnostics should report:

- raw sample rate;
- output epoch duration;
- expected samples per epoch;
- incomplete epochs;
- gaps or missing samples;
- calibration status;
- input and output units;
- requested and resolved mapping.

## Common missing-data and valid-day stage

After a scalar epoch series is produced and page-5 support intervals are parsed, every file follows the same sequence:

1. regularize the timestamp index at the detected epoch duration;
2. represent absent or non-finite epochs as missing;
3. apply start/stop limits;
4. combine reader/mapped non-wear with manual or uploaded masks when requested;
5. calculate recorded, gap, non-wear, manual-mask, and analyzable hours for each calendar day;
6. mask days below the page-2 valid-day threshold;
7. activate the final mask for metrics and sleep scoring;
8. reuse the same validity state for sleep-window coverage.

This prevents an all-missing resampling bin from becoming zero activity. Genuine recorded zeros remain valid observations.

## Multi-day eligibility

IS, IV, ISm, IVm, ISp, IVp, RAp, and SRI are gated by the configured longest consecutive valid-day run, two days by default. Invalid or missing days stay on the time axis so artificial transitions are not created across gaps.

## Binarization and thresholds

A pyActigraphy threshold such as 4 may be a count-scale convention and must not automatically be interpreted as 4 mg. For processed `acc`, MAD, and ENMO:

- begin with binarization disabled unless a validated protocol specifies otherwise;
- report continuous units;
- define and justify any threshold;
- retain threshold and binarization settings in exports.

A binarized L5 of zero can produce RA = 1 even when the continuous profile contains nonzero night-time movement.
