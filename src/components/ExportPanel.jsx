import React, { useMemo, useState } from "react";
import { downloadBlob, downloadJson, rowsToCsv, summaryResultsToRows } from "../services/exportUtils";
import { getAlgorithmLabel, getMetricLabel } from "../services/configUtils";
import ProcessedActivityDownload from "./ProcessedActivityDownload";

function Help({ text }) {
  return <span tabIndex={0} role="img" aria-label={text} title={text} style={{ cursor: "help", color: "#2563eb", marginLeft: 5 }}>ⓘ</span>;
}

export default function ExportPanel({
  title, exportRegistry, resultsGenerated, summaryResults = {}, qcWarnings = [],
  metricRegistry, algorithmRegistry, analysisConfig, selectedAlgorithm,
  analysisMode, supportFileSummary, dataQuality, lightResults = {},
  multiFileResults = [], onDownloadProcessedActivity = () => {},
  processedActivityDownloadState = {},
}) {
  const [dailySelected, setDailySelected] = useState(true);
  const [aggregateSelected, setAggregateSelected] = useState(true);
  const enabledExports = (exportRegistry?.exports ?? []).filter((item) => item.enabled && ["csv_summary", "json_full"].includes(item.id));
  const selectedAlgorithmLabel = getAlgorithmLabel(algorithmRegistry, selectedAlgorithm);
  const completed = useMemo(() => multiFileResults.filter((row) => ["completed", "completed_with_warnings"].includes(row.status)), [multiFileResults]);
  const dailyRows = useMemo(() => completed.flatMap((row) => row.releaseTables?.daily_rows ?? []), [completed]);
  const aggregatedRows = useMemo(() => completed.flatMap((row) => row.releaseTables?.aggregated_rows ?? []), [completed]);
  const anyGenerated = resultsGenerated && completed.length > 0;
  const saveCsv = (rows, filename) => downloadBlob(rowsToCsv(rows), filename, "text/csv;charset=utf-8");

  const exportSummaryCsv = () => {
    const rows = summaryResultsToRows(summaryResults, (metricId) => getMetricLabel(metricRegistry, metricId)).map((row) => ({
      ...row, sleep_algorithm: selectedAlgorithmLabel || selectedAlgorithm || "not_selected",
    }));
    downloadBlob(rowsToCsv(rows, ["metric", "label", "value", "sleep_algorithm"]), "actilab_metric_summary_long.csv", "text/csv;charset=utf-8");
  };
  const buildMetadata = () => ({
    schema_version: "actilab-export-bundle-1.0",
    exported_at_utc: new Date().toISOString(),
    software: "ActiLab", analysisMode,
    selectedAlgorithm, selectedAlgorithmLabel,
    analysisConfig, qcWarnings, supportFileSummary, dataQuality,
    selected_outputs: { daily_csv: dailySelected, aggregated_csv: aggregateSelected, metadata_json: true },
    recording_methods: completed.map((row) => ({
      source_file: row.fileName,
      effective_methods: row.effectiveMethods || null,
      release_table_schema: row.releaseTables?.schema_version || null,
      daily_scope: row.releaseTables?.daily_scope || null,
      aggregation_notes: row.releaseTables?.aggregation_notes || null,
      dataQuality: row.dataQuality || null,
      processingProvenance: row.processingProvenance || null,
      activityMapping: row.activityMapping || null,
      detectedInputType: row.detectedInputType || null,
      lightResults: row.lightResults || {},
      lightDiagnostics: row.lightDiagnostics || {},
      diagnostics: row.diagnostics || null,
      qcWarnings: row.qcWarnings || [],
    })),
    note: "All available effective parameters and default values are recorded, not only user overrides. ActiLab preprocessing and sleep scoring are not proven equivalent to GGIR.",
  });
  const exportAllJson = () => downloadJson({
    results: completed.map((row) => ({ source_file: row.fileName, results: row.results, light_results: row.lightResults })),
    methods: buildMetadata(),
    qcWarnings, analysisMode, selectedAlgorithm, selectedAlgorithmLabel,
    analysisConfig, supportFileSummary, dataQuality, lightResults,
  }, "actilab_results_full.json");
  const exportMethods = () => downloadJson(buildMetadata(), "actilab_meta.json");
  const handleLegacy = (item) => item.id === "csv_summary" ? exportSummaryCsv() : exportAllJson();

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#475569", lineHeight: 1.6, marginTop: 0 }}>
        Export daily quality-window summaries, recording/participant-level results, and reproducibility metadata.
        These are <strong>ActiLab output schemas inspired by GGIR’s daily/aggregate levels</strong>, not GGIR-identical files.
        <Help text="Daily rows describe measured QC windows and valid-epoch activity. Recording-level metrics come directly from ActiLab analysis; multi-day IS/IV/RA and sleep results are not averages of daily values. GGIR-specific outputs and definitions must be benchmarked separately." />
      </p>
      <ProcessedActivityDownload batchResults={multiFileResults} onDownload={onDownloadProcessedActivity} downloadState={processedActivityDownloadState} />
      <div style={{ marginTop: 14, border: "1px solid #cbd5e1", borderRadius: 14, padding: 16, background: "#f8fafc" }}>
        <div style={{ fontWeight: 800, marginBottom: 12 }}>Choose research summary outputs <Help text="Only selected CSVs download. Metadata is always provided separately and contains defaults, resolved settings, per-file provenance and package versions where available." /></div>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, cursor: "pointer" }}>
          <input type="checkbox" checked={dailySelected} onChange={(e) => setDailySelected(e.target.checked)} />
          <span>Daily CSV <Help text="One row per calendar day or recording-anchored 24h QC window, including validity, missingness, non-wear and valid-epoch activity summaries. When eligible windows were actually scored, nightly TST/WASO/efficiency are assigned to the window start date, not guessed for missing windows." /></span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, cursor: "pointer" }}>
          <input type="checkbox" checked={aggregateSelected} onChange={(e) => setAggregateSelected(e.target.checked)} />
          <span>Aggregated CSV <Help text="One row per selected recording or joined participant. Includes real recording-level scalar metrics from pyActigraphy/ActiLab and activity across valid epochs; no fabricated GGIR variables." /></span>
        </label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          <button type="button" disabled={!anyGenerated || !dailySelected || !dailyRows.length} onClick={() => saveCsv(dailyRows, "actilab_daily.csv")}>Download daily CSV ({dailyRows.length} rows)</button>
          <button type="button" disabled={!anyGenerated || !aggregateSelected || !aggregatedRows.length} onClick={() => saveCsv(aggregatedRows, "actilab_aggregated.csv")}>Download aggregated CSV ({aggregatedRows.length} rows)</button>
          <button type="button" disabled={!anyGenerated} onClick={exportMethods}>Download metadata JSON <Help text="Contains effective preprocessing, minimum valid hours/days, auto-selected or manually selected metric, epoch length, analysis parameters, masks, input detection, software versions and processing warnings when available." /></button>
        </div>
        {resultsGenerated && !anyGenerated && <p role="status" style={{ color: "#92400e" }}>Re-run analysis to generate the daily and aggregated table payloads for this version. Older saved results may not include them.</p>}
        {anyGenerated && !dailyRows.length && <p role="status" style={{ color: "#92400e" }}>No daily QC rows were returned; review data-quality diagnostics before exporting.</p>}
        <p style={{ color: "#64748b", fontSize: 12, marginBottom: 0 }}>Metadata is downloadable regardless of the two CSV selections. Files that failed analysis are excluded from numeric outputs and remain identified in quality-control warnings.</p>
      </div>
      <h3 style={{ marginBottom: 8, marginTop: 20, fontSize: 16 }}>Additional formats</h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {enabledExports.map((item) => <button type="button" key={item.id} disabled={!resultsGenerated} onClick={() => handleLegacy(item)}>{item.id === "csv_summary" ? "Metric summary (long CSV)" : "Full results JSON"}</button>)}
      </div>
    </div>
  );
}
