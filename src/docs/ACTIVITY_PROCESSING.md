# Activity processing and mapping

## Terminology

### Source/device activity

An existing one-dimensional activity or count series supplied by the recording format. Examples include `.agd` activity counts and native Actiwatch activity.

### Raw XYZ acceleration

High-frequency X/Y/Z samples, usually expressed in gravitational units after calibration. These axes cannot be supplied unchanged to metrics expecting one activity value per epoch.

### Processed `acc`

The recommended raw-acceleration basis. Uploaded Oxford time-series files use their existing `acc` column. Direct memory-safe processing follows this sequence where supported:

1. obtain calibrated X/Y/Z samples;
2. compute vector magnitude;
3. apply a fourth-order 20 Hz low-pass filter;
4. subtract 1 g;
5. truncate negative values to zero;
6. average into the selected epochs;
7. express the result in milligravity.

Diagnostics identify the exact engine used, such as:

- `accelerometer_timeseries`;
- `streaming_calibrated_filtered_vm_acc`;
- `pygt3x_calibrated_filtered_vm_acc`.

### MAD

Mean amplitude deviation of vector magnitude within each epoch. It summarizes within-epoch movement variability and is expressed in mg in the application.

### Custom ENMO

A legacy direct calculation based on positive vector magnitude above 1 g. It is retained for comparison but is not the recommended default when processed `acc` is available.

## Default mapping rules

```text
Does the file provide a source/device activity series?
  Yes → use source/device activity.
  No  → does it provide supported raw XYZ?
          Yes → use processed acc.
          No  → activity analysis is unavailable until a valid activity column is mapped.
```

Preview mapping and analysis mapping are independent.

## Epoch processing

Chunked raw processing must preserve filter and epoch state between chunks. An unfinished epoch at the end of one chunk must be continued with samples from the next chunk. Gaps should remain missing rather than being interpreted as inactivity.

Diagnostics should report:

- raw sample rate;
- output epoch duration;
- expected samples per epoch;
- incomplete epochs;
- missing samples or gaps;
- calibration status;
- input and output units;
- requested and resolved mapping.

## Use with metrics

The resolved scalar activity series becomes `raw.data` for selected pyActigraphy analyses. This is appropriate computationally for RA, M10/L5, IS, IV, activity profiles, and compatible fragmentation calculations.

Scientific comparability still depends on signal scale and preprocessing. A metric calculated from device counts is not numerically interchangeable with the same metric calculated from mg.

## Binarization and thresholds

The default pyActigraphy threshold of 4 is a count-scale convention and should not automatically be applied as 4 mg. For processed `acc`, MAD, and ENMO:

- start with binarization disabled;
- report the continuous units;
- define any threshold explicitly and justify it;
- retain the threshold in exports and methods text.

A binarized L5 of zero can produce RA = 1 even when the continuous activity profile has nonzero night-time movement.
