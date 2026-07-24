# Application architecture

## Frontend

The frontend uses React and Vite. The current interface is a ten-page workflow. After at least one actigraphy file is imported, pages 2–9 are available through the left navigation; page 10 unlocks after a successful result run.

| Module | Responsibility |
|---|---|
| `pages/Dashboard.jsx` | Ten-page workflow state, direct sidebar navigation, uploads, API requests, progress polling, result orchestration, and export unlocking |
| `components/WorkflowSidebar.jsx` | Clickable workflow navigation and lock state |
| `components/FileSelectionPanel.jsx` | Page 1 actigraphy-file import and analysis mode |
| `components/PreprocessingPanel.jsx` | Page 2 valid-day hours, consecutive-day requirement, sleep-window coverage, and non-wear policy |
| `components/ActivityMappingPanel.jsx` | Page 3 activity-basis selection: recommended/automatic, processed acceleration, MAD, or ENMO |
| `components/PreviewPanel.jsx` | Page 4 activity preview and page 7 standard light preview |
| `components/SupportFilesStep.jsx` | Page 5 start/stop and masking inputs; page 6 sleep-diary and custom sleep-window inputs |
| `components/MetricsPanel.jsx` | Page 6 sleep-wake algorithm configuration and page 8 metric/family configuration through separate render modes |
| `components/OtherSensorsPanel.jsx` | Page 7 light preview/analysis and clearly labelled future temperature/other-sensor attachments with file metadata retained in the analysis configuration |
| `components/LightRGBPanel.jsx` | Multichannel/RGB light preview |
| `components/LightMetricsPanel.jsx` | Light metric selection and settings |
| `components/ResultsPanel.jsx` | Page 9 result generation, live progress, result tables/plots, quality summaries, and diagnostics |
| `components/ExportPanel.jsx` | Page 10 CSV/JSON and other configured output downloads |
| `components/DiagnosticPanel.jsx` | Per-stage diagnostic presentation and downloads |
| `components/DocumentationPanel.jsx` | Full-content in-app documentation search and GitHub documentation links |
| `services/backgroundJobClient.js` | Background submission, affinity-aware polling, and result handoff |
| `config/*.json` | Workflow, metric, algorithm, family, preview, shared-parameter, and export registries |

## Workflow and unlock rules

```text
1 Import Actigraphy Files
  ↓ file selected
2 Pre-processing ─────────────┐
3 Estimate Activity Metric    │
4 Activity Preview            │ directly clickable from the sidebar
5 Cleaning and Masking        │ after file import
6 Sleep-Wake Classification   │
7 Other Sensors               │
8 Analysis Setup              │
9 Generate Results ───────────┘
  ↓ successful run
10 Export Outputs
```

Direct navigation changes presentation order only. The backend still receives one resolved analysis payload containing preprocessing, mapping, intervals, sleep-window, algorithm, metric, and light settings. Page-level validation prevents an invalid setup from being submitted.

## Backend

The backend uses FastAPI/Uvicorn.

| Module | Responsibility |
|---|---|
| `backend/app.py` | API endpoints, upload handling, orchestration, JSON errors, feature flags |
| `backend/io_helpers.py` | Reader inference and native file loading |
| `backend/geneactiv_bin.py` | Streaming GENEActiv decoding and Raw-like adapter |
| `backend/gt3x_loader.py` | Separate bounded GT3X acceleration and type-`0x05` lux readers |
| `backend/accelerometer_loader.py` | Oxford converter/time-series support |
| `backend/activity_mapping.py` | Mapping normalization, resolution, and provenance metadata |
| `backend/preprocessing.py` | Start/stop, masking, diary, and custom interval handling |
| `backend/data_quality.py` | Common gaps, non-wear, analyzable-time, valid-day, consecutive-day, and sleep-window coverage processing |
| `backend/analysis.py` | Metrics, sleep scoring/windows, light analysis, and previews |
| `backend/qc.py` | Non-fatal quality control |
| `backend/diagnostics.py` | Stage instrumentation, memory/timing, exceptions, and JSON safety |
| `backend/progress.py` | Request-scoped live progress |
| `backend/job_manager.py` | Bounded background executor and persistent job/result state |

## Analysis data flow

```text
Browser actigraphy upload
  → per-job input file
  → HTTP 202 with job ID
  → bounded background worker
  → reader detection and native/raw or mapped-tabular loading
  → localized text decoding and semantic RPX header detection when applicable
  → activity-basis resolution
  → timestamp/data validation
  → start/stop and manual masks
  → common gap/non-wear/analyzable-time processing
  → valid-day and longest-consecutive-run calculation
  → diary/custom/AoT sleep-window resolution
  → sleep-window coverage filtering
  → selected sleep scoring and metrics
  → selected embedded/separate light metrics
  → non-fatal quality control
  → JSON-safe stored result
  → job/result polling
  → page 9 results and diagnostics
  → page 10 exports
  → temporary-file cleanup
```

## Registry-driven configuration

The registries define user-facing labels, defaults, availability, and analysis metadata independently from the components. When adding a metric or algorithm, update the registry, backend implementation, documentation, tests, and export handling together. Workflow titles and descriptions come from `config/appConfig.json`.

## Documentation search architecture

`DocumentationPanel.jsx` indexes more than topic names. Its search corpus includes:

- section labels and full explanatory text;
- all workflow titles and descriptions;
- supported-format and activity-option content;
- complete algorithm, metric, and analysis-family registry content;
- diagnostics, limitations, deployment, and developer guidance.

The panel always renders a GitHub documentation link. `VITE_GITHUB_DOCS_URL` can point to an exact docs branch/path; otherwise the link falls back to `${VITE_GITHUB_REPOSITORY_URL}/tree/main/src/docs`, and then to the project default repository.

## API endpoints

| Method and endpoint | Purpose |
|---|---|
| `GET /api/version` | Build metadata and feature flags |
| `GET /api/progress/{request_id}` | Live analysis progress |
| `GET /api/jobs/{job_id}` | Background preview/analysis status and completed result |
| `POST /api/jobs/preview/basic` | Start an activity-preview job; returns HTTP 202 |
| `POST /api/jobs/light/preview` | Start a standard light-preview job; also returns channels and an initial multichannel sample |
| `POST /api/jobs/light/rgb-preview` | Start a resampled multichannel/RGB light-preview job |
| `POST /api/jobs/light/channels` | Discover light channels through the background queue |
| `POST /api/jobs/light/analyze` | Inspect once and run all selected light metrics in one background job |
| `POST /api/jobs/analyze/basic` | Start a main-analysis job; returns HTTP 202 |
| `POST /api/tabular/columns` | Inspect CSV/text/spreadsheet columns, encoding, suggested mapping, and format-specific guidance |
| `POST /api/preview/basic` | Synchronous activity-preview compatibility route |
| `POST /api/analyze/basic` | Synchronous main-analysis compatibility route |
| `POST /api/feedback` | Feedback persistence |
| Converter/light endpoints | Format-specific conversion, preview, and light functions defined in `backend/app.py` |

## Error boundaries

- Metric calls are isolated so one failure does not erase unrelated results.
- Quality control is non-fatal.
- Missingness/non-wear/validity processing is format-independent and runs before metrics.
- Activity and sleep calculations share the final epoch-validity mask.
- NumPy/Pandas outputs and non-finite values are converted to strict JSON-safe types.
- A global exception handler returns structured JSON for ordinary unhandled Python errors.
- Operating-system kills, gateway rejection, and proxy timeouts remain outside the Python error boundary.
- Background execution removes decoding and analysis from the ingress request, but the initial browser upload must still finish within the platform upload/request limit.
- GT3X activity and light capabilities use separate bounded readers. Absence of light is a successful skip and does not affect activity processing.
