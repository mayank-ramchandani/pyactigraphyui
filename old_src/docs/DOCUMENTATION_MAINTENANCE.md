# Documentation maintenance

## Sources of truth

| Subject | Primary source |
|---|---|
| Metric labels/defaults | `config/metricRegistry.json` |
| Algorithms/defaults | `config/algorithmRegistry.json` |
| Analysis families | `config/analysisFamilyRegistry.json` |
| Shared parameters | `config/sharedParamRegistry.json` |
| Workflow names | `config/appConfig.json` |
| Backend feature flags | `backend/app.py` `/api/version` |
| In-app guide | `components/DocumentationPanel.jsx` |
| Long-form documentation | `docs/*.md` |

The in-app metric, algorithm, family, and workflow tables are generated from registries. Explanatory methods text is maintained manually and must be updated when implementation behaviour changes.

## Documentation checklist for every change

### New or changed metric

- update metric registry;
- update backend calculation and JSON serialization;
- update `METRICS_AND_ALGORITHMS.md`;
- add or update validation tests;
- add a change-log entry;
- confirm Results and Documentation tables.

### New or changed file format

- update reader inference and loader;
- document signal, units, mapping, and limitations in `FILE_FORMATS.md`;
- update in-app file table;
- add a golden file;
- document deployment dependencies.

### Activity mapping change

- update `ActivityMappingPanel.jsx` and backend normalization;
- record requested/resolved mapping in diagnostics;
- update `ACTIVITY_PROCESSING.md`;
- update validation tolerances;
- document threshold implications.

### Diagnostic or deployment change

- update `/api/version` feature flags;
- update `DIAGNOSTICS_AND_TROUBLESHOOTING.md` or `DEPLOYMENT.md`;
- update environment-variable examples;
- add a change-log entry.

## Writing principles

- Distinguish implementation fact from scientific recommendation.
- State units and signal scale.
- Do not describe exploratory combinations as validated.
- Use exact endpoint, setting, and environment-variable names.
- Include the date and release/commit when documenting validation.
- Remove obsolete instructions rather than leaving contradictory notes.

## GitHub publishing

Commit the entire `docs/` directory and root `README.md`. GitHub renders the Markdown automatically. Configure:

```text
VITE_GITHUB_REPOSITORY_URL=https://github.com/owner/repository
```

so users can open the repository documentation from the website.
