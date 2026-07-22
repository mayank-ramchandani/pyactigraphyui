import React from "react";
import { downloadBlob, downloadJson, rowsToCsv, summaryResultsToRows } from "../services/exportUtils";
import { getAlgorithmLabel, getMetricLabel } from "../services/configUtils";

export default function ExportPanel({
  title,
  exportRegistry,
  resultsGenerated,
  summaryResults = {},
  qcWarnings = [],
  metricRegistry,
  algorithmRegistry,
  analysisConfig,
  selectedAlgorithm,
  analysisMode,
  supportFileSummary,
  dataQuality,
  lightResults = {},
}) {
  const enabledExports = (exportRegistry?.exports ?? []).filter((item) => item.enabled);
  const selectedAlgorithmLabel = getAlgorithmLabel(algorithmRegistry, selectedAlgorithm);

  const exportSummaryCsv = () => {
    const rows = summaryResultsToRows(summaryResults, (metricId) => getMetricLabel(metricRegistry, metricId)).map((row) => ({
      ...row,
      sleep_algorithm: selectedAlgorithmLabel || selectedAlgorithm || "not_selected",
    }));
    const csv = rowsToCsv(rows, ["metric", "label", "value", "sleep_algorithm"]);
    downloadBlob(csv, "actigraphy_summary_results.csv", "text/csv;charset=utf-8");
  };

  const exportMethods = () => {
    downloadJson(
      {
        analysisMode,
        selectedAlgorithm,
        selectedAlgorithmLabel,
        analysisConfig,
        qcWarnings,
        supportFileSummary,
        dataQuality,
        lightResults,
        exportedAt: new Date().toISOString(),
      },
      "actigraphy_methods_summary.json"
    );
  };

  const exportAllJson = () => {
    downloadJson(
      {
        results: summaryResults,
        lightResults,
        qcWarnings,
        analysisMode,
        selectedAlgorithm,
        selectedAlgorithmLabel,
        analysisConfig,
        supportFileSummary,
        dataQuality,
        exportedAt: new Date().toISOString(),
      },
      "actigraphy_results_export.json"
    );
  };

  const handleExport = (item) => {
    if (item.id === "csv_summary") {
      exportSummaryCsv();
      return;
    }
    exportAllJson();
  };

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
        Export the generated results as CSV or JSON. Both exports include the sleep-analysis algorithm used, support-file metadata, QC warnings, and analysis settings.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        {enabledExports.map((item) => (
          <button
            key={item.id}
            disabled={!resultsGenerated}
            onClick={() => handleExport(item)}
            style={{
              padding: 12,
              borderRadius: 12,
              background: "white",
              border: "1px solid #cbd5e1",
              cursor: resultsGenerated ? "pointer" : "not-allowed",
              opacity: resultsGenerated ? 1 : 0.5,
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
