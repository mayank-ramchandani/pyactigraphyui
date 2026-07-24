# Documentation maintenance

## Sources of truth

| Subject | Primary source |
|---|---|
| Workflow titles/order | `config/appConfig.json` |
| Workflow composition/unlock rules | `pages/Dashboard.jsx` and `components/WorkflowSidebar.jsx` |
| Metric labels/defaults | `config/metricRegistry.json` |
| Algorithms/defaults | `config/algorithmRegistry.json` |
| Analysis families | `config/analysisFamilyRegistry.json` |
| Shared parameters | `config/sharedParamRegistry.json` |
| Backend feature flags | `backend/app.py` `/api/version` |
| In-app guide and search corpus | `components/DocumentationPanel.jsx` |
| Long-form GitHub documentation | `docs/*.md` and root `README.md` |

The in-app workflow, metric, algorithm, family, and format content is partly registry-driven. Explanatory methods text is maintained manually and must be updated whenever behaviour changes.

## Current navigation contract

The documented public flow contains exactly ten pages:

1. Import Actigraphy Files
2. Pre-processing
3. Estimating Activity Metric / Magnitude of Acceleration
4. Activity Preview
5. Cleaning and Masking
6. Sleep-Wake Classification
7. Other Sensors
8. Analysis Setup
9. Generate Results
10. Export Outputs

After file import, pages 2–9 are directly clickable. Export remains locked until page 9 completes successfully. Any UI change that modifies this contract must update `appConfig.json`, `Dashboard.jsx`, `DocumentationPanel.jsx`, `USER_GUIDE.md`, `README.md`, `ARCHITECTURE.md`, and `CHANGELOG.md` together.

## Full-content search maintenance

The in-app search must match content, not only section/topic names. Keep the search corpus synchronized with:

- narrative documentation text;
- workflow descriptions;
- file formats and sensor capability;
- all four activity options;
- algorithm registry entries;
- metric registry entries;
- analysis-family entries;
- diagnostics, errors, deployment, and limitations.

When adding a new term or concept, verify that searching a phrase from its body text returns the relevant section even when the phrase is not in the section title.

## Documentation checklist for every change

### Workflow or preprocessing change

- update `config/appConfig.json` and relevant panel/component;
- update page validation and direct-navigation behaviour in `Dashboard.jsx`;
- update the in-app narrative/search corpus;
- update `USER_GUIDE.md`, related methods files, architecture, and change log;
- add frontend/backend tests for payload and unlock behaviour.

### New or changed metric

- update the metric registry;
- update backend calculation and JSON serialization;
- update `METRICS_AND_ALGORITHMS.md`;
- add or update validation tests;
- add a change-log entry;
- confirm Results and Documentation tables/search.

### New or changed file/sensor format

- update reader inference and loader;
- document signal, units, mapping, page location, and limitations in `FILE_FORMATS.md`;
- update the in-app file/sensor content;
- add a golden file;
- document deployment dependencies.

### Activity-basis change

- update `ActivityMappingPanel.jsx` and backend normalization;
- keep the public UI at the documented four options unless intentionally revised;
- record requested/resolved mapping in diagnostics;
- update `ACTIVITY_PROCESSING.md` and validation tolerances;
- document units and threshold implications.

### Diagnostic or deployment change

- update `/api/version` feature flags;
- update `DIAGNOSTICS_AND_TROUBLESHOOTING.md` or `DEPLOYMENT.md`;
- update `.env.example`;
- add a change-log entry.

## Writing principles

- Distinguish implementation fact from scientific recommendation.
- State units and signal scale.
- Do not describe exploratory combinations as validated.
- Use exact endpoint, setting, and environment-variable names.
- Include the date and release/commit when documenting validation.
- Remove obsolete instructions rather than retaining contradictory historical guidance.
- Explain quality concepts in both technical and plain language, especially analyzable hours, consecutive valid days, and sleep-window coverage.

## GitHub publishing and links

Commit the entire `docs/` directory and root `README.md`. Configure both values in the frontend deployment:

```text
VITE_GITHUB_REPOSITORY_URL=https://github.com/owner/repository
VITE_GITHUB_DOCS_URL=https://github.com/owner/repository/tree/main/src/docs
```

`VITE_GITHUB_DOCS_URL` is the preferred direct target and can include a branch or custom documentation directory. The Documentation page still shows a clickable link when it is omitted by deriving `/tree/main/src/docs` from the repository URL. The bundled project default is used only as a final fallback.

## Release documentation checks

Before deployment:

1. search the in-app documentation for body-only phrases such as “expected epochs” and “longest consecutive run”;
2. click the GitHub docs link and confirm the deployed branch/path exists;
3. compare all ten workflow labels between the sidebar, in-app guide, and GitHub user guide;
4. confirm page 2 describes the current default thresholds and customization opt-in;
5. confirm future sensor features are explicitly labelled as not yet analysed;
6. record the release in `docs/CHANGELOG.md`.
