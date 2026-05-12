import React from "react";
import { downloadBlob, downloadJson, rowsToCsv, summaryResultsToRows } from "../services/exportUtils";
import { getMetricLabel } from "../services/configUtils";

export default function ExportPanel({
  title,
  exportRegistry,
  resultsGenerated,
  summaryResults = {},
  qcWarnings = [],
  metricRegistry,
  analysisConfig,
  selectedAlgorithm,
  analysisMode,
  supportFileSummary,
}) {
  const enabledExports = (exportRegistry?.exports ?? []).filter((item) => item.enabled);

  const exportSummaryCsv = () => {
    const rows = summaryResultsToRows(summaryResults, (metricId) => getMetricLabel(metricRegistry, metricId));
    const csv = rowsToCsv(rows, ["metric", "label", "value"]);
    downloadBlob(csv, "actigraphy_summary_results.csv", "text/csv;charset=utf-8");
  };

  const exportMethods = () => {
    downloadJson(
      {
        analysisMode,
        selectedAlgorithm,
        analysisConfig,
        qcWarnings,
        supportFileSummary,
        exportedAt: new Date().toISOString(),
      },
      "actigraphy_methods_summary.json"
    );
  };

  const exportAllJson = () => {
    downloadJson(
      {
        results: summaryResults,
        qcWarnings,
        analysisMode,
        selectedAlgorithm,
        analysisConfig,
        supportFileSummary,
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
    if (item.id === "methods_report" || item.id === "citation_summary") {
      exportMethods();
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
        Save result tables, QC information, and methods metadata from the generated workflow.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
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
