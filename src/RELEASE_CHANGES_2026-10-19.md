# ActiLab source update — 19 October 2026

## Delivered in this source bundle

1. **Raw acceleration epoch selection:** Step 3 offers 5, 10, 15, 30 and 60 seconds (legacy default 30s). The parameter reaches streaming GENEActiv BIN, GT3X, and eligible CWA conversion paths. Pre-aggregated activity files retain source epochs. The request and resolved settings are recorded in exports.
2. **CSV raw XYZ ingestion:** New `backend/tabular_xyz.py` and updated automatic/manual CSV mapping support timestamp + x/y/z in explicit g, mg, or m/s²; may also map light, temperature and non-wear. Recognizable units are inferred from column headers; ambiguity triggers a clear error. ENMO/MAD/PIM/ZCM/TAT are available where compatible. XYZ CSV decoding **is not** GGIR sensor auto-calibration.
3. **Daily and aggregated CSV results:** `backend/release_exports.py` provides tables in `/api/analyze/basic` derived from actual final QC masks and actual analysis output. Daily rows are defined by each QC window; valid-epoch summary and night scoring appear only where measured. Aggregated rows contain actual recording/joined-participant scalar results; no fictitious per-day RA/IS/IV or GGIR-specific columns.
4. **Complete methods metadata:** Backend `effective_methods_manifest` includes signal epoch and metric settings, explicit raw defaults, quality defaults and effective QC settings, selected analysis and algorithm configuration, device/readers, CSV mappings, concatenation, QC, provenance and Python package versions. Frontend downloads `actilab_meta.json` for completed files independently of selected CSVs.
5. **Safety for sleep-scoring claims:** Warnings when applying classic count-based sleep methods to raw acceleration in mg. Existing pyActigraphy sleep paths remain intact. Added per-night TST/WASO/efficiency only where existing scored windows satisfy coverage rules.
6. **Tooltip/help text and documentation:** New searchable Plug-and-play & outputs in-app section, tooltips at CSV mapping, activity epochs, metrics and export; `docs/PLUG_AND_PLAY_RELEASE.md`, `docs/GGIR_COMPARISON_PROTOCOL.md`, and 130-entry candidate metric catalogue. Existing docs, changelog, and README updated.
7. **Comparison helper:** `validation/compare_outputs.py` computes numerical agreement on user-aligned GGIR/ActiLab output columns, but does not establish scientific validity without actual paired raw recordings.

## Important limitations / not claimed as complete

- **GGIR HDCZA/SIB angle-based automatic sleep scoring is NOT implemented.** Automatic file recognition and reader selection do not imply automatic selection of a validated sleep algorithm for every input type; the existing pyActigraphy scorers still require appropriate device, units, populations and epoch conditions.
- **No empirical GGIR comparison has been performed.** A comparison protocol and CLI utility are supplied; paired raw files and a GGIR run are necessary for a validation result. This is not a GGIR-verified official scientific release.
- **Device-specific native calibration/non-wear parity is not assured**; the XYZ CSV parser expects known physical units but performs no static/dynamic temperature auto-calibration.
- **Metric catalogue is a selection/release planning document**, not evidence that every listed metric is implemented.
- **ActiLab daily and aggregate CSVs are GGIR-inspired levels, not identical GGIR file schema**. Sleep metrics are included only where the selected existing scorer genuinely produced adequate sleep windows.
- **Re-run all data after changing epoch length**; compare and document downstream impacts on activity, thresholds and sleep. Existing vendor counts are not reconstructed from raw signals.

## Verification performed

- `PYTHONPATH=. python -m unittest backend.tests.test_release_exports_and_xyz backend.tests.test_localized_tabular backend.tests.test_data_quality backend.tests.test_activity_metrics -q`: **33 passed**.
- Full suite: **87 tests, 7 errors**, all 7 confined to GT3X streaming tests requiring unavailable `pygt3x`. The original uploaded source baseline has **79 tests, the same 7 errors** on the same environment. In a backend environment with `pygt3x==0.7.1`, re-run the full suite and record the result.
- Python byte-compilation on `backend` and `validation`: passed.
- React JSX syntax checks of seven changed files: passed. Full Vite build **not performed** because the uploaded `src/` archive does not contain the parent `package.json` or `node_modules`.

## Deploying/merging

Apply the included `src/` tree to the corresponding `src/` folder in your current frontend/backend repository, retaining the repository's package manifests and deployment infrastructure. Verify `requirements.txt`/runtime dependencies against your actual backend environment and redeploy backend and frontend together. Run the regression suite and replay representative BIN, GT3X, CWA, raw XYZ CSV and activity-count CSV files before production use. Review `docs/PLUG_AND_PLAY_RELEASE.md` and scientific cautions with the research team.
