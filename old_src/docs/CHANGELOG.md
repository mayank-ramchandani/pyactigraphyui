# Change log

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
