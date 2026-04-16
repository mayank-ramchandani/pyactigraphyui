import React from "react";

export default function ExportPanel({
  title,
  exportRegistry,
  setCurrentStep,
  resultsGenerated,
}) {
  const enabledExports = exportRegistry.exports.filter((item) => item.enabled);

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
        Save processed values and generated visuals for later use.
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
            onClick={() => setCurrentStep("5")}
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