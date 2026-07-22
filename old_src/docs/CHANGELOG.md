# Change log

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
