import React, { useEffect, useMemo, useState } from "react";

function parseCsvHeader(text) {
  const firstLine = text.split(/\r?\n/)[0] || "";
  return firstLine.split(",").map((item) => item.trim()).filter(Boolean);
}

export default function CsvMappingPanel({
  title,
  csvFile,
  csvMapping,
  setCsvMapping,
  csvSeparator,
  setCsvSeparator,
  onContinue,
}) {
  const [columns, setColumns] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function readHeader() {
      if (!csvFile) {
        setColumns([]);
        return;
      }

      try {
        const text = await csvFile.text();
        if (cancelled) return;
        const detectedColumns = parseCsvHeader(text);
        setColumns(detectedColumns);
        setError("");
      } catch (err) {
        if (!cancelled) {
          setError("Failed to read CSV header.");
          setColumns([]);
        }
      }
    }

    readHeader();

    return () => {
      cancelled = true;
    };
  }, [csvFile]);

  const availableColumns = useMemo(() => ["", ...columns], [columns]);

  const updateField = (field, value) => {
    setCsvMapping((prev) => ({
      ...prev,
      [field]: value || "",
    }));
  };

  const isReady = Boolean(csvMapping.timestamp_col && csvMapping.activity_col);

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
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>
        Map the uploaded CSV columns to the data fields used for preview and pyActigraphy processing.
        Timestamp and activity are required. Light and temperature are optional.
      </p>

      <div
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: 14,
          padding: 14,
          background: "#f8fafc",
          marginBottom: 16,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Current CSV</div>
        <div style={{ color: "#475569", fontSize: 14 }}>{csvFile?.name || "No CSV selected"}</div>
      </div>

      {error && (
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
          {error}
        </div>
      )}

      <div style={{ display: "grid", gap: 14 }}>
        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Separator</div>
          <select
            value={csvSeparator}
            onChange={(e) => setCsvSeparator(e.target.value)}
            style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          >
            <option value=",">Comma (,)</option>
            <option value=";">Semicolon (;)</option>
            <option value="\t">Tab</option>
          </select>
        </div>

        {[
          ["timestamp_col", "Timestamp column *"],
          ["activity_col", "Activity column *"],
          ["light_col", "Light column"],
          ["temperature_col", "Temperature column"],
          ["nonwear_col", "Non-wear / mask column"],
        ].map(([field, label]) => (
          <div key={field}>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>{label}</div>
            <select
              value={csvMapping[field] || ""}
              onChange={(e) => updateField(field, e.target.value)}
              style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", minWidth: 280 }}
            >
              {availableColumns.map((column) => (
                <option key={`${field}-${column || "none"}`} value={column}>
                  {column || "Not assigned"}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 20,
          display: "flex",
          justifyContent: "flex-end",
        }}
      >
        <button
          type="button"
          disabled={!isReady}
          onClick={onContinue}
          style={{
            padding: "10px 16px",
            borderRadius: 12,
            background: isReady ? "#0f172a" : "#94a3b8",
            color: "white",
            border: "none",
            cursor: isReady ? "pointer" : "not-allowed",
            fontWeight: 600,
          }}
        >
          Continue to Preview
        </button>
      </div>
    </div>
  );
}