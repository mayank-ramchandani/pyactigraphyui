# Methods and reproducibility

The application is designed to keep the important processing choices with each result so that analyses can be reviewed and repeated consistently.

## Computational foundation

The application uses pyActigraphy for native readers and downstream actigraphy methods, including non-parametric rhythm metrics, Crespo_AoT and Roenneberg_AoT procedures, and Cosinor modelling. Raw accelerometer files are first reduced to the selected epoch-level activity measure and then supplied to the corresponding analysis methods.

References:

- [pyActigraphy documentation](https://ghammad.github.io/pyActigraphy/)
- [pyActigraphy source code](https://github.com/ghammad/pyActigraphy)
- [pyActigraphy package paper](https://doi.org/10.1371/journal.pcbi.1009514)

## Processing sequence

For each file, the analysis generally follows this order:

1. identify the file format and available signals;
2. construct or select the epoch-level activity measure;
3. preserve timestamp gaps and missing values;
4. apply start/stop limits;
5. apply detected or mapped non-wear and manual masks;
6. calculate quality-window validity;
7. create or apply sleep windows and check their coverage;
8. run the selected algorithms and metrics;
9. produce quality-control messages, results, plots, and exports.

Missing and excluded epochs remain unavailable rather than being replaced with zero activity.

## Information retained with results

Results and exports can retain:

- source filename and file ID;
- detected reader or file format;
- requested and resolved activity measure;
- source column or raw-processing method;
- units and epoch duration;
- start/stop intervals;
- non-wear and masks;
- quality-window basis and thresholds;
- valid-window counts and longest consecutive run;
- sleep-window source, coverage, and exclusions;
- selected algorithms, metrics, families, and parameters;
- warnings and unavailable-result explanations;
- application version and build information.

## Reproducible analysis checklist

1. Confirm the reader, date range, epoch duration, and resolved activity measure.
2. Review gaps, non-wear, masks, valid-window decisions, and sleep-window coverage.
3. Save the selected families, metrics, algorithms, thresholds, and parameters.
4. Retain quality-control messages and unavailable-result explanations.
5. Keep the exported configuration and application version with the result tables.
6. Apply the same stored configuration when processing additional files intended for the same analysis.

## Interpretation

Values labelled recommended are starting points rather than universal standards. Users remain responsible for choosing methods appropriate to the device, population, protocol, and research question, and for reporting exclusions and sensitivity analyses accurately.

## Data handling and feedback

Uploaded recording and support files are used temporarily to complete the requested operation and are deleted after processing. Download any result files that need to be retained.

Feedback requires a contact email and may include non-raw technical context such as filenames, file sizes, selected settings, processing stages, request IDs, errors, and summary results. Feedback and its attached context are retained for 30 days and then automatically deleted. Do not include participant identifiers or raw measurements in filenames or feedback text.
