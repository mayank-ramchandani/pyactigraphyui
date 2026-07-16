# RA, sleep-window, and progress changes

## Corrected direct `.bin` RA

- Replaced full-record rolling L5/M10 calculations with a cyclic average-daily-profile calculation equivalent to pyActigraphy.
- Added M10, L5, start times, threshold, binarization, and `RA == 1` boundary diagnostics.
- Added a QC warning for RA exactly equal to 1.
- Added a visible RA calculation summary to the diagnostic panel.

## Corrected direct `.bin` Crespo/Roenneberg integration

- Added the `raw_data` interface required by pyActigraphy's Crespo implementation.
- Added `frequency` and `resampled_data` interfaces used by pyActigraphy scoring.
- Delegated `Crespo`, `Crespo_AoT`, `Roenneberg`, and `Roenneberg_AoT` to pyActigraphy 1.2.2.
- Normalized Crespo's 0=rest/1=activity output to the application's 1=sleep/rest convention for downstream sleep metrics.
- Kept the requested no-fallback behavior for sleep-window detection.
- Added a visible sleep-window method/count/notes summary to diagnostics.

## Live stage progress

- Added request-scoped backend progress tracking and `GET /api/progress/{request_id}`.
- Changed the CPU-heavy analysis route to a FastAPI synchronous route so it runs in the threadpool and progress polling remains responsive.
- Added real upload progress using `XMLHttpRequest`.
- Added stage number, stage total, percentage, current-stage text, decoded page count, and decoded sample count.
- Added byte-level progress updates during streamed GENEActiv decoding.
- A full all-metric analysis resolves to 26 stages.

## Validation performed

- Python syntax compilation for all backend modules.
- Frontend JSX bundling for Dashboard and ResultsPanel/DiagnosticPanel.
- RA tests showing binary RA=1 only when L5=0, while continuous RA remains below 1 on the same synthetic recording.
- Direct integration tests against pyActigraphy 1.2.2 for Crespo_AoT and Roenneberg_AoT.
- End-to-end synthetic window conversion showing both methods produce overnight rest windows.
- Nested-stage progress regression test and 26-stage count test.

The exact user recording was not available in the execution environment, so it must be rerun after deployment to inspect its M10/L5 components and actual AoT outputs.
