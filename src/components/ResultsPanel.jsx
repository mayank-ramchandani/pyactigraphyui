import React from "react";
import {
  getAlgorithmDefinition,
  getAlgorithmLabel,
  getMetricDefinition,
  getMetricLabel,
  getMetricResultSchema,
} from "../services/configUtils";

function formatResultValue(value, schema) {
  if (value == null) return "Not available";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number") {
    const rounded = Number.isInteger(value) ? String(value) : value.toFixed(4);
    return schema?.unit ? `${rounded} ${schema.unit}` : rounded;
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
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
}) {
  const resultKeys = Object.keys(summaryResults || {});
  const activeMetricDefinition = selectedResultMetric
    ? getMetricDefinition(metricRegistry, selectedResultMetric)
    : null;
  const activeAlgorithm = selectedAlgorithm
    ? getAlgorithmDefinition(algorithmRegistry, selectedAlgorithm)
    : null;

  const selectableMetricIds = [...new Set([...(selectedMetrics || []), ...resultKeys])];

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 20,
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Generate summary metrics and method-aware outputs from the currently selected pyActigraphy workflow.
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
          Selected algorithm:{" "}
          <strong>{selectedAlgorithm ? getAlgorithmLabel(algorithmRegistry, selectedAlgorithm) : "Not selected"}</strong>
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

      {resultsGenerated && (
        <>
          <div style={{ marginBottom: 16 }}>
            <select
              value={selectedResultMetric}
              onChange={(e) => setSelectedResultMetric(e.target.value)}
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: "1px solid #cbd5e1",
                background: "white",
              }}
            >
              <option value="">Select metric to inspect</option>
              {selectableMetricIds.map((metricId) => (
                <option key={metricId} value={metricId}>
                  {getMetricLabel(metricRegistry, metricId)}
                </option>
              ))}
            </select>
          </div>

          {activeMetricDefinition && (
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 16,
                padding: 16,
                background: "#f8fafc",
                marginBottom: 16,
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 8 }}>
                {activeMetricDefinition.label}
              </div>
              <div style={{ color: "#475569", lineHeight: 1.6, marginBottom: 8 }}>
                {activeMetricDefinition.description}
              </div>

              {(activeMetricDefinition.references || []).length > 0 && (
                <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.5 }}>
                  <strong>References:</strong> {activeMetricDefinition.references.join("; ")}
                </div>
              )}
            </div>
          )}

          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 16,
              padding: 16,
              background: "#f8fafc",
              marginBottom: 16,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Summary Table</div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {Object.entries(summaryResults).map(([key, value]) => {
                  const schema = getMetricResultSchema(metricRegistry, key);
                  return (
                    <tr key={key}>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "left" }}>
                        {getMetricLabel(metricRegistry, key)}
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

          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 16,
              padding: 16,
              background: "#f8fafc",
              marginBottom: 16,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Methods Summary</div>
            <div style={{ color: "#475569", lineHeight: 1.7, fontSize: 14 }}>
              Metrics requested:{" "}
              {(selectedMetrics || []).map((metricId) => getMetricLabel(metricRegistry, metricId)).join(", ") || "None"}
              <br />
              Sleep/rest algorithm: {selectedAlgorithm ? getAlgorithmLabel(algorithmRegistry, selectedAlgorithm) : "None"}
              <br />
              Analysis mode: {analysisMode === "standard" ? "Standard defaults" : "Customized settings"}
              {activeAlgorithm?.citationText && (
                <>
                  <br />
                  Algorithm citation: {activeAlgorithm.citationText}
                </>
              )}
              {analysisConfig?.metrics?.length > 0 && (
                <>
                  <br />
                  Metric parameters: {JSON.stringify(analysisConfig.metrics)}
                </>
              )}
              {analysisConfig?.algorithm && (
                <>
                  <br />
                  Algorithm parameters: {JSON.stringify(analysisConfig.algorithm)}
                </>
              )}
            </div>
          </div>

          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 16,
              padding: 16,
              background: "#fff7ed",
            }}
          >
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