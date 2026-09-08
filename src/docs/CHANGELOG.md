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

# What’s new

This page summarizes changes that affect users of the application. Internal deployment and implementation details are documented separately from the public user guide.

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
