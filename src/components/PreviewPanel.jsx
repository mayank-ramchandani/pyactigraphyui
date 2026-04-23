import React from "react";
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
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  return String(value);
}

export default function PreviewPanel({
  title,
  mode = "activity",
  previewLoaded,
  previewLoading,
  previewError,
  previewData,
  onPreview,
  onContinue,
}) {
  const summary = previewData?.summary || {};
  const detectedInputType = previewData?.detected_input_type || "unknown";
  const activityPoints = previewData?.full_recording_preview || [];
  const lightPoints = previewData?.light_preview || [];
  const hasLight = Boolean(previewData?.light_preview_available);

  const points = mode === "light" ? lightPoints : activityPoints;
  const yLabel = mode === "light" ? "Light" : "Activity";
  const previewTitle = mode === "light" ? "Light Preview" : "Activity Preview";

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
          ? "Inspect light data after the activity preview. If no light channel is available, this step will explain that."
          : "Load a full-recording activity preview before moving to cleaning, sleep diary, and start/stop pages."}
      </p>

      {mode === "activity" && (
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={onPreview}
            disabled={previewLoading}
            style={{
              padding: "10px 16px",
              borderRadius: 12,
              background: previewLoading ? "#94a3b8" : "#0f172a",
              color: "white",
              border: "none",
              cursor: previewLoading ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            {previewLoading ? "Loading Preview..." : "Load Preview"}
          </button>
        </div>
      )}

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
              <div style={{ fontWeight: 700, marginBottom: 10 }}>What happens next</div>
              <div style={{ color: "#475569", lineHeight: 1.6, fontSize: 14 }}>
                {mode === "light"
                  ? hasLight
                    ? "Light data were detected. Continue to cleaning and masking."
                    : "No light channel was detected in the loaded data. You can continue to cleaning and masking."
                  : "Continue to the light preview page, then proceed to masking and diary/start-stop configuration."}
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
                marginBottom: 20,
                color: "#475569",
              }}
            >
              No light preview is available for the currently loaded file(s).
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
                <div style={{ fontWeight: 700, marginBottom: 10 }}>{previewTitle} Sample</div>
                {points.length === 0 ? (
                  <div style={{ color: "#64748b" }}>No preview points were returned for this file.</div>
                ) : (
                  <div style={{ overflowX: "auto", maxHeight: 320, overflowY: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr>
                          <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #cbd5e1" }}>
                            Timestamp
                          </th>
                          <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>
                            {yLabel}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {points.slice(0, 200).map((row, index) => (
                          <tr key={`${row.timestamp}-${index}`}>
                            <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{row.timestamp}</td>
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
                  marginBottom: 20,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 10 }}>{previewTitle} Plot</div>

                {points.length === 0 ? (
                  <div style={{ color: "#64748b" }}>No preview points were returned for this file.</div>
                ) : (
                  <div style={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={points}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="timestamp" tick={false} minTickGap={40} />
                        <YAxis />
                        <Tooltip
                          formatter={(value) => [value, yLabel]}
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

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={onContinue}
              style={{
                padding: "10px 16px",
                borderRadius: 12,
                background: "#0f172a",
                color: "white",
                border: "none",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Continue
            </button>
          </div>
        </>
      )}
    </div>
  );
}