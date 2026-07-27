# Activity processing and mapping

Activity mapping is configured on **page 3: Estimating Activity Metric / Magnitude of Acceleration**. The selected epoch-level series is used for activity preview and becomes the basis supplied to pyActigraphy rest–activity metrics.

## pyActigraphy basis

The application uses pyActigraphy for native readers and downstream actigraphy calculations. Raw tri-axial files require a one-dimensional epoch series first; the web backend performs that bounded-memory preprocessing and then attaches the resolved signal and units to the pyActigraphy-compatible raw object.

- Documentation: https://ghammad.github.io/pyActigraphy/
- Source: https://github.com/ghammad/pyActigraphy
- Package paper: https://doi.org/10.1371/journal.pcbi.1009514

## Six activity-basis options

| Option | Processing behaviour | Units |
|---|---|---|
| Recommended source / processed `acc` | Uses the file's source/device activity when available; raw `.bin`, `.cwa`, and `.gt3x` use epoch-level processed acceleration. | Source-dependent or mg |
| Processed acceleration (`acc`) | Uses an Oxford `acc` column when supplied, or filtered vector magnitude minus 1 g, negative values truncated, and averaged by epoch. | mg |
| MAD | Mean absolute deviation of vector magnitude within each epoch. | mg |
| ENMO | Mean positive Euclidean Norm Minus One within each epoch. | mg |
| PIM | Integral of absolute dynamic vector magnitude across each epoch. | mg·s/epoch |
| ZCM | Count of dead-band sign changes in dynamic vector magnitude across each epoch. | crossings/epoch |

The backend records both the requested and resolved mapping, activity column or raw-sample engine, units, epoch duration, and mapping-specific parameters.

## Raw accelerometer preprocessing

For supported raw `.bin` and `.gt3x` inputs, the memory-safe path performs the following steps without materializing the full recording:

1. decode and calibrate X/Y/Z samples;
2. calculate vector magnitude;
3. apply a fourth-order 20 Hz low-pass filter when the sample rate permits for processed `acc`, PIM, and ZCM;
4. calculate the selected signal:
   - processed `acc`: `max(filtered VM − 1 g, 0)`;
   - ENMO: `max(VM − 1 g, 0)`;
   - MAD: mean absolute deviation of VM;
   - PIM: sum/integral of `abs(filtered VM − 1 g)` over time;
   - ZCM: sign-change count for `filtered VM − 1 g` outside the configured dead band;
5. aggregate directly into output epochs;
6. retain genuine timestamp gaps as missing epochs.

PIM and ZCM preserve accumulator state across contiguous chunks. ZCM resets sign continuity across gaps so missing recording periods do not create artificial crossings. The default ZCM dead band is 4 mg and can be changed with `ACTIVITY_ZCM_THRESHOLD_MG`.

## Format-specific behaviour

- **GT3X:** `log.bin` activity events are decoded in bounded chunks. Calibrated axes are reduced immediately to the selected activity basis. Compatible 30 Hz source-count processing remains available through the source/original mapping.
- **GENEActiv BIN:** pages are decoded directly, with light and temperature summarized alongside the activity series. Activity aggregation is streamed by epoch.
- **Axivity CWA:** processing uses the supported Oxford accelerometer conversion path, whose standard server output is epoch-level `acc`. ENMO, MAD, PIM, or ZCM can be selected only when the uploaded converted time-series explicitly contains that column.
- **Oxford `timeSeries.csv(.gz)`:** existing `acc`, ENMO, MAD, PIM, or ZCM columns are used directly when selected.
- **Actiwatch ATR:** explicit PIM and ZCM requests are passed to pyActigraphy's native ATR reader mode.
- **Generic mapped tabular input:** the mapped activity column is used as supplied and labelled with the requested basis; no raw XYZ reconstruction is performed.

## Missingness, masks, and valid days

After the scalar series is built, every file follows the common preprocessing sequence:

1. regularize timestamps at the detected epoch duration;
2. preserve absent/non-finite epochs as missing;
3. apply per-file start/stop limits;
4. combine mapped/reader non-wear and manual/uploaded masks;
5. calculate recorded, gap, non-wear, masked, and analyzable hours by calendar day;
6. exclude days below the configured valid-day threshold;
7. apply the same availability state to sleep-window coverage and downstream metrics.

Recorded zeros remain data. Missing, masked, and non-wear epochs remain unavailable.

## Thresholds and binarization

Counts, mg, mg·s/epoch, and crossings/epoch are different scales. Binarization thresholds therefore remain explicit configuration values and are stored with the result. Continuous analysis is available for RA, IS, IV, M10, L5, and related measures; binarization can be enabled when the selected method requires it.
