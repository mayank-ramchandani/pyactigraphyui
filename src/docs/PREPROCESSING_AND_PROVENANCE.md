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
2. optionally apply raw X/Y/Z filtering, magnitude, and gravity normalization (Step 2);
3. construct or select the epoch-level activity measure;
4. preserve timestamp gaps and missing values;
5. apply start/stop limits;
6. apply detected or mapped non-wear and manual masks;
7. calculate quality-window validity;
8. create or apply sleep windows and check their coverage;
9. run the selected algorithms and metrics;
10. produce quality-control messages, results, plots, and exports.

Missing and excluded epochs remain unavailable rather than being replaced with zero activity.

### Signal processing versus actigraphy preprocessing

ActiLab records these as two separate layers:

1. **Activity signal generation:** calibrated raw X/Y/Z → metric-specific vector-magnitude/gravity handling → epoch-level ENMO, MAD, PIM, ZCM, TAT, or processed acceleration.
2. **Actigraphy preprocessing:** epoch series → timestamp regularization → start/stop limits → non-wear/manual masks → valid-window rules → rhythm and sleep analyses.

By default (with the new Step 2 optional controls disabled), no universal band-pass filter is applied before every raw-derived metric. ENMO, MAD, PIM, ZCM, and TAT use their documented metric-specific unfiltered inputs; the processed-acceleration option retains its own named processing path. This separation follows the reproducibility concern described by [Maczák et al. (2021)](https://doi.org/10.1371/journal.pone.0261718): preprocessing order and metric definition are part of the result, not interchangeable implementation details.

### Configurable raw acceleration pipeline (Step 2)

This optional mode is **off by default**, preserving previous analyses. It is currently implemented in the native .gt3x and GENEActiv .bin streaming loaders. It cannot run on already-aggregated CSV, counts/AGD/AWD, converted CWA or Oxford time-series uploads; native raw X/Y/Z samples are required. **Step 2 disables its custom-processing checkbox** until at least one eligible native file is uploaded. For multiple recordings (including joined participants), **every actigraphy file must be eligible** or the option remains unavailable, with an explanation in the adjacent **i** bubble. Replacing raw recordings with an unsupported type automatically switches off previously enabled custom settings; regular activity analyses remain available. File extension is only a first check: the server verifies actual GENEActiv `.bin` content and rejects unsupported inputs instead of ignoring custom settings.

With custom mode enabled, calibrated raw X/Y/Z samples (g) are converted into a scalar sample-level signal in this order:

1. Optional Butterworth **low-pass**, **high-pass**, or **band-pass** filter, order 1–8. Specify corner frequencies in hertz. Each cutoff must fall below the individual source's Nyquist frequency (native sampling frequency / 2). Choose either **per-axis filtering before magnitude** or **filtering the magnitude after taking its norm**. The former produces a nonnegative vector norm; the latter may remain signed after high-/band-pass filtering.
2. Acceleration magnitude is `sqrt(X² + Y² + Z²)`. Without filtering, this is always a nonnegative raw norm that includes gravity.
3. Optional normalization: **none**; **absolute amplitude** `|signal|`; **subtract gravity reference** `signal - 1 g` (signed); **absolute gravity deviation** `|signal - 1 g|`; or **positive gravity deviation** `max(signal - 1 g, 0)` (ENMO-style). Gravity reference is adjustable (normally 1 g) but only meaningful when the static gravitational component remains in the signal. Therefore, subtract-one variants cannot be combined with high-pass or band-pass filtering. The user can select mg, g, or m/s² as the **final** epoch output acceleration unit.
4. The chosen Step 3 activity metric reduces these transformed samples to epochs: acceleration/ENMO use epoch means (signed if chosen), MAD uses within-epoch mean absolute deviation, PIM integrates absolute signal amplitude using sample time, ZCM counts level crossings of absolute signal amplitude above an mg threshold, and TAT accumulates duration above that threshold. These customized activity variants may **not be comparable to validated conventional ENMO, MAD, PIM, ZCM or TAT**, even when the same metric name is selected.

A memory-safe **causal forward-only SOS Butterworth** filter carries state across contiguous blocks and resets at timestamp gaps or sampling-rate changes. It is **not** zero-phase / forward-backward filtering; any transient/phase effects must be considered. ActiLab neither fills missing raw intervals with zeros nor applies filters across separate source files. Users should avoid assuming that sleep scoring thresholds calibrated to manufacturer counts also apply to arbitrarily transformed acceleration.

The user interface deliberately uses descriptive processing names rather than paper-specific identifiers. Maczák et al. (2021) call unfiltered magnitude **UFM**, absolute gravity-normalized unfiltered magnitude **UFNM**, filtered axes **FXYZ**, filtering axes then taking magnitude **FMpre**, and taking magnitude then filtering **FMpost**. Their illustrative third-order Butterworth 0.25–2.5 Hz band-pass can be selected as a starting point, but ActiLab's causal streaming implementation need not reproduce the exact phase response used in every published comparison. Consult [Maczák et al. (2021)](https://doi.org/10.1371/journal.pone.0261718) for the full methodological comparisons.

When custom mode is enabled, **the same selected Step 3 activity measure and Step 2 raw-signal configuration are used in Initial QC, the Step 4 activity preview, and the final analysis**. The preview does not offer an independent activity basis in custom mode, preventing inadvertent differences between plotted values and analyzed values. Each supported native recording is processed independently from its original raw samples for each request; the plotted trace is the epoch-level processed signal (not a reconstructed raw high-frequency waveform). Masks and recording windows are applied after epoch generation, while rhythm and sleep analyses consume the resulting activity time series. Light and temperature channels, raw X/Y/Z diagnostics, and light-specific analyses remain separate and are not filtered by these controls. Only compatible raw data formats are eligible; errors are returned for unsupported formats or settings. Do not interpret custom-filtered inputs as validated replacements for manufacturer counts in count-dependent sleep algorithms.

The processing configuration and units are retained with the run settings, diagnostics and Methods/provenance output so results can be reproduced. Review the signal and algorithm selection with the research protocol before interpreting downstream outcomes.

### Joined participant recordings

When multiple recordings from the same participant are joined, each source is processed independently before the participant timeline is assembled. If the native accelerometer sampling rates differ, ActiLab does not resample one raw stream to imitate the other. Each recording is converted at its own native rate into the selected activity representation and common analytical epoch, and the epoch-level series are then joined by timestamp.

The join keeps real calendar gaps as missing time, removes exact duplicate boundary timestamps, and records the native sampling rate for every source. Metric-specific safeguards are applied when rates differ: ENMO and processed acceleration proceed with an informational notice; MAD, PIM, and TAT proceed with a warning; ZCM proceeds with a strong warning; source/device activity or ActiGraph counts are rejected unless they have already been externally harmonized/validated. Joined ZCM/TAT also requires one fixed threshold shared by every source. Files with different processed epoch durations, activity bases, or units are not combined.

## Information retained with results

Results and exports can retain:

- source filename and file ID;
- detected reader or file format;
- requested and resolved activity measure;
- source column or raw-processing method;
- raw input signal, gravity handling, filtering status, and operation order;
- ZCM/TAT threshold method and resolved threshold value;
- units and epoch duration;
- native sampling rate for each source in a joined participant recording;
- joined-recording harmonization notices and warnings;
- start/stop intervals;
- non-wear and masks;
- quality-window basis and thresholds;
- valid-window counts and longest consecutive run;
- sleep-window source, coverage, and exclusions;
- selected algorithms, metrics, families, and parameters;
- warnings and unavailable-result explanations;
- application version and build information.

The Results page includes a copyable Methods paragraph assembled from these fields. It is a reporting aid and should be reviewed alongside the study protocol before publication.

## Exporting the exact preprocessed activity series

Step 9 (Generate Results) and Step 10 (Export Outputs) provide a **Download Preprocessed Activity Data** button for each completed analysis. The archive contains `preprocessed_activity.csv`, `processing_manifest.json`, and `README.txt`. The download uses the same source recordings and frozen processing configuration as that completed run, recomputing the epoch-level signal in a bounded background job rather than adding a large time series to the normal result JSON. It is available only while the original uploaded files are still accessible in the current browser session.

The CSV contains a timestamp, pre-QC processed activity, and activity eligible for downstream analysis, all in the exact chosen activity units. It also records missing/gap epochs, non-wear detection, whether non-wear was excluded, manual masks, invalid 24-hour quality windows, selected-interval membership, analysis inclusion, and an exclusion reason. **Missing and excluded data are blank, never forced to zero.**

The manifest records filter type/order/cutoffs, operation order, magnitude normalization and units when custom processing is used, as well as activity metric, epoch duration, mask and QC settings, analysis intervals, joined-file provenance, and methods text. These are the settings needed to reproduce the activity input from the source recordings. The CSV is *not* the native high-frequency waveform, nor does it encode sleep-scoring predictions or aggregate rhythm/sleep metrics. For combined whole-recording-and-interval analyses, the activity-used column represents the whole-file branch and a dedicated flag identifies selected-interval rows. Exports are temporary; researchers must retain downloaded files for long-term reproducibility.

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

Uploaded recording files, support files, job data, and temporary processing data are automatically deleted no later than 30 days after upload. Temporary files may be deleted sooner after processing. Download any result files that need to be retained.

Feedback requires a contact email and may include non-raw technical context such as filenames, file sizes, selected settings, processing stages, request IDs, errors, and summary results. Feedback and its attached context are retained for a maximum of 30 days and then automatically deleted. A minimal notification email may contain the submitter email, filename, workflow step, category, and feedback ID, without the feedback message or detailed diagnostic context. Do not include participant identifiers or raw measurements in filenames or feedback text.
