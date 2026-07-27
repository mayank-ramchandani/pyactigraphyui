# Implementation update — 2026-07-27

## Implemented requests

1. **Warning severity** — recoverable processing and QC warnings use yellow/amber styling. True request/file failures and invalid quality windows remain red.
2. **Step 4 file search** — uploaded files are displayed as a live searchable list. Duplicate filenames remain separate uploads and are labelled with duplicate position and file size. Stable upload keys prevent one duplicate from replacing another in preview selection.
3. **24-hour validity basis** — calendar-day windows remain the recommended default; recording-aligned 24-hour windows are available as an explicit sensitivity option. The selected basis is sent to the backend and retained in QC/results.
4. **Initial Step 2 QC** — a background endpoint loads each recording and reports initial per-window recorded hours, gaps, detected/mapped non-wear, effective hours, and threshold status before start/stop restrictions and manual masks.
5. **Recommended-setting wording** — preprocessing, results, configuration descriptions, and documentation now describe the default thresholds as recommended and configurable rather than mandatory standards.
6. **Algorithm details** — the heterogeneous Context column was removed. Algorithm-specific context, notes, warnings, and citations appear in the Context / details dialog.
7. **Terms of Use** — a persistent header button and searchable documentation section describe OBI hosting, CFA grant support, transient raw-file processing, de-identification, diagnostics/feedback metadata, scientific responsibility, availability, third-party software, and acceptable use.

## Backend/API changes

- Added `POST /api/qc/initial` and `POST /api/jobs/qc/initial`.
- Added `validDayWindowMode` support with `calendar_day` and `recording_anchored` values.
- Added both window interpretations to the initial-QC payload.
- Added window start/stop, labels, mode, and quality-window counts to final QC.
- Raw job inputs are now removed before terminal completion/failure status is exposed.

## Deployment notes

- Redeploy both frontend and backend together because the Step 2 UI depends on the new QC endpoint and payload.
- No database migration is required.
- The configured job store still controls transient result retention. `ANALYSIS_JOB_TTL_SECONDS` defaults to 21,600 seconds (six hours).
- Feedback and diagnostic metadata are separate from raw uploads and may persist when `APP_DATA_DIR` uses persistent storage; apply an institutional access and retention policy.
- The uploaded archive did not include a frontend `package.json`, so source parsing was checked but a full Vite production build could not be run in this workspace.

## Verification

- Python backend modules compile successfully.
- 26 focused data-quality/background-job tests pass.
- The broader backend suite passes 40 tests; five GT3X streaming tests require the optional deployment dependency `pygt3x`, which is not installed in this workspace.
- Modified JavaScript/JSX files parse successfully, and duplicate-file identity/search behaviour was exercised with a direct utility check.
