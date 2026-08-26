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
