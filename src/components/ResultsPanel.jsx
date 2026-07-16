import React, { useState } from "react";
import {
  getAlgorithmDefinition,
  getAlgorithmLabel,
  getMetricDefinition,
  getMetricLabel,
  getMetricResultSchema,
} from "../services/configUtils";
import { LIGHT_METRIC_DEFINITIONS } from "./LightMetricsPanel";
import DiagnosticPanel, { downloadDiagnostics } from "./DiagnosticPanel";
import { activityMappingLabel } from "./ActivityMappingPanel";


const RESULT_INFO_OVERRIDES = {
  sleep_window_source: "Shows whether TST, WASO, and sleep efficiency used a sleep diary/user-defined window, a pyActigraphy-estimated rest window, or no available sleep window.",
  sleep_window_method: "Shows which method produced the sleep/rest window used for window-dependent sleep metrics.",
  sleep_window_count: "Number of sleep/rest windows used in the sleep metric calculations.",
  time_in_bed_minutes: "Total minutes inside the diary-defined or estimated rest window. Sleep efficiency is calculated relative to this window.",
  sleep_window_estimated: "True means the sleep/rest window was estimated by the selected pyActigraphy Crespo_AoT/Roenneberg_AoT method rather than supplied by a sleep diary or manual interval.",
  sleep_window_notes: "Backend notes about how the sleep/rest window was selected, or why Crespo_AoT/Roenneberg_AoT could not produce a usable window.",
  sleep_window_details_summary: "Human-readable summary of each diary-defined or pyActigraphy-estimated sleep/rest window.",
  sleep_window_details: "Structured per-night diagnostics for the sleep/rest window detection method.",
  analysis_window_mode: "Shows whether metrics were calculated on the whole recording or selected analysis intervals.",
  analysis_window_count: "Number of selected analysis intervals used for this run.",
  analysis_window_summary: "Explanation of how selected-interval outputs were summarized in the top-level table.",
};

const RESULT_LABEL_OVERRIDES = {
  sleep_window_source: "Sleep window source",
  sleep_window_method: "Sleep window method",
  sleep_window_count: "Sleep window count",
  time_in_bed_minutes: "Time in bed / rest window",
  sleep_window_estimated: "Sleep window estimated",
  sleep_window_notes: "Sleep window notes",
  sleep_window_details_summary: "Sleep window details summary",
  sleep_window_details: "Sleep window details",
  analysis_window_mode: "Analysis window mode",
  analysis_window_count: "Analysis window count",
  analysis_window_summary: "Analysis window summary",
};

function resultLabel(metricRegistry, key) {
  return RESULT_LABEL_OVERRIDES[key] || getMetricLabel(metricRegistry, key);
}

function metricInfoText(metricRegistry, key) {
  const metric = getMetricDefinition(metricRegistry, key);
  const pieces = [];
  if (metric?.description) pieces.push(metric.description);
  else if (metric?.summary) pieces.push(metric.summary);
  if (RESULT_INFO_OVERRIDES[key]) pieces.push(RESULT_INFO_OVERRIDES[key]);
  if ((metric?.references || []).length > 0) pieces.push(`References: ${metric.references.join("; ")}`);
  return pieces.join("\n");
}

function lightMetricInfoText(metricId) {
  const metric = LIGHT_METRIC_DEFINITIONS[metricId];
  if (!metric) return "";
  return [metric.summary, metric.description].filter(Boolean).join("\n");
}

function InfoBubble({ text }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;

  return (
    <span
      className="metric-info-bubble-wrap"
      style={{ position: "relative", display: "inline-flex", verticalAlign: "middle" }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={text}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((value) => !value);
        }}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 18,
          height: 18,
          marginLeft: 8,
          borderRadius: 999,
          border: "1px solid #94a3b8",
          color: "#334155",
          background: "#ffffff",
          fontSize: 12,
          fontWeight: 800,
          lineHeight: 1,
          cursor: "help",
          padding: 0,
          fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        i
      </button>
      {open && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            zIndex: 2000,
            left: 28,
            top: "50%",
            transform: "translateY(-50%)",
            width: 320,
            maxWidth: "min(320px, calc(100vw - 80px))",
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
            background: "#0f172a",
            color: "#f8fafc",
            boxShadow: "0 12px 35px rgba(15, 23, 42, 0.25)",
            fontSize: 13,
            lineHeight: 1.45,
            fontWeight: 500,
            whiteSpace: "pre-line",
            textAlign: "left",
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
}

function formatSigFigNumber(value, sig = 3) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "";
  if (number === 0) return "0";
  const abs = Math.abs(number);
  if (abs >= 0.001 && abs < 10000) {
    const decimals = Math.max(0, sig - Math.floor(Math.log10(abs)) - 1);
    return Number(number.toFixed(decimals)).toString();
  }
  return number.toPrecision(sig).replace(/(\.\d*?[1-9])0+(e|$)/, "$1$2").replace(/\.0+(e|$)/, "$1");
}

function compactJson(value) {
  try {
    return JSON.stringify(value, (key, item) => (typeof item === "number" ? formatSigFigNumber(item) : item));
  } catch (error) {
    return String(value);
  }
}

function formatResultValue(value, schema) {
  if (value == null) return "Not available";
  if (Array.isArray(value)) return value.map((item) => (typeof item === "number" ? formatSigFigNumber(item) : String(item))).join(", ");
  if (typeof value === "number") {
    const rounded = formatSigFigNumber(value);
    return schema?.unit ? `${rounded} ${schema.unit}` : rounded;
  }
  if (typeof value === "object") return compactJson(value);
  return String(value);
}

function formatLightValue(value) {
  if (value == null || Number.isNaN(value)) return "";
  if (typeof value === "number") return formatSigFigNumber(value);
  return String(value);
}

function lightResultScalarText(result) {
  if (!result) return "Not available";
  if (result.kind === "scalar") return formatLightValue(result.value);
  if (result.kind === "series") return `${result.values?.length || 0} value(s)`;
  if (result.kind === "dataframe") return `${result.rows?.length || 0} row(s)`;
  return "Available";
}

function formatSleepDetailValue(value) {
  if (value == null || value === "") return "—";
  if (typeof value === "number") return formatSigFigNumber(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function SleepWindowDetailsCard({ details }) {
  if (!Array.isArray(details) || details.length === 0) return null;

  return (
    <div style={{ border: "1px solid #bae6fd", borderRadius: 16, padding: 16, background: "#f0f9ff", marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <div style={{ fontWeight: 800 }}>Sleep Window Analysis Details</div>
        <InfoBubble text="This section explains exactly how the sleep/rest window was selected. Windows come from a sleep diary/manual window or from the selected pyActigraphy Crespo_AoT/Roenneberg_AoT onset-offset detector. No low-activity fallback window is used." />
      </div>
      <div style={{ color: "#475569", lineHeight: 1.6, fontSize: 14, marginBottom: 12 }}>
        These diagnostics show the actual sleep/rest windows used for window-dependent sleep metrics. If Crespo_AoT or Roenneberg_AoT does not return usable activity onset/offset arrays, those metrics will be unavailable rather than estimated with a fallback window.
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #bae6fd" }}>Night/date</th>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #bae6fd" }}>Sleep/rest window</th>
              <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #bae6fd" }}>Duration</th>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #bae6fd" }}>Method/source</th>
            </tr>
          </thead>
          <tbody>
            {details.map((item, idx) => (
              <tr key={`${item.start || item.date}-${idx}`}>
                <td style={{ padding: 8, borderTop: "1px solid #bae6fd" }}>{formatSleepDetailValue(item.date)}</td>
                <td style={{ padding: 8, borderTop: "1px solid #bae6fd" }}>{formatSleepDetailValue(`${item.start || "—"} → ${item.stop || "—"}`)}</td>
                <td style={{ padding: 8, borderTop: "1px solid #bae6fd", textAlign: "right" }}>{item.duration_hours != null ? `${formatSleepDetailValue(item.duration_hours)} h` : "—"}</td>
                <td style={{ padding: 8, borderTop: "1px solid #bae6fd", fontSize: 13, color: "#475569" }}>
                  <div>Method: {formatSleepDetailValue(item.method)}</div>
                  <div>Source: {formatSleepDetailValue(item.source)}</div>
                  <div>Estimated: {formatSleepDetailValue(item.estimated)}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function renderLightResult(result) {
  if (!result) return null;

  if (result.kind === "scalar") {
    return (
      <div style={{ padding: 16, borderRadius: 12, background: "white", border: "1px solid #e2e8f0", fontSize: 18, fontWeight: 700 }}>
        {formatLightValue(result.value)}
      </div>
    );
  }

  if (result.kind === "series") {
    return (
      <div style={{ overflowX: "auto", maxHeight: 360, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #cbd5e1" }}>Index</th>
              <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>Value</th>
            </tr>
          </thead>
          <tbody>
            {(result.index || []).slice(0, 300).map((label, idx) => (
              <tr key={`${label}-${idx}`}>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{label}</td>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatLightValue(result.values?.[idx])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (result.kind === "dataframe") {
    return (
      <div style={{ overflowX: "auto", maxHeight: 420, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #cbd5e1" }}>Index</th>
              {(result.columns || []).map((col) => (
                <th key={col} style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(result.rows || []).slice(0, 300).map((row, rowIdx) => (
              <tr key={`${row.index}-${rowIdx}`}>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{row.index}</td>
                {(row.values || []).map((value, colIdx) => (
                  <td key={`${rowIdx}-${colIdx}`} style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatLightValue(value)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return null;
}

function isCompletedStatus(status) {
  return ["completed", "completed_with_warnings"].includes(String(status || "").toLowerCase());
}

function statusLabel(status) {
  if (status === "completed_with_warnings") return "Completed with warnings";
  if (status === "completed") return "Completed";
  return "Failed";
}

export default function ResultsPanel({
  title,
  actigraphyFiles = [],
  selectedAnalysisFileNames = [],
  setSelectedAnalysisFileNames = () => {},
  multiFileResults = [],
  resultsGenerated,
  onGenerate,
  selectedMetrics = [],
  summaryResults,
  qcWarnings,
  metricRegistry,
  algorithmRegistry,
  selectedAlgorithm,
  analysisConfig,
  analysisError,
  analysisLoading,
  analysisProgress = {},
  analysisMode,
  activityMapping = "auto",
  supportFileSummary,
  lightResults = {},
  selectedLightMetrics = [],
  lightMetricSettings = {},
  lightAnalysisError = "",
}) {
  const lightResultKeys = Object.keys(lightResults || {});
  const selectedAnalysisNameSet = new Set(selectedAnalysisFileNames || []);
  const completedBatchResults = Array.isArray(multiFileResults) ? multiFileResults : [];
  const hasBatchResults = completedBatchResults.length > 0;
  const successfulBatchResults = completedBatchResults.filter((item) => isCompletedStatus(item.status));
  const batchMetricKeys = Array.from(new Set(
    successfulBatchResults.flatMap((item) => Object.keys(item.results || {}))
  )).filter((key) => !["analysis_windows", "sleep_window_details"].includes(key));
  const displayBatchMetricKeys = batchMetricKeys.slice(0, 5);
  const analysisWindows = Array.isArray(summaryResults?.analysis_windows) ? summaryResults.analysis_windows : [];
  const sleepWindowDetails = Array.isArray(summaryResults?.sleep_window_details) ? summaryResults.sleep_window_details : [];
  const activeAlgorithm = selectedAlgorithm
    ? getAlgorithmDefinition(algorithmRegistry, selectedAlgorithm)
    : null;
  const selectedMetricCount = (analysisConfig?.metrics || []).length || (selectedMetrics || []).length;
  const selectedLightMetricCount = (selectedLightMetrics || []).length;
  const selectedFileCount = selectedAnalysisFileNames.length;

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Generate summary metrics and family-aware outputs from the selected actigraphy workflow.
      </p>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        <button
          onClick={onGenerate}
          disabled={analysisLoading || selectedFileCount === 0}
          style={{
            padding: "10px 16px",
            borderRadius: 12,
            background: analysisLoading || selectedFileCount === 0 ? "#94a3b8" : "#0f172a",
            color: "white",
            border: "none",
            cursor: analysisLoading || selectedFileCount === 0 ? "not-allowed" : "pointer",
            fontWeight: 600,
          }}
        >
          {analysisLoading ? "Generating Results..." : "Generate Results"}
        </button>

        <div style={{ color: "#64748b", fontSize: 14 }}>
          Current mode: <strong>{analysisMode === "standard" ? "Standard" : "Customized"}</strong>
        </div>

        <div style={{ color: "#64748b", fontSize: 14 }}>
          Selected algorithm: <strong>{selectedAlgorithm ? getAlgorithmLabel(algorithmRegistry, selectedAlgorithm) : "Not selected"}</strong>
        </div>

        <div style={{ color: "#64748b", fontSize: 14 }}>
          Activity mapping: <strong>{activityMappingLabel(activityMapping)}</strong>
        </div>
      </div>

      <div
        style={{
          marginBottom: 16,
          padding: 12,
          borderRadius: 12,
          border: "1px solid #bfdbfe",
          background: "#eff6ff",
          color: "#1e3a8a",
          fontSize: 14,
          lineHeight: 1.5,
        }}
      >
        Selecting all activity/sleep metrics plus all light metrics can be slow, especially for large raw .bin or .gt3x files. This run has {selectedFileCount} file(s), {selectedMetricCount} activity/sleep metric(s), and {selectedLightMetricCount} light metric(s) selected. Keep this page open while the progress indicator updates.
      </div>

      {actigraphyFiles.length > 0 && (
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontWeight: 800 }}>Files selected for analysis</div>
              <div style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
                Preview is optional. The analysis will run for the checked files below and report any file-level errors separately.
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" onClick={() => setSelectedAnalysisFileNames(actigraphyFiles.map((file) => file.name))} style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", cursor: "pointer", fontWeight: 700 }}>
                Select all
              </button>
              <button type="button" onClick={() => setSelectedAnalysisFileNames([])} style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", cursor: "pointer", fontWeight: 700 }}>
                Clear
              </button>
            </div>
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {actigraphyFiles.map((file, idx) => {
              const checked = selectedAnalysisNameSet.has(file.name);
              return (
                <label key={`${file.name}-${idx}`} style={{ display: "flex", alignItems: "center", gap: 10, padding: 10, borderRadius: 12, border: "1px solid #e2e8f0", background: "white", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedAnalysisFileNames(Array.from(new Set([...(selectedAnalysisFileNames || []), file.name])));
                      } else {
                        setSelectedAnalysisFileNames((selectedAnalysisFileNames || []).filter((name) => name !== file.name));
                      }
                    }}
                  />
                  <span style={{ flex: 1, fontWeight: 700 }}>{file.name}</span>
                  <span style={{ color: "#64748b", fontSize: 13 }}>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                </label>
              );
            })}
          </div>
        </div>
      )}

      {analysisLoading && (
        <div
          style={{
            marginBottom: 16,
            padding: 14,
            borderRadius: 14,
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 8, color: "#334155", fontSize: 14 }}>
            <strong>{analysisProgress.phase || "Running analysis"}</strong>
            <span>{analysisProgress.percent ?? 0}% overall</span>
          </div>
          <div style={{ width: "100%", height: 10, borderRadius: 999, background: "#e2e8f0", overflow: "hidden" }}>
            <div
              style={{
                width: `${analysisProgress.percent ?? 0}%`,
                height: "100%",
                borderRadius: 999,
                background: "#0f172a",
                transition: "width 200ms ease",
              }}
            />
          </div>
          <div style={{ marginTop: 8, color: "#64748b", fontSize: 13, lineHeight: 1.5 }}>
            {analysisProgress.total > 0 && analysisProgress.current > 0
              ? `Backend stage ${analysisProgress.current} of ${analysisProgress.total}. `
              : "Uploading/preparing the current file. "}
            Current file: {analysisProgress.filePercent ?? 0}%.
            {analysisProgress.detail ? <div style={{ marginTop: 3 }}>{analysisProgress.detail}</div> : null}
          </div>
        </div>
      )}

      {analysisError && (
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            fontSize: 14,
          }}
        >
          {analysisError}
        </div>
      )}

      {lightAnalysisError && (
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #fed7aa",
            background: "#fff7ed",
            color: "#9a3412",
            fontSize: 14,
          }}
        >
          Light analysis warning: {lightAnalysisError}
        </div>
      )}

      {hasBatchResults && (
        <>
          <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
              <div style={{ fontWeight: 700 }}>Batch Summary</div>
              <button
                type="button"
                onClick={() => downloadDiagnostics(
                  {
                    generated_at: new Date().toISOString(),
                    files: completedBatchResults.map((item) => ({
                      fileName: item.fileName,
                      status: item.status,
                      error: item.error || null,
                      activityMapping: item.activityMapping || null,
                      diagnostics: item.diagnostics || null,
                      lightDiagnostics: item.lightDiagnostics || {},
                    })),
                  },
                  "actigraphy-batch-diagnostics.json"
                )}
                style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #94a3b8", background: "white", cursor: "pointer", fontWeight: 700 }}
              >
                Download all diagnostics
              </button>
            </div>
            <div style={{ color: "#475569", lineHeight: 1.6, fontSize: 14, marginBottom: 12 }}>
              Completed: <strong>{successfulBatchResults.length}</strong>; failed: <strong>{completedBatchResults.length - successfulBatchResults.length}</strong>.
              {displayBatchMetricKeys.length > 0 && " The table shows the first selected/result metrics; open each file below for full details."}
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 640, tableLayout: "fixed" }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #e2e8f0" }}>File</th>
                    <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #e2e8f0" }}>Status</th>
                    <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #e2e8f0" }}>Mapping</th>
                    {displayBatchMetricKeys.map((key) => (
                      <th key={key} style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #e2e8f0" }}>
                        {resultLabel(metricRegistry, key)}
                        <InfoBubble text={metricInfoText(metricRegistry, key)} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {completedBatchResults.map((item, idx) => (
                    <tr key={`${item.fileName}-${idx}`}>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", fontWeight: 700, overflowWrap: "anywhere", fontSize: 13 }}>{item.fileName}</td>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", color: isCompletedStatus(item.status) ? (item.status === "completed_with_warnings" ? "#9a3412" : "#166534") : "#991b1b", overflowWrap: "anywhere", fontSize: 13 }}>
                        {isCompletedStatus(item.status) ? statusLabel(item.status) : item.error || "Failed"}
                      </td>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", fontSize: 13, overflowWrap: "anywhere" }}>
                        {activityMappingLabel(item.activityMapping?.resolved || item.activityMapping?.requested || activityMapping)}
                      </td>
                      {displayBatchMetricKeys.map((key) => (
                        <td key={`${item.fileName}-${key}`} style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right", fontSize: 13, overflowWrap: "anywhere" }}>
                          {isCompletedStatus(item.status) ? formatResultValue(item.results?.[key], getMetricResultSchema(metricRegistry, key)) : "—"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            {completedBatchResults.map((item, idx) => {
              const fileAnalysisWindows = Array.isArray(item.results?.analysis_windows) ? item.results.analysis_windows : [];
              const fileSleepWindowDetails = Array.isArray(item.results?.sleep_window_details) ? item.results.sleep_window_details : [];
              const fileLightResultKeys = Object.keys(item.lightResults || {});
              return (
                <details key={`${item.fileName}-detail-${idx}`} style={{ border: "1px solid #cbd5e1", borderRadius: 16, padding: 14, background: "white" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 800 }}>
                    {item.fileName} · {statusLabel(item.status).toLowerCase()}
                  </summary>
                  {!isCompletedStatus(item.status) ? (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ color: "#991b1b" }}>{item.error || "This file could not be analyzed."}</div>
                      <DiagnosticPanel
                        diagnostics={item.diagnostics}
                        title="Activity/sleep diagnostic report"
                        fileName={`${item.fileName || "file"}-diagnostics.json`}
                      />
                    </div>
                  ) : (
                    <div style={{ marginTop: 14 }}>
                      <div style={{ marginBottom: 12, padding: "10px 12px", borderRadius: 12, border: "1px solid #bfdbfe", background: "#eff6ff", color: "#1e3a8a", fontSize: 13 }}>
                        Activity mapping used: <strong>{activityMappingLabel(item.activityMapping?.resolved || item.activityMapping?.requested || activityMapping)}</strong>
                        {item.activityMapping?.source ? ` · Source: ${item.activityMapping.source}` : ""}
                      </div>
                      <div style={{ border: "1px solid #e2e8f0", borderRadius: 14, padding: 12, background: "#f8fafc", marginBottom: 12, maxHeight: 460, overflowY: "auto" }}>
                        <div style={{ fontWeight: 700, marginBottom: 8 }}>Summary Table</div>
                        <table style={{ width: "100%", borderCollapse: "collapse", tableLayout: "fixed" }}>
                          <tbody>
                            {Object.entries(item.results || {}).filter(([key]) => key !== "analysis_windows" && key !== "sleep_window_details").map(([key, value]) => (
                              <tr key={`${item.fileName}-${key}`}>
                                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "left" }}>
                                  {resultLabel(metricRegistry, key)}
                                  <InfoBubble text={metricInfoText(metricRegistry, key)} />
                                </td>
                                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                                  {formatResultValue(value, getMetricResultSchema(metricRegistry, key))}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <SleepWindowDetailsCard details={fileSleepWindowDetails} />
                      {fileAnalysisWindows.length > 0 && (
                        <div style={{ border: "1px solid #c7d2fe", borderRadius: 14, padding: 12, background: "#eef2ff", marginBottom: 12 }}>
                          <div style={{ fontWeight: 700, marginBottom: 8 }}>Analysis Window Details</div>
                          <div style={{ overflowX: "auto" }}>
                            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
                              <thead>
                                <tr>
                                  <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Interval</th>
                                  <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Start</th>
                                  <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Stop</th>
                                  <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Duration</th>
                                  <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Results</th>
                                </tr>
                              </thead>
                              <tbody>
                                {fileAnalysisWindows.map((window, windowIdx) => (
                                  <tr key={`${item.fileName}-${window.start}-${window.stop}-${windowIdx}`}>
                                    <td style={{ padding: 8, borderTop: "1px solid #c7d2fe" }}>{window.label || `Interval ${windowIdx + 1}`}</td>
                                    <td style={{ padding: 8, borderTop: "1px solid #c7d2fe" }}>{window.start}</td>
                                    <td style={{ padding: 8, borderTop: "1px solid #c7d2fe" }}>{window.stop}</td>
                                    <td style={{ padding: 8, borderTop: "1px solid #c7d2fe", textAlign: "right" }}>{window.duration_hours != null ? `${formatSigFigNumber(window.duration_hours)} h` : "—"}</td>
                                    <td style={{ padding: 8, borderTop: "1px solid #c7d2fe", fontSize: 13 }}>
                                      {window.error ? (
                                        <span style={{ color: "#991b1b" }}>{window.error}</span>
                                      ) : (
                                        Object.entries(window.results || {}).map(([key, value]) => `${resultLabel(metricRegistry, key)}: ${formatResultValue(value, getMetricResultSchema(metricRegistry, key))}`).join("; ") || "No values"
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                      {fileLightResultKeys.length > 0 && (
                        <div style={{ border: "1px solid #dbeafe", borderRadius: 14, padding: 12, background: "#eff6ff", marginBottom: 12 }}>
                          <div style={{ fontWeight: 700, marginBottom: 8 }}>Light Metrics Results</div>
                          {fileLightResultKeys.map((metricId) => {
                            const payload = item.lightResults[metricId];
                            const metric = LIGHT_METRIC_DEFINITIONS[metricId];
                            return (
                              <details key={`${item.fileName}-light-${metricId}`} style={{ border: "1px solid #bfdbfe", borderRadius: 12, padding: 10, background: "white", marginBottom: 8 }}>
                                <summary style={{ cursor: "pointer", fontWeight: 800 }}>{metric?.label || metricId} · {payload?.channel || "channel"}</summary>
                                {renderLightResult(payload?.result)}
                              </details>
                            );
                          })}
                        </div>
                      )}
                      <DiagnosticPanel
                        diagnostics={item.diagnostics}
                        title="Activity/sleep diagnostic report"
                        fileName={`${item.fileName || "file"}-diagnostics.json`}
                      />
                      {Object.entries(item.lightDiagnostics || {}).map(([metricId, diagnostic]) => (
                        <DiagnosticPanel
                          key={`${item.fileName}-light-diagnostic-${metricId}`}
                          diagnostics={diagnostic}
                          title={`Light metric diagnostic: ${LIGHT_METRIC_DEFINITIONS[metricId]?.label || metricId}`}
                          fileName={`${item.fileName || "file"}-${metricId}-light-diagnostics.json`}
                        />
                      ))}
                    </div>
                  )}
                </details>
              );
            })}
          </div>
        </>
      )}

      {resultsGenerated && !hasBatchResults && (
        <>
          <div style={{ marginBottom: 12, padding: "10px 12px", borderRadius: 12, border: "1px solid #bfdbfe", background: "#eff6ff", color: "#1e3a8a", fontSize: 13 }}>
            Activity mapping used: <strong>{activityMappingLabel(activityMapping)}</strong>
          </div>
          <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Summary Table</div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {Object.entries(summaryResults).filter(([key]) => key !== "analysis_windows" && key !== "sleep_window_details").map(([key, value]) => {
                  const schema = getMetricResultSchema(metricRegistry, key);
                  return (
                    <tr key={key}>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "left" }}>
                        {resultLabel(metricRegistry, key)}
                        <InfoBubble text={metricInfoText(metricRegistry, key)} />
                      </td>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                        {formatResultValue(value, schema)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <SleepWindowDetailsCard details={sleepWindowDetails} />

          {analysisWindows.length > 0 && (
            <div style={{ border: "1px solid #c7d2fe", borderRadius: 16, padding: 16, background: "#eef2ff", marginBottom: 16 }}>
              <div style={{ fontWeight: 700, marginBottom: 10 }}>Analysis Window Details</div>
              <div style={{ color: "#475569", lineHeight: 1.6, fontSize: 14, marginBottom: 12 }}>
                Metrics were calculated separately for each selected interval. The main summary table reports the mean of numeric metrics across intervals when possible.
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 760 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Interval</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Start</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Stop</th>
                      <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Duration</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #c7d2fe" }}>Results</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysisWindows.map((window, idx) => (
                      <tr key={`${window.start}-${window.stop}-${idx}`}>
                        <td style={{ padding: 8, borderTop: "1px solid #c7d2fe" }}>{window.label || `Interval ${idx + 1}`}</td>
                        <td style={{ padding: 8, borderTop: "1px solid #c7d2fe" }}>{window.start}</td>
                        <td style={{ padding: 8, borderTop: "1px solid #c7d2fe" }}>{window.stop}</td>
                        <td style={{ padding: 8, borderTop: "1px solid #c7d2fe", textAlign: "right" }}>{window.duration_hours != null ? `${formatSigFigNumber(window.duration_hours)} h` : "—"}</td>
                        <td style={{ padding: 8, borderTop: "1px solid #c7d2fe", fontSize: 13 }}>
                          {window.error ? (
                            <span style={{ color: "#991b1b" }}>{window.error}</span>
                          ) : (
                            Object.entries(window.results || {}).map(([key, value]) => `${resultLabel(metricRegistry, key)}: ${formatResultValue(value, getMetricResultSchema(metricRegistry, key))}`).join("; ") || "No values"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Methods Summary</div>
            <div style={{ color: "#475569", lineHeight: 1.7, fontSize: 14 }}>
              Analysis scope: <strong>{analysisConfig?.analysisScope || "metric"}</strong>
              <br />
              Families requested: {(analysisConfig?.families || []).map((family) => family.label || family.id).join(", ") || "None"}
              <br />
              Metrics requested: {(analysisConfig?.metrics || []).map((metric) => getMetricLabel(metricRegistry, metric.id)).join(", ") || "None"}
              <br />
              Sleep/rest algorithm: {selectedAlgorithm ? getAlgorithmLabel(algorithmRegistry, selectedAlgorithm) : "None"}
              <br />
              Analysis mode: {analysisMode === "standard" ? "Standard defaults" : "Customized settings"}
              <br />
              Analysis window mode: {analysisConfig?.analysisWindowSettings?.mode === "selected" ? "Selected intervals" : "Whole cleaned recording"}
              <br />
              Selected analysis intervals: {(analysisConfig?.analysisWindowSettings?.manualIntervals || []).length}
              <br />
              No-diary sleep-window estimation: {analysisConfig?.sleepWindowSettings?.estimateWithoutDiary === false ? "Disabled" : "Enabled"}
              {analysisConfig?.sleepWindowSettings?.estimateWithoutDiary !== false && (
                <>
                  <br />
                  Estimation method: {analysisConfig?.sleepWindowSettings?.method === "roenneberg_aot" ? "pyActigraphy Roenneberg_AoT" : "pyActigraphy Crespo_AoT"}
                </>
              )}
              {activeAlgorithm?.citationText && (
                <>
                  <br />
                  Algorithm citation: {activeAlgorithm.citationText}
                </>
              )}
            </div>
          </div>


          {lightResultKeys.length > 0 && (
            <div style={{ border: "1px solid #dbeafe", borderRadius: 16, padding: 16, background: "#eff6ff", marginBottom: 16 }}>
              <div style={{ fontWeight: 700, marginBottom: 10 }}>Light Metrics Results</div>
              <div style={{ color: "#475569", lineHeight: 1.7, fontSize: 14, marginBottom: 12 }}>
                Channel: <strong>{lightMetricSettings.channel || lightResults[lightResultKeys[0]]?.channel || "Auto/default"}</strong>
                <br />
                Selected light metrics: {(selectedLightMetrics || []).map((metricId) => LIGHT_METRIC_DEFINITIONS[metricId]?.label || metricId).join(", ") || "None"}
              </div>

              <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 16 }}>
                <tbody>
                  {lightResultKeys.map((metricId) => {
                    const payload = lightResults[metricId];
                    const metric = LIGHT_METRIC_DEFINITIONS[metricId];
                    return (
                      <tr key={`light-summary-${metricId}`}>
                        <td style={{ padding: 8, borderTop: "1px solid #bfdbfe", textAlign: "left" }}>
                          {metric?.label || metricId}
                          <InfoBubble text={lightMetricInfoText(metricId)} />
                        </td>
                        <td style={{ padding: 8, borderTop: "1px solid #bfdbfe", textAlign: "right" }}>
                          {lightResultScalarText(payload?.result)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <div style={{ display: "grid", gap: 14 }}>
                {lightResultKeys.map((metricId) => {
                  const payload = lightResults[metricId];
                  const metric = LIGHT_METRIC_DEFINITIONS[metricId];
                  return (
                    <details key={`light-detail-${metricId}`} style={{ border: "1px solid #bfdbfe", borderRadius: 14, padding: 12, background: "white" }}>
                      <summary style={{ cursor: "pointer", fontWeight: 800 }}>
                        {metric?.label || metricId} · {payload?.channel || "channel"}
                      </summary>
                      {metric?.description && (
                        <div style={{ color: "#475569", marginTop: 10, marginBottom: 10, lineHeight: 1.5 }}>
                          {metric.description}
                        </div>
                      )}
                      {renderLightResult(payload?.result)}
                    </details>
                  );
                })}
              </div>
            </div>
          )}

          {supportFileSummary && (
            <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#eef2ff", marginBottom: 16 }}>
              <div style={{ fontWeight: 700, marginBottom: 10 }}>Support File Processing</div>
              <div style={{ color: "#475569", lineHeight: 1.7, fontSize: 14 }}>
                Masking files: {supportFileSummary.masking_files_received ?? 0}; mask intervals applied: {supportFileSummary.mask_intervals_applied ?? 0}
                <br />
                Sleep diary files: {supportFileSummary.sleep_diary_files_received ?? 0}; diary rows loaded: {supportFileSummary.sleep_diary_rows_loaded ?? 0}; sleep windows loaded: {supportFileSummary.sleep_windows_loaded ?? 0}
                <br />
                Start/stop files: {supportFileSummary.start_stop_files_received ?? 0}; start/stop applied: {supportFileSummary.start_stop_applied ? "Yes" : "No"}
                {(supportFileSummary.notes || []).length > 0 && (
                  <>
                    <br />
                    Notes: {(supportFileSummary.notes || []).join(" | ")}
                  </>
                )}
              </div>
            </div>
          )}

          <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#fff7ed" }}>
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Quick QC</div>
            {qcWarnings.length === 0 ? (
              <div style={{ color: "#475569" }}>No QC warnings.</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18, color: "#7c2d12" }}>
                {qcWarnings.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}