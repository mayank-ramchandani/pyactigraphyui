# Choosing an activity measure

The activity measure is selected on **Step 3: Estimating Activity Metric**. It becomes the epoch-level signal used by the selected rest-activity analyses.

## Recommended choice

Use **Recommended source / processed acc** unless the study protocol requires a specific measure.

- Files that already contain device activity or counts use that source series.
- Supported raw `.bin`, `.cwa`, and `.gt3x` files use an epoch-level processed acceleration series.

This setting provides a consistent default while preserving the original count scale when a file is already count-based.

## Available measures

| Measure | What it represents | Typical units |
|---|---|---|
| Recommended source / processed acc | Source activity when supplied; otherwise processed epoch-level acceleration | Source-dependent or mg |
| Processed acceleration (acc) | Gravity-adjusted acceleration summarized by epoch | mg |
| ENMO | Positive Euclidean Norm Minus One summarized by epoch | mg |
| MAD | Mean amplitude deviation of vector magnitude within an epoch | mg |
| PIM | Integrated dynamic movement intensity within an epoch | mg·s/epoch |
| ZCM | Frequency of dead-band zero crossings within an epoch | crossings/epoch |

## How to choose

Choose a specific measure when:

- it is required by the study protocol;
- you need comparability with a previous analysis;
- a validated threshold or interpretation is tied to that signal;
- the selected file already contains the desired epoch-level column.

Do not compare thresholds across counts, mg, mg·s/epoch, and crossings/epoch as though they were the same scale.

## Raw accelerometer files

Raw X/Y/Z acceleration must be reduced to one scalar epoch-level series before pyActigraphy metrics can be calculated. Depending on the selected measure, the application calibrates the axes, calculates vector magnitude, applies the relevant signal processing, summarizes by epoch, and preserves genuine recording gaps as missing.

The exact resolved measure, units, epoch duration, and processing details are included with the results.

## Joining recordings with different native sampling rates

When **Join as one participant timeline** is selected, ActiLab distinguishes the device's **native/raw sampling rate** (for example, 30 Hz or 100 Hz) from the **analytical epoch** used for actigraphy analysis (for example, 30-second epochs).

ActiLab does **not** concatenate raw samples recorded at different frequencies. Instead, each source recording is processed independently at its own native sampling rate into the selected activity representation, summarized to the same analytical epoch, and only then joined by timestamp. Original timestamps and true gaps between recordings are preserved. Native sampling rates are retained in QC, preview information, results, and provenance.

For joined files with different native sampling rates:

| Activity representation | Behaviour |
|---|---|
| ENMO | Join allowed with an informational notice |
| Processed acceleration | Join allowed with an informational notice |
| MAD | Join allowed with a warning |
| PIM | Join allowed with a warning |
| ZCM | Join allowed with a strong warning because zero-crossing counts are sampling-frequency sensitive |
| Source/device activity or ActiGraph counts | Join blocked across differing native sampling rates unless the inputs have already been externally harmonized/validated |

The join is also blocked if the processed epoch durations differ or if the files resolve to different activity measures or units. Matching the analytical epoch does not mean that the original recordings had the same sampling rate; ActiLab records that distinction explicitly.

## Existing time-series columns

For Oxford time-series and mapped tabular files, an existing acc, ENMO, MAD, PIM, ZCM, or activity column can be used directly. Confirm that the column units and epoch duration are correct before analysis.

Mapping a generic activity column labels and uses that column as supplied. It does not reconstruct raw X/Y/Z processing.

## Missingness and masks

After the activity series is created:

1. timestamps are regularized at the detected epoch duration;
2. missing values remain missing;
3. start/stop limits are applied;
4. non-wear and masks are applied;
5. quality-window and sleep-window coverage are calculated;
6. eligible metrics are run.

Recorded zeros remain data. Missing, masked, and non-wear epochs do not become zero activity.

## Binarization and thresholds

Some analyses can use continuous activity, while others may use a thresholded active/rest series. Keep thresholds tied to the selected signal and units. The chosen binarization setting and threshold are included in the exported analysis configuration.

## pyActigraphy references

- [pyActigraphy documentation](https://ghammad.github.io/pyActigraphy/)
- [pyActigraphy source code](https://github.com/ghammad/pyActigraphy)
- [pyActigraphy package paper](https://doi.org/10.1371/journal.pcbi.1009514)
