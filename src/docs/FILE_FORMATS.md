# Supported file formats

Upload actigraphy recordings on **Step 1**. Add start/stop files and masks on Step 5, sleep diaries on Step 6, and separate light or other sensor files on Step 8.

Support depends on both the file extension and the signals or columns actually contained in the file.

| Format | Typical content | Recommended activity basis | User notes |
|---|---|---|---|
| GENEActiv `.bin` | Raw X/Y/Z acceleration, light, and temperature | Recommended source / processed acc | ENMO, MAD, PIM, and ZCM are available. Embedded light is used when present. |
| Axivity `.cwa` | Raw X/Y/Z acceleration | Processed acc | Other measures require corresponding columns in a converted time-series file. |
| ActiGraph `.gt3x` | Raw X/Y/Z acceleration, with optional lux | Recommended source / processed acc | A file without light can still be analysed for activity. |
| ActiGraph `.agd` | Device activity counts | Source/device activity | Use when the analysis should remain on the ActiGraph count scale. |
| Actiwatch `.awd` and other native pyActigraphy formats | Device activity | Source/device activity | Available options depend on the information supported by the reader. |
| Oxford `*timeSeries.csv(.gz)` | Epoch-level processed acceleration | Existing acc column | Existing ENMO, MAD, PIM, or ZCM columns can also be selected. |
| Philips Actiware/RPX CSV | Epoch activity with optional white/RGB light | Source activity | English, French, and German exports are supported. |
| Generic CSV/TXT | User-defined timestamp, activity, and sensor columns | Mapped activity column | Automatic detection is attempted first; manual mapping is available. |
| NHANES `PAXHR_H` | Hourly summaries for multiple participants | PAXMTSH after preparation | Prepare one participant and a participant-relative time index before upload. |
| Excel/ODS | Tabular activity data | Mapped source activity | Avoid very large spreadsheets for raw high-frequency acceleration. |

## CSV and TXT files

The application attempts to identify:

- timestamp or separate date/time columns;
- activity;
- light;
- temperature;
- wear/non-wear or mask indicators.

Enable manual mapping when the suggestions are incorrect. Always confirm the resulting preview before analysis.

A generic CSV containing X/Y/Z values should not be treated as calibrated acceleration unless the units, sampling frequency, timestamp alignment, and calibration are known.

## Localized Actiware/RPX exports

English, French, and German epoch exports are supported. The importer can handle common UTF-8 and Windows-1252 encodings, metadata rows before the epoch table, decimal-comma values, and white/red/green/blue light channels when present.

A valid Actiware file without light remains usable for activity analysis.

## NHANES PAXHR_H

`PAXHR_H` is a cohort-level hourly summary file, not one continuous actigraphy recording. Before using it:

1. select one participant (`SEQN`);
2. obtain the starting day/time information needed to construct the sequence;
3. create and document a participant-relative hourly time index;
4. map `PAXMTSH` as activity; and
5. document that the signal is an hourly MIMS summary rather than raw acceleration or device counts.

Do not analyse all participants as one time series.

## Missing data and non-wear

Once an activity series is available, all formats use the same downstream rules:

- missing timestamps and non-finite values remain missing;
- recorded zeros remain valid recorded values;
- non-wear is applied only when an indicator is available and enabled;
- manual masks remain file-specific;
- valid-window and sleep-window coverage rules are applied consistently.

## Light data

Light availability is determined from the signals inside the file. When no usable light is found, the light preview and light metrics are skipped while activity analysis continues.

Confirm the channel and units before setting light thresholds. Supported files may expose lux, log-transformed light, white light, or RGB channels.

## Large recordings

Large raw files can take longer to upload, preview, and analyse. Keep the browser page open during processing and avoid starting multiple large runs at the same time. When a large file repeatedly fails, record the file format, file size, workflow step, request ID, and exact error before submitting feedback.
