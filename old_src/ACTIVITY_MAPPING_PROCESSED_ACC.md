# Processed `acc` activity basis

## Default behavior

The frontend now defaults to **Recommended source / accelerometer activity**.

- Native count/activity files (`.agd`, `.awd`, `.atr`, and similar) retain their source/device activity series.
- Raw GENEActiv `.bin`, Axivity `.cwa`, and ActiGraph `.gt3x` recordings use an epoch-level processed acceleration (`acc`) basis.
- Uploaded Oxford `*timeSeries.csv.gz` files use their `acc` column directly.
- MAD and the legacy/custom ENMO mapping remain optional.

## Large raw files

The direct GENEActiv reader uses a chunked, calibrated, gravity-adjusted epoch implementation so large recordings do not have to be expanded into a high-frequency Pandas DataFrame. The diagnostics identify this engine as `streaming_calibrated_filtered_vm_acc`.

The GT3X reader likewise streams `log.bin` activity events into epochs instead
of calling whole-file `FileReader.to_pandas()`. It preserves the fixed timezone
from `info.txt`, leaves real gaps missing, and reports checksum or timestamp
records that were skipped. Diagnostics identify this engine as
`pygt3x_low_level_streaming_epoch_aggregation`.

For a result that must match a specific Oxford `accProcess` release exactly, process the raw file with that release and upload its `*timeSeries.csv.gz` output. The app will then use the generated `acc` column directly and record the detected column and package summary in diagnostics.

## Preview and analysis

The preview activity signal and analysis activity basis are now independent. Changing the preview no longer changes the signal used for metrics.

## Metric behavior

The resolved activity basis is used as `raw.data` for the selected pyActigraphy analyses. Results and diagnostics record the requested and resolved mapping, units, source column/engine, and epoch duration. Count thresholds are not treated as equivalent to mg thresholds.
