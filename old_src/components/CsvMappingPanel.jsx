import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
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
  const [detectedMapping, setDetectedMapping] = useState({});
  const [detectedInputType, setDetectedInputType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const availableColumns = useMemo(() => ["", ...columns], [columns]);

  useEffect(() => {
    let cancelled = false;

    async function fetchColumns() {
      if (!csvFile) {
        setColumns([]);
        setDetectedMapping({});
        setDetectedInputType("");
        return;
      }

      try {
        setLoading(true);
        setError("");

        const formData = new FormData();
        formData.append("file", csvFile);
        formData.append("csvSeparator", csvSeparator);

        const res = await fetch(buildApiUrl("api/tabular/columns"), {
          method: "POST",
          body: formData,
        });

        const text = await res.text();
        const data = text ? JSON.parse(text) : {};

        if (!res.ok) {
          throw new Error(data?.detail || "Failed to detect columns.");
        }

        if (cancelled) return;

        const detectedColumns = data?.columns || [];
        const mapping = data?.detected_mapping || {};

        setColumns(detectedColumns);
        setDetectedMapping(mapping);
        setDetectedInputType(data?.detected_input_type || "");

        setCsvMapping((prev) => ({
          timestamp_col: prev.timestamp_col || mapping.timestamp_col || "",
          time_col: prev.time_col || mapping.time_col || "",
          activity_col: prev.activity_col || mapping.activity_col || "",
          light_col: prev.light_col || mapping.light_col || "",
          temperature_col: prev.temperature_col || mapping.temperature_col || "",
          nonwear_col: prev.nonwear_col || mapping.nonwear_col || "",
        }));
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to detect columns.");
          setColumns([]);
          setDetectedMapping({});
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchColumns();

    return () => {
      cancelled = true;
    };
  }, [csvFile, csvSeparator, setCsvMapping]);

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
        Manual mapping is optional. The backend inspects the uploaded file and suggests the most likely timestamp, activity, and light columns.
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
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Current file</div>
        <div style={{ color: "#475569", fontSize: 14 }}>{csvFile?.name || "No file selected"}</div>
        {detectedInputType && (
          <div style={{ color: "#64748b", fontSize: 13, marginTop: 6 }}>
            Detected type: {detectedInputType}
          </div>
        )}
      </div>

      {loading && (
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: "#f8fafc",
            color: "#334155",
            fontSize: 14,
          }}
        >
          Detecting columns...
        </div>
      )}

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
            <option value="|">Pipe (|)</option>
          </select>
        </div>

        {[
          ["timestamp_col", "Timestamp column *"],
          ["time_col", "Optional time column"],
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
              style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", minWidth: 320 }}
            >
              {availableColumns.map((column) => (
                <option key={`${field}-${column || "none"}`} value={column}>
                  {column || "Not assigned"}
                </option>
              ))}
            </select>

            {detectedMapping[field] && (
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 6 }}>
                Suggested: {detectedMapping[field]}
              </div>
            )}
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