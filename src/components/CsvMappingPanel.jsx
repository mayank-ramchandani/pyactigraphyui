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
  const [guidance, setGuidance] = useState("");
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
        setGuidance("");
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
        setGuidance(data?.guidance || "");

        setCsvMapping((prev) => ({
          timestamp_col: prev.timestamp_col || mapping.timestamp_col || "",
          time_col: prev.time_col || mapping.time_col || "",
          activity_col: prev.activity_col || mapping.activity_col || "",
          x_col: prev.x_col || mapping.x_col || "",
          y_col: prev.y_col || mapping.y_col || "",
          z_col: prev.z_col || mapping.z_col || "",
          acceleration_unit: prev.acceleration_unit || mapping.acceleration_unit || "",
          light_col: prev.light_col || mapping.light_col || "",
          temperature_col: prev.temperature_col || mapping.temperature_col || "",
          nonwear_col: prev.nonwear_col || mapping.nonwear_col || "",
        }));
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to detect columns.");
          setColumns([]);
          setDetectedMapping({});
          setGuidance("");
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

  const xyzMapped = Boolean(csvMapping.x_col && csvMapping.y_col && csvMapping.z_col && csvMapping.acceleration_unit);
  const isReady = Boolean(csvMapping.timestamp_col && (csvMapping.activity_col || xyzMapped));

  return (
    <div
      className="workflow-panel-centered"
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 20,
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>
        Manual mapping is optional. ActiLab identifies timestamps, activity/counts, optional sensor columns, and unambiguous raw X/Y/Z acceleration columns. Select all three axes and their units for a raw XYZ file; never treat X-axis acceleration as an activity-count column.
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
        {(detectedMapping.x_col && detectedMapping.y_col && detectedMapping.z_col) && (
          <div style={{ color: "#1d4ed8", fontSize: 13, marginTop: 6 }}>
            Raw XYZ detected: {detectedMapping.x_col}, {detectedMapping.y_col}, {detectedMapping.z_col}. {detectedMapping.acceleration_unit ? `Unit suggested: ${detectedMapping.acceleration_unit}.` : "Select acceleration units explicitly."}
          </div>
        )}
        {detectedInputType && (
          <div style={{ color: "#64748b", fontSize: 13, marginTop: 6 }}>
            Detected type: {detectedInputType}
          </div>
        )}
      </div>


      {guidance && (
        <div
          style={{
            marginBottom: 16,
            padding: 14,
            borderRadius: 12,
            border: "1px solid #fde68a",
            background: "#fffbeb",
            color: "#92400e",
            fontSize: 14,
            lineHeight: 1.55,
            textAlign: "center",
          }}
        >
          {guidance}
        </div>
      )}

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
          ["activity_col", "Activity or count column (OR use all 3 raw axes)"],
          ["x_col", "Raw X acceleration column"],
          ["y_col", "Raw Y acceleration column"],
          ["z_col", "Raw Z acceleration column"],
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

      <div style={{ padding: 13, border: "1px solid #bfdbfe", background: "#eff6ff", borderRadius: 12, marginTop: 15 }}>
        <label htmlFor="acceleration-unit" style={{ fontWeight: 700 }}>Raw X/Y/Z units <span role="img" tabIndex={0} aria-label="Units required for unambiguous acceleration interpretation" title="Only select this for raw X/Y/Z data. g, mg and m/s² cannot be safely inferred from unnamed columns. ActiLab computes epoch metrics without full static/temperature auto-calibration or GGIR HDCZA sleep detection." style={{ color: "#2563eb", cursor: "help" }}>ⓘ</span></label>
        <select id="acceleration-unit" value={csvMapping.acceleration_unit || ""} onChange={(e) => updateField("acceleration_unit", e.target.value)} style={{ marginTop: 8, display: "block", padding: "9px 12px", border: "1px solid #93c5fd", borderRadius: 9, width: "100%" }}>
          <option value="">Not specified (required for XYZ conversion)</option>
          <option value="g">g — gravitational units</option><option value="mg">mg — milligravity</option><option value="m_s2">m/s² — SI acceleration</option>
        </select>
        <p style={{ color: "#475569", fontSize: 12, lineHeight: 1.5, marginBottom: 0 }}>For count/activity CSVs, leave X/Y/Z empty. For raw XYZ, select X, Y, Z, and units; ActiLab uses the selected Step 3 metric and epoch length. No automatic gravity/temperature calibration is claimed.</p>
      </div>
      <div
        style={{
          marginTop: 20,
          display: "flex",
          justifyContent: "center",
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
          Continue to Initial QC
        </button>
      </div>
    </div>
  );
}