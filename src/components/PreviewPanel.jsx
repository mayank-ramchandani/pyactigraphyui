import React, { useMemo, useState } from "react";
import ActivityMappingPanel, { activityMappingLabel } from "./ActivityMappingPanel";
import { downloadBlob, downloadJson, previewToRows, rowsToCsv } from "../services/exportUtils";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Brush,
} from "recharts";


function formatTimestampTick(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatTooltipTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

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
  lightSourceAvailable = null,
  lightSourceMessage = "",
  activityMapping = "auto",
  setActivityMapping = () => {},
  onPreview,
}) {
  const [search, setSearch] = useState("");
  const [previewZoomKey, setPreviewZoomKey] = useState(0);

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
  const meanActivityWave = previewData?.mean_activity_wave || [];
  const timezoneInfo = previewData?.timezone_info || {};
  const lightAxisLabel =
    previewData?.light_summary?.y_axis_label ||
    previewData?.light_y_axis_label ||
    "Light intensity";
  const mappingFromResponse = previewData?.activity_mapping || {};
  const activityAxisLabel = mode === "activity"
    ? activityMappingLabel(mappingFromResponse.resolved || activityMapping)
    : "Activity";
  const yAxisLabel = mode === "light" ? lightAxisLabel : activityAxisLabel;
  const yValueLabel = mode === "light" ? lightAxisLabel : activityAxisLabel;


  const onExportPreviewCsv = () => {
    const rows = previewToRows(previewData, mode);
    downloadBlob(rowsToCsv(rows), `${mode}_preview.csv`, "text/csv;charset=utf-8");
  };

  const onExportPreviewJson = () => {
    downloadJson(previewData, `${mode}_preview.json`);
  };

  const canLoad =
    mode === "activity"
      ? Boolean(selectedPreviewFile)
      : lightSourceAvailable == null
        ? Boolean(selectedLightPreviewFile || selectedPreviewFile)
        : Boolean(lightSourceAvailable);

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
          ? "Load light preview from a separate light file, or use the selected actigraphy file when that reader exposes an embedded light channel."
          : "Load a full-recording activity preview from the selected actigraphy file."}
      </p>

      {mode === "light" && lightSourceMessage && (
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #fde68a",
            background: "#fffbeb",
            color: "#92400e",
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          {lightSourceMessage}
        </div>
      )}

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
                <option value="">
                  {lightSourceMessage ? "Select a supported separate light file" : "Use selected actigraphy file"}
                </option>
                {filteredLightFiles.map((file, idx) => (
                  <option key={`${file.name}-${idx}`} value={file.name}>
                    {file.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {mode === "activity" && (
          <ActivityMappingPanel
            value={activityMapping}
            onChange={setActivityMapping}
            compact
            context="preview"
          />
        )}

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
              ? mode === "light"
                ? "Inspecting Light Data..."
                : "Loading Preview..."
              : mode === "light"
              ? "Inspect & Load Light Preview"
              : "Load Activity Preview"}
          </button>
          {previewLoaded && previewData && (
            <>
              <button
                onClick={onExportPreviewCsv}
                style={{
                  marginLeft: 10,
                  padding: "10px 16px",
                  borderRadius: 12,
                  background: "white",
                  color: "#0f172a",
                  border: "1px solid #cbd5e1",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Export Preview CSV
              </button>
              <button
                onClick={onExportPreviewJson}
                style={{
                  marginLeft: 10,
                  padding: "10px 16px",
                  borderRadius: 12,
                  background: "white",
                  color: "#0f172a",
                  border: "1px solid #cbd5e1",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Export Preview JSON
              </button>
            </>
          )}
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
                    : previewData?.message || "No embedded light measurements were found."
                  : "Activity preview is available."}
              </div>
              <div
                style={{
                  marginTop: 12,
                  padding: 10,
                  borderRadius: 12,
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  color: "#1e3a8a",
                  fontSize: 13,
                  lineHeight: 1.45,
                }}
              >
                <strong>Timezone note:</strong>{" "}
                {timezoneInfo?.note ||
                  "pyActigraphy uses the timestamps available in the file/index. If the file does not include timezone-aware timestamps, confirm the device/export timezone before interpreting clock-time metrics."}
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
              {previewData?.message || "No embedded light measurements were found for this selection."}
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
                            {yValueLabel}
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
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
                  <div style={{ fontWeight: 700 }}>
                    {mode === "light" ? "Light Preview Plot" : "Activity Preview Plot"}
                  </div>
                  {points.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setPreviewZoomKey((value) => value + 1)}
                      style={{
                        padding: "7px 10px",
                        borderRadius: 10,
                        background: "white",
                        color: "#0f172a",
                        border: "1px solid #cbd5e1",
                        cursor: "pointer",
                        fontWeight: 700,
                      }}
                    >
                      Reset zoom
                    </button>
                  )}
                </div>

                {mode === "light" ? (
                  <div style={{ color: "#64748b", fontSize: 13, marginBottom: 10 }}>
                    X-axis: recording time. Drag the range selector under the plot to zoom into a specific time window.
                    <br />
                    Y-axis: {lightAxisLabel}
                    {previewData?.light_summary?.light_scale_note
                      ? ` — ${previewData.light_summary.light_scale_note}`
                      : ""}
                  </div>
                ) : (
                  <div style={{ color: "#64748b", fontSize: 13, marginBottom: 10 }}>
                    X-axis: recording time. Drag the range selector under the plot to zoom into a specific time window.
                  </div>
                )}

                {points.length === 0 ? (
                  <div style={{ color: "#64748b" }}>No preview points were returned.</div>
                ) : (
                  <div style={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer key={previewZoomKey} width="100%" height="100%">
                      <LineChart data={points} margin={{ top: 8, right: 24, left: 8, bottom: 48 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="timestamp"
                          tick={{ fontSize: 11 }}
                          minTickGap={40}
                          tickFormatter={formatTimestampTick}
                        />
                        <YAxis
                          width={88}
                          label={{
                            value: yAxisLabel,
                            angle: -90,
                            position: "insideLeft",
                            style: { textAnchor: "middle", fill: "#475569", fontSize: 12 },
                          }}
                        />
                        <Tooltip
                          formatter={(value) => [value, yValueLabel]}
                          labelFormatter={(label) => `Time: ${formatTooltipTimestamp(label)}`}
                        />
                        <Line
                          type="monotone"
                          dataKey={mode === "light" ? "light" : "activity"}
                          dot={false}
                          strokeWidth={2}
                          isAnimationActive={false}
                        />
                        <Brush dataKey="timestamp" height={26} travellerWidth={10} tickFormatter={formatTimestampTick} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {mode === "activity" && meanActivityWave.length > 0 && (
                <div
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: 16,
                    padding: 16,
                    background: "#f8fafc",
                    marginTop: 20,
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>
                    Mean 24-hour Activity Wave
                  </div>
                  <div style={{ color: "#64748b", fontSize: 14, marginBottom: 10 }}>
                    Average activity at each clock time across the entire recording window.
                  </div>
                  <div style={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={meanActivityWave}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" minTickGap={40} />
                        <YAxis />
                        <Tooltip
                          formatter={(value) => [value, "Mean activity"]}
                          labelFormatter={(label) => `Clock time: ${label}`}
                        />
                        <Line
                          type="monotone"
                          dataKey="mean_activity"
                          dot={false}
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
