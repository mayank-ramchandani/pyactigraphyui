import React, { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function formatValue(value) {
  if (value == null || Number.isNaN(value)) return "Not available";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
}

export default function PreviewPanel({
  title,
  mode = "activity",
  previewLoaded,
  previewLoading,
  previewError,
  previewData,
  actigraphyFiles = [],
  selectedPreviewFile,
  setSelectedPreviewFile,
  lightFiles = [],
  selectedLightPreviewFile = "",
  setSelectedLightPreviewFile = () => {},
  onPreview,
}) {
  const [search, setSearch] = useState("");

  const filteredActigraphyFiles = useMemo(() => {
    return actigraphyFiles.filter((file) =>
      file.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [actigraphyFiles, search]);

  const filteredLightFiles = useMemo(() => {
    return lightFiles.filter((file) =>
      file.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [lightFiles, search]);

  const activityPoints = previewData?.full_recording_preview || [];
  const lightPoints = previewData?.light_preview || [];
  const summary =
    mode === "light"
      ? previewData?.light_summary || {}
      : previewData?.summary || {};

  const detectedInputType = previewData?.detected_input_type || "unknown";
  const points = mode === "light" ? lightPoints : activityPoints;
  const hasLight = Boolean(previewData?.light_preview_available);

  const canLoad =
    mode === "activity"
      ? Boolean(selectedPreviewFile)
      : Boolean(selectedLightPreviewFile || selectedPreviewFile);

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
        {mode === "light"
          ? "Load light preview from a separate light file, or fall back to the selected actigraphy file if it already contains light."
          : "Load a full-recording activity preview from the selected actigraphy file."}
      </p>

      <div style={{ display: "grid", gap: 12, marginBottom: 20 }}>
        <input
          type="text"
          placeholder="Search files"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
          }}
        />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>
              {mode === "light" ? "Reference actigraphy file" : "Actigraphy file"}
            </div>
            <select
              value={selectedPreviewFile}
              onChange={(e) => setSelectedPreviewFile(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 10,
                border: "1px solid #cbd5e1",
                background: "white",
              }}
            >
              <option value="">Select a file</option>
              {filteredActigraphyFiles.map((file, idx) => (
                <option key={`${file.name}-${idx}`} value={file.name}>
                  {file.name}
                </option>
              ))}
            </select>
          </div>

          {mode === "light" && (
            <div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Optional separate light file</div>
              <select
                value={selectedLightPreviewFile}
                onChange={(e) => setSelectedLightPreviewFile(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 10,
                  border: "1px solid #cbd5e1",
                  background: "white",
                }}
              >
                <option value="">Use selected actigraphy file</option>
                {filteredLightFiles.map((file, idx) => (
                  <option key={`${file.name}-${idx}`} value={file.name}>
                    {file.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div>
          <button
            onClick={onPreview}
            disabled={!canLoad || previewLoading}
            style={{
              padding: "10px 16px",
              borderRadius: 12,
              background: canLoad && !previewLoading ? "#0f172a" : "#94a3b8",
              color: "white",
              border: "none",
              cursor: canLoad && !previewLoading ? "pointer" : "not-allowed",
              fontWeight: 600,
            }}
          >
            {previewLoading
              ? "Loading Preview..."
              : mode === "light"
              ? "Load Light Preview"
              : "Load Activity Preview"}
          </button>
        </div>
      </div>

      {previewError && (
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
          {previewError}
        </div>
      )}

      {previewLoaded && previewData && (
        <>
          <div
            style={{
              marginBottom: 20,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
            }}
          >
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 16,
                padding: 16,
                background: "#f8fafc",
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 10 }}>Preview Summary</div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <tbody>
                  <tr>
                    <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "left" }}>
                      detected_input_type
                    </td>
                    <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                      {detectedInputType}
                    </td>
                  </tr>
                  {Object.entries(summary).map(([key, value]) => (
                    <tr key={key}>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "left" }}>
                        {key}
                      </td>
                      <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                        {formatValue(value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 16,
                padding: 16,
                background: "#f8fafc",
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 10 }}>Status</div>
              <div style={{ color: "#475569", lineHeight: 1.6, fontSize: 14 }}>
                {mode === "light"
                  ? hasLight
                    ? "Light preview is available."
                    : "No light preview was returned for the selected file."
                  : "Activity preview is available."}
              </div>
            </div>
          </div>

          {mode === "light" && !hasLight ? (
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: 16,
                padding: 16,
                background: "#f8fafc",
                color: "#475569",
              }}
            >
              No light values were returned for this selection.
            </div>
          ) : (
            <>
              <div
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: 16,
                  padding: 16,
                  background: "#f8fafc",
                  marginBottom: 20,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 10 }}>
                  {mode === "light" ? "Light Sample" : "Activity Sample"}
                </div>

                {points.length === 0 ? (
                  <div style={{ color: "#64748b" }}>No preview points were returned.</div>
                ) : (
                  <div style={{ overflowX: "auto", maxHeight: 320, overflowY: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #cbd5e1" }}>
                            Timestamp
                          </th>
                          <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>
                            {mode === "light" ? "Light" : "Activity"}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {points.slice(0, 200).map((row, index) => (
                          <tr key={`${row.timestamp}-${index}`}>
                            <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>
                              {row.timestamp}
                            </td>
                            <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                              {formatValue(mode === "light" ? row.light : row.activity)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: 16,
                  padding: 16,
                  background: "#f8fafc",
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 10 }}>
                  {mode === "light" ? "Light Preview Plot" : "Activity Preview Plot"}
                </div>

                {points.length === 0 ? (
                  <div style={{ color: "#64748b" }}>No preview points were returned.</div>
                ) : (
                  <div style={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={points}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="timestamp" tick={false} minTickGap={40} />
                        <YAxis />
                        <Tooltip
                          formatter={(value) => [value, mode === "light" ? "Light" : "Activity"]}
                          labelFormatter={(label) => `Time: ${label}`}
                        />
                        <Line
                          type="monotone"
                          dataKey={mode === "light" ? "light" : "activity"}
                          dot={false}
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}