import React from "react";
import {
  getAlgorithmDefinition,
  getAlgorithmLabel,
  getMetricDefinition,
  getMetricLabel,
  getMetricResultSchema,
} from "../services/configUtils";
import { LIGHT_METRIC_DEFINITIONS } from "./LightMetricsPanel";

const RESULT_LABEL_OVERRIDES = {
  sleep_window_source: "Sleep window source",
  sleep_window_method: "Sleep window method",
  sleep_window_count: "Sleep window count",
  time_in_bed_minutes: "Time in bed / rest window",
  sleep_window_estimated: "Sleep window estimated",
  sleep_window_notes: "Sleep window notes",
  analysis_window_mode: "Analysis window mode",
  analysis_window_count: "Analysis window count",
  analysis_window_summary: "Analysis window summary",
};

function resultLabel(metricRegistry, key) {
  return RESULT_LABEL_OVERRIDES[key] || getMetricLabel(metricRegistry, key);
}

function formatResultValue(value, schema) {
  if (value == null) return "Not available";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number") {
    const rounded = Number.isInteger(value) ? String(value) : value.toFixed(4);
    return schema?.unit ? `${rounded} ${schema.unit}` : rounded;
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatLightValue(value) {
  if (value == null || Number.isNaN(value)) return "";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
}

function lightResultScalarText(result) {
  if (!result) return "Not available";
  if (result.kind === "scalar") return formatLightValue(result.value);
  if (result.kind === "series") return `${result.values?.length || 0} value(s)`;
  if (result.kind === "dataframe") return `${result.rows?.length || 0} row(s)`;
  return "Available";
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

export default function ResultsPanel({
  title,
  resultsGenerated,
  onGenerate,
  selectedResultMetric,
  setSelectedResultMetric,
  selectedMetrics,
  summaryResults,
  qcWarnings,
  metricRegistry,
  algorithmRegistry,
  selectedAlgorithm,
  analysisConfig,
  analysisError,
  analysisLoading,
  analysisMode,
  supportFileSummary,
  lightResults = {},
  selectedLightMetrics = [],
  lightMetricSettings = {},
  lightAnalysisError = "",
}) {
  const resultKeys = Object.keys(summaryResults || {});
  const lightResultKeys = Object.keys(lightResults || {});
  const analysisWindows = Array.isArray(summaryResults?.analysis_windows) ? summaryResults.analysis_windows : [];
  const activeMetricDefinition = selectedResultMetric
    ? getMetricDefinition(metricRegistry, selectedResultMetric)
    : null;
  const activeAlgorithm = selectedAlgorithm
    ? getAlgorithmDefinition(algorithmRegistry, selectedAlgorithm)
    : null;

  const hiddenResultKeys = new Set(["analysis_windows"]);
  const selectableMetricIds = [...new Set([...(selectedMetrics || []), ...resultKeys.filter((key) => !hiddenResultKeys.has(key))])];

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Generate summary metrics and family-aware outputs from the selected actigraphy workflow.
      </p>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        <button
          onClick={onGenerate}
          disabled={analysisLoading}
          style={{
            padding: "10px 16px",
            borderRadius: 12,
            background: analysisLoading ? "#94a3b8" : "#0f172a",
            color: "white",
            border: "none",
            cursor: analysisLoading ? "not-allowed" : "pointer",
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
      </div>

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

      {resultsGenerated && (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              value={selectedResultMetric}
              onChange={(e) => setSelectedResultMetric(e.target.value)}
              style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}
            >
              <option value="">Select result to inspect</option>
              {selectableMetricIds.map((metricId) => (
                <option key={metricId} value={metricId}>
                  {getMetricLabel(metricRegistry, metricId)}
                </option>
              ))}
              {Object.keys(summaryResults || {})
                .filter((key) => !selectableMetricIds.includes(key) && !hiddenResultKeys.has(key))
                .map((key) => (
                  <option key={key} value={key}>
                    {key}
                  </option>
                ))}
            </select>
          </div>

          {activeMetricDefinition && (
            <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>{activeMetricDefinition.label}</div>
              <div style={{ color: "#475569", lineHeight: 1.6, marginBottom: 8 }}>{activeMetricDefinition.description}</div>
              {(activeMetricDefinition.references || []).length > 0 && (
                <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.5 }}>
                  <strong>References:</strong> {activeMetricDefinition.references.join("; ")}
                </div>
              )}
            </div>
          )}

          <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Summary Table</div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {Object.entries(summaryResults).filter(([key]) => key !== "analysis_windows").map(([key, value]) => {
                  const schema = getMetricResultSchema(metricRegistry, key);
                  return (
                    <tr key={key}>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "left" }}>
                        {resultLabel(metricRegistry, key)}
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
                        <td style={{ padding: 8, borderTop: "1px solid #c7d2fe", textAlign: "right" }}>{window.duration_hours ?? "—"} h</td>
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