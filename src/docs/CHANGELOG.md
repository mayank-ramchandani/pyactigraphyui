# Change log

## 2026-07-23 — Ten-page workflow and full-content documentation

- Reorganized the interface into the requested ten-page process from actigraphy import through export.
- Made sidebar pages 2–9 directly clickable after file import; Export unlocks only after successful result generation.
- Moved valid-day, consecutive-day, sleep-window coverage, and non-wear choices to the Pre-processing page.
- Limited the activity-estimation page to four options: recommended/automatic, processed acceleration, MAD, and ENMO.
- Separated cleaning/masking, sleep-wake classification, other sensors, metric setup, result generation, and export into dedicated pages.
- Added an information explanation for minimum sleep-window coverage.
- Expanded in-app search to index complete narrative, workflow, format, metric, algorithm, family, diagnostic, limitation, and developer content.
- Made the GitHub documentation link persistently visible with an exact `VITE_GITHUB_DOCS_URL` override and repository fallback.
- Updated the in-app guide, GitHub Markdown documentation, environment example, and validation guidance.

## 2026-07-23 — Optional preprocessing validity thresholds

- Kept the project standards active by default: 16 analyzable hours per valid day, two consecutive valid days for multi-day rhythm/SRI metrics, and 80% sleep-window coverage.
- Added an explicit preprocessing opt-in before custom thresholds are applied.
- Changed rhythm/SRI eligibility from total valid-day count to the longest consecutive valid-day run.
- Added the consecutive-day run to results, diagnostics, documentation, and regression tests.

## 2026-07-23 — Content-aware GT3X light processing

- Replaced extension-based GT3X light rejection with complete `log.bin`
  inspection for official type-`0x05` lux records.
- Added bounded-memory lux aggregation with checksum, timestamp, and payload
  validation; real gaps remain missing.
- Exposed GT3X light as `LIGHT` (`log10(lux + 1)`) and `LIGHT_LUX` (lux).
- Added explicit successful no-light responses so activity continues while
  light preview and metrics are skipped.
- Added one background batch job for all selected light metrics, avoiding one
  upload and file scan per metric.
- Made lux thresholds follow the selected channel's raw-lux or log scale.
- Updated the UI, API feature flags, deployment guidance, in-app documentation,
  and regression suite.
- Added five focused tests; the complete 26-test backend suite passes.

## 2026-07-23 — Safe large-file light previews

- Stopped `.gt3x` activity files from being used as implicit light sources.
- Added a clear GT3X-light limitation message while preserving GT3X activity
  preview and analysis.
- Rejected direct GT3X light requests before temporary-file copying or decoding.
- Added background jobs for standard light preview, multichannel/RGB preview,
  and light-channel discovery.
- Returned standard preview, channels, and the initial multichannel sample from
  one raw-file decode to avoid redundant GENEActiv processing.
- Added frontend affinity-aware polling for background light jobs.
- Added four regression tests for early GT3X rejection, supported light-job
  lifecycle, and single-decode preview composition; the complete 21-test
  backend suite passes.

## 2026-07-22 — Missing days, non-wear, and valid-day QC

- Added one format-independent missingness/non-wear stage for GT3X, direct BIN,
  converted BIN/CWA, Oxford time-series, and native pyActigraphy files.
- Kept absent and excluded epochs as missing rather than zero activity.
- Connected **Respect detected non-wear** to backend reader/mapped masks.
- Added configurable defaults of 16 valid hours/day, two consecutive valid
  days for rhythm/SRI eligibility, and 80% sleep-window coverage.
- Added daily QC with recorded, gap, detected-non-wear, manual-mask, and
  analyzable hours.
- Made SRI use valid 24-hour pairs and prevented direct-BIN transitions across
  missing gaps.
- Excluded low-coverage sleep windows and used observed/scored minutes as the
  sleep-efficiency denominator.
- Added ten focused data-quality tests; the complete 17-test suite passes.

## 2026-07-22 — Resilient background-job polling

- Retried transient missing-job responses instead of failing on the first 404.
- Included credentials on cross-origin job requests for Azure session affinity.
- Added replica/revision and job-store-scope diagnostics to job responses.
- Added a targeted error for replica-local or lost background-job state.

## 2026-07-22 — Strict JSON for recording previews

- Converted missing and non-finite preview points to JSON `null` after
  resampling recordings that contain gaps.
- Routed activity previews through the same JSON-safety boundary as analyses.
- Enforced strict JSON when persisting background-job results so `NaN` and
  infinite numeric values cannot reappear during polling.
- Added regression coverage for gapped previews and background results.

## 2026-07-21 — Background jobs for the 240-second ingress limit

- Added HTTP 202 background-job submission and result polling for activity
  preview and main analysis.
- Kept GT3X decoding and selected metrics outside the original upload request.
- Added a one-worker default to protect 2 GiB deployments from concurrent
  large-recording memory multiplication.
- Persisted job status/results under `APP_DATA_DIR` and removed job input files
  after completion.
- Added frontend recovery when ingress closes exactly as a known job ID is
  accepted.

## 2026-07-21 — Bounded-memory GT3X loading

- Replaced whole-file `pygt3x.FileReader.to_pandas()` decoding with low-level
  streamed `log.bin` event processing.
- Reduced calibrated X/Y/Z directly into epoch-level processed `acc`, MAD,
  custom ENMO, or supported 30 Hz ActiGraph-style counts.
- Preserved device-local timestamps and real recording gaps.
- Added checksum, impossible-timestamp, duplicate-event, calibration, buffer,
  and GT3X progress diagnostics.
- Moved CPU-heavy preview/conversion routes into FastAPI's thread pool and
  guaranteed temporary-upload cleanup.
- Added synthetic gap/timezone/MAD regression tests and a full 289 MB GT3X
  benchmark.

## 2026-07-16 — Documentation centre

- Added a searchable in-app Documentation page.
- Added GitHub-ready user, methods, file-format, diagnostics, validation, architecture, deployment, and maintenance documentation.
- Added optional `VITE_GITHUB_REPOSITORY_URL` support.
- Added the `documentation_center` backend feature flag.

## 2026-07-16 — Processed activity basis

- Restored file-aware recommended activity behaviour.
- Count-based files use source/device activity.
- Raw `.bin`, `.cwa`, and `.gt3x` files use processed epoch-level `acc` where supported.
- Kept MAD and custom ENMO as optional mappings.
- Decoupled preview mapping from analysis mapping.
- Added mapping engine, units, filter, and epoch metadata to diagnostics.

## 2026-07-16 — RA, sleep windows, and live progress

- Corrected direct GENEActiv RA to use the cyclic average daily profile.
- Added M10/L5 component diagnostics and RA boundary warnings.
- Added Raw-like interfaces needed by pyActigraphy Crespo and Roenneberg methods.
- Kept the no-fallback-window requirement.
- Added live upload, stage, byte, page, and sample progress.

## 2026-07-16 — Structured diagnostics and response safety

- Added per-file, per-stage timing and memory diagnostics.
- Captured previously suppressed metric exceptions.
- Made QC non-fatal.
- Added JSON-safe conversion for NumPy/Pandas/vector metric outputs.
- Added structured unhandled-error responses and downloadable diagnostic reports.
