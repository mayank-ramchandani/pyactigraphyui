## 2026-10-16 — Raw preprocessing file-type eligibility

- Custom raw acceleration preprocessing in Step 2 is only selectable when every uploaded actigraphy recording is a native `.gt3x` or `.bin` candidate (GENEActiv BIN content is verified by the backend).
- Other formats show a disabled toggle and an accessible **i** information bubble explaining why original high-frequency X/Y/Z samples are required. Mixed eligible/unsupported uploads remain unavailable; standard analysis is unaffected.
- Replacing recordings with unsupported file types automatically switches off previously enabled custom preprocessing, avoiding stale analysis/preview settings. Added eligibility regression checks and updated user documentation.

## 2026-10-15 — Preprocessed activity export

- Added **Download Preprocessed Activity Data** on Generate Results (Step 9) and Export Outputs (Step 10) for each successfully analyzed recording or joined participant.
- The ZIP includes a complete epoch-level activity CSV (before and after quality-control/selected-interval exclusions), mask and non-wear flags, timestamps and actual activity units, plus a machine-readable settings/provenance JSON and short README.
- A bounded background export reprocesses the source uploads using the exact settings captured when results were generated; large raw streams are not embedded in the main JSON analysis response.
- Updated documentation on export scope, eligible/missing epochs, temporary availability, and research reproducibility.

## 2026-10-15 — Workflow and feedback fixes

- Renamed workflow Step 2 and its panel to **Preprocessing/Initial QC**.
- Fixed the feedback modal on smaller/shorter screens: constrained the scrollable form height to the viewport and kept Submit/Cancel actions visible while scrolling.
- When advanced raw-signal processing is enabled, the activity preview now uses the **same Step 3 activity measure** as the analysis instead of its independent preview selection; the preview shows the processed signal's label and actual units.
- Raw preprocessing changes invalidate cached previews and result displays; raw X/Y/Z diagnostics and light/temperature processing remain unaffected. Results display the actual custom-signal labels and units.

## 2026-10-15 — Optional raw acceleration preprocessing

- Added a Step 2 **Raw acceleration signal processing** panel (disabled by default) with explanatory hover/focus **i** bubbles.
- Added customizable Butterworth low-, high- and band-pass filtering (order 1–8 and cutoff frequencies), per-axis-before-magnitude or magnitude-before-filter operation order, adjustable 1 g reference, normalization and output units (mg, g, m/s²).
- Added scientifically descriptive presets including unfiltered magnitude, positive/absolute gravity deviation, and an illustrative third-order 0.25–2.5 Hz band-pass; paper-specific abbreviations appear only in supporting documentation.
- Connected the settings to the native GT3X and GENEActiv BIN bounded-memory decoders, including continuity-aware filter state, per-file Nyquist validation, metadata, Methods text and explicit raw-data compatibility errors.
- Preserved previous metric defaults with the custom processing switch off, added tests, and documented the limitations of applying altered activity scales to existing sleep algorithms.

## 2026-10-07 — Metric-specific raw processing and provenance

- Added TAT (seconds above threshold per epoch) for raw GENEActiv/GT3X and compatible preprocessed columns.
- Replaced the former filtered/dead-band PIM/ZCM path with documented metric-specific unfiltered `|VM - 1 g|` processing.
- Added adaptive recording-SD and fixed-mg threshold modes for ZCM/TAT; adaptive processing uses two bounded-memory passes.
- Required one fixed ZCM/TAT threshold for joined participant files so source definitions remain consistent.
- Added complete activity-processing provenance and copyable Methods text to analysis results.
- Added the preprocessing rationale and citation to Maczák et al. (2021), while retaining the paper's limitations.

## 2026-09-11 — Workflow order and labels

- Renamed Step 2 from **Pre-processing** to **Initial QC**.
- Moved **Analysis Set-up** to Step 7 and **Other Sensors** to Step 8.
- Simplified the Analysis settings wording by removing “recommended” labels and shortening the consecutive-valid-window label.

## 2026-09-10 — Workflow sidebar readability

- Increased the workflow sidebar width slightly on desktop so long step names and descriptions wrap less aggressively.
- Increased active-step description font size, contrast, line height, spacing, and active-row padding for easier reading.
- Increased step-title weight/size and strengthened the active-step background.
- Added the full step description as a hover tooltip for every workflow step without permanently increasing sidebar height.

# What’s new

This page summarizes changes that affect users of the application. Internal deployment and implementation details are documented separately from the public user guide.

## 2026-09-10

- Fixed theme inconsistency by making ActiLab use a consistent light colour scheme instead of inheriting the operating system/browser dark-mode preference.
- Moved the workflow sidebar to the top of the page and centred the ActiLab logo/header within the main workflow content area.
- Moved accepted-file and multiple-file guidance into a hover tooltip on the actigraphy upload box.
- Moved validity thresholds, 24-hour period definition, and detected/mapped non-wear handling to **Step 8: Analysis Set-up** under **Analysis settings**.
- Removed the duplicate detected non-wear toggle from Cleaning and Masking.
- Removed the logo image's light canvas so the ActiLab mark blends cleanly with its surrounding page background.
- Standardized paired choices (including Analysis type, participant file handling, valid 24-hour period definition, and Analysis scope) as balanced two-column controls that collapse cleanly on small screens.
- Reworked the workflow sidebar into a compact sticky navigator with a Step X of 10 indicator, progress bar, active-step highlighting, and automatic active-row visibility. Moving between workflow steps now returns the new step content to its top.

## 2026-09-08 — Joined participant fixes and sampling-rate harmonization

- Joined participant mode now distinguishes native/raw accelerometer sampling rate from the common analytical epoch used after processing. Raw 30-Hz and 100-Hz samples are never directly concatenated.
- Each source recording is processed independently at its native rate into the same epoch-level activity representation before timestamp joining; native rates are retained in provenance and shown in QC/preview/results.
- ENMO and processed acceleration are allowed across differing native rates with an informational notice. MAD and PIM are allowed with a warning. ZCM is allowed with a strong warning because zero-crossing counts are sampling-frequency sensitive. Source/device activity and ActiGraph counts are blocked across differing native rates unless externally harmonized/validated.
- Fixed joined pyActigraphy recordings so the combined activity/light timeline is rebuilt as a new `BaseRaw` instead of attempting to write to read-only `data`/`light` properties. This prevents joined workflows from silently continuing to expose only the first source file.
- Joined preview resampling now processes each source recording separately before combining preview points, avoiding millions of empty resample bins across long calendar gaps.
- Activity and light previews now preserve a visible gap break and guarantee that each source segment is represented in the sampled plot.
- Added joined-source coverage tables showing each source file's start/stop range, epoch count, raw sample rate (where available), and resolved activity basis.
- Added validation that all joined files resolve to the same activity basis/units before they are combined.
- Updated the user documentation and in-app Documentation panel to explain native sampling rate versus analytical epoch, metric-specific join safeguards, blocking conditions, and provenance for mixed-frequency recordings.


## 2026-08-26 — Participant-level file joining and feedback alerts

- Expanded the opt-in same-participant join into an end-to-end workflow mode selected from Step 1 (and reviewable in Results).
- Joined mode now applies to initial QC, activity preview, support-interval selection, preprocessing, sleep-wake processing, final activity/sleep metrics, light preview, RGB/multichannel light inspection, and light metrics.
- Embedded light is joined across actigraphy files; when separate light files are supplied, those files are joined as the participant light timeline. Files without light contribute missing intervals rather than zero exposure.
- Joined analysis validates compatible sampling intervals, preserves real timestamp gaps, and removes duplicate boundary timestamps before metric calculation.
- Added optional minimal feedback notification emails to the designated project contact; notifications contain only feedback ID, submitter email, filename, workflow step, and category.
- Updated privacy wording so uploaded/job data and feedback are described as automatically deleted no later than 30 days, with temporary files potentially deleted sooner.

## 2026-08-05 — User-focused documentation

- Reorganized the in-app guide around user tasks and decisions.
- Removed deployment, API, storage-path, admin-token, and maintainer instructions from public documentation.
- Added a clearer “Start here” section, recommended first-run approach, and final review checklist.
- Rewrote troubleshooting guidance as practical user actions.
- Simplified file-format, preprocessing, activity-measure, metric, reproducibility, and data-handling explanations.
- Moved internal architecture, deployment, maintenance, and implementation notes outside the public `docs` directory.

## 2026-07-30 — Feedback contact and retention

- Made a contact email required in the feedback form so the team can follow up.
- Added a 30-day retention period for feedback, contact email, and attached technical context.
- Updated the Terms of Use to explain the retention period and de-identification expectations.

## 2026-07-27 — Data-quality windows and preview improvements

- Added initial per-file coverage information on the Pre-processing page.
- Added a choice between calendar-day and recording-aligned 24-hour quality windows.
- Improved file search and duplicate-filename identification in Activity Preview.
- Changed recoverable warning styling to yellow while retaining red for true failures and invalid quality windows.

## 2026-07-24 — Additional activity measures and analysis families

- Added PIM and ZCM activity measures.
- Restored family-level and metric-level analysis selection.
- Added the pyActigraphy Cosinor family.
- Improved localized Actiware/RPX CSV support and manual CSV mapping.
- Added preparation guidance for NHANES PAXHR_H files.

## 2026-07-23 — Ten-step workflow

- Reorganized the application into ten workflow pages from upload through export.
- Made Steps 2–9 directly accessible after file upload.
- Separated preprocessing, activity selection, preview, cleaning, sleep, sensors, metric setup, results, and export.
- Added configurable valid-window, consecutive-window, and sleep-window coverage criteria.
- Added content-aware light handling so recordings without light remain usable for activity analysis.

## 2026-07-22 — Missingness and quality control

- Preserved missing and excluded epochs as unavailable rather than zero activity.
- Added daily quality information for recorded time, gaps, non-wear, masks, and analyzable time.
- Added sleep-window coverage checks and valid 24-hour pairs for SRI.
- Improved background processing and preview reliability for large recordings.

## 2026-07-16 — Documentation and processing transparency

- Added the searchable in-app Documentation page.
- Added file-aware recommended activity processing.
- Corrected relative-amplitude calculation for direct GENEActiv processing.
- Added per-file status, warnings, and downloadable diagnostic information.
