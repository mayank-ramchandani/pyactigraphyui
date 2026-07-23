# Application architecture

## Frontend

The frontend uses React and Vite.

Important modules:

| Module | Responsibility |
|---|---|
| `pages/Dashboard.jsx` | Workflow state, uploads, API requests, progress polling, result orchestration |
| `services/backgroundJobClient.js` | Background light-job submission, affinity-aware polling, and result handoff |
| `components/FileSelectionPanel.jsx` | File categories and upload selection |
| `components/PreviewPanel.jsx` | Activity and light preview controls |
| `components/ActivityMappingPanel.jsx` | Independent preview/analysis mapping selector |
| `components/MetricsPanel.jsx` | Metric families, algorithms, parameters, and analysis intervals |
| `components/ResultsPanel.jsx` | Results, progress, QC, and diagnostics |
| `components/DiagnosticPanel.jsx` | Per-stage diagnostic presentation and downloads |
| `components/DocumentationPanel.jsx` | Searchable in-app documentation |
| `config/*.json` | Workflow, metric, algorithm, family, preview, parameter, and export registries |

## Backend

The backend uses FastAPI/Uvicorn.

| Module | Responsibility |
|---|---|
| `backend/app.py` | API endpoints, upload handling, orchestration, JSON errors, feature flags |
| `backend/io_helpers.py` | Reader inference and native file loading |
| `backend/geneactiv_bin.py` | Streaming GENEActiv decoding and Raw-like adapter |
| `backend/gt3x_loader.py` | Separate bounded GT3X acceleration and type-`0x05` lux readers |
| `backend/accelerometer_loader.py` | Oxford converter/time-series support |
| `backend/activity_mapping.py` | Mapping normalization, resolution, and metadata |
| `backend/preprocessing.py` | Intervals, masks, and support files |
| `backend/analysis.py` | Metrics, sleep scoring/windows, light analysis, and previews |
| `backend/qc.py` | Non-fatal quality control |
| `backend/data_quality.py` | Common gaps, non-wear, valid-day, and daily-QC processing |
| `backend/diagnostics.py` | Stage instrumentation, memory/timing, exceptions, JSON safety |
| `backend/progress.py` | Request-scoped live progress |
| `backend/job_manager.py` | Bounded background executor and persistent job/result state |

## Data flow

```text
Browser upload
  → per-job input file
  → HTTP 202 with job ID
  → bounded background worker
  → reader detection
  → native reader or raw acceleration adapter
  → activity mapping resolution
  → timestamp/data validation
  → start/stop and masking
  → common gap/non-wear/valid-day preprocessing
  → sleep diary or AoT window detection
  → selected metrics
  → quality control
  → stored JSON-safe result
  → job/result polling
  → results and diagnostic downloads
  → temporary-file cleanup
```

## Registry-driven configuration

The registries define user-facing labels and analysis metadata independently from the components. When adding a metric or algorithm, update the registry, backend implementation, documentation, tests, and export handling together.

## API endpoints

| Method and endpoint | Purpose |
|---|---|
| `GET /api/version` | Build metadata and feature flags |
| `GET /api/progress/{request_id}` | Live analysis progress |
| `GET /api/jobs/{job_id}` | Background preview/analysis status and completed result |
| `POST /api/jobs/preview/basic` | Start an activity-preview job; returns HTTP 202 |
| `POST /api/jobs/light/preview` | Start a standard light-preview job; also returns channels and the initial multichannel sample |
| `POST /api/jobs/light/rgb-preview` | Start a resampled multichannel/RGB light-preview job |
| `POST /api/jobs/light/channels` | Discover light channels through the background queue |
| `POST /api/jobs/light/analyze` | Inspect once and run all selected light metrics in one background job |
| `POST /api/jobs/analyze/basic` | Start a main-analysis job; returns HTTP 202 |
| `POST /api/preview/basic` | Activity preview |
| `POST /api/analyze/basic` | Main analysis |
| `POST /api/feedback` | Feedback persistence |
| Converter/light endpoints | Format-specific conversion, light previews, and light metrics as defined in `backend/app.py` |

## Error boundaries

- Metric calls are isolated so one failure does not erase unrelated results.
- QC is non-fatal.
- Missingness/non-wear QC is format-independent and runs before metrics.
- Activity and sleep calculations share the final epoch-validity mask.
- NumPy/Pandas outputs are converted to JSON-safe types before response construction.
- A global exception handler returns structured JSON for ordinary unhandled Python errors.
- Operating-system kills, gateway rejection, and proxy timeouts remain outside the Python error boundary.
- Background execution removes decoding and analysis from the ingress request, but the initial browser upload must still finish within the platform's upload/request limit.
- GT3X activity and light capabilities use separate bounded readers. Activity
  decodes calibrated X/Y/Z; light scans only `log.bin` event headers/payloads
  for record type `0x05`. Absence of light is a successful skip, not a reader
  failure, and does not affect GT3X activity processing.
