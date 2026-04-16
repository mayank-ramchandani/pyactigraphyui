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
  if (value == null || Number.isNaN(value)) {
    return "Not available";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  return String(value);
}

export default function PreviewPanel({
  title,
  previewCards,
  previewLoaded,
  previewLoading,
  previewError,
  previewData,
  actigraphyFiles,
  selectedPreviewFile,
  setSelectedPreviewFile,
  onPreview,
}) {
  const [search, setSearch] = useState("");

  const filteredFiles = useMemo(() => {
    return actigraphyFiles.filter((file) =>
      file.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [actigraphyFiles, search]);

  const previewPoints = previewData?.full_recording_preview || [];
  const summary = previewData?.summary || {};

  const visiblePreviewCards = (previewCards || []).filter(
    (card) => !["mask_overlay_preview", "sleep_diary_overlay_preview"].includes(card.id)
  );

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
        Load a full-recording preview before moving to cleaning, masking, sleep diary, or algorithm overlay steps.
      </p>

      <div style={{ display: "grid", gap: 12, marginBottom: 20 }}>
        <input
          type="text"
          placeholder="Search uploaded actigraphy files"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
          }}
        />

        <select
          value={selectedPreviewFile}
          onChange={(e) => setSelectedPreviewFile(e.target.value)}
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
            background: "white",
          }}
        >
          <option value="">Select a file to preview</option>
          {filteredFiles.map((file, idx) => (
            <option key={`${file.name}-${idx}`} value={file.name}>
              {file.name}
            </option>
          ))}
        </select>

        <div>
          <button
            onClick={onPreview}
            disabled={!selectedPreviewFile || previewLoading}
            style={{
              padding: "10px 16px",
              borderRadius: 12,
              background: selectedPreviewFile && !previewLoading ? "#0f172a" : "#94a3b8",
              color: "white",
              border: "none",
              cursor: selectedPreviewFile && !previewLoading ? "pointer" : "not-allowed",
              fontWeight: 600,
            }}
          >
            {previewLoading ? "Loading Preview..." : "Load Full Recording Preview"}
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
                Use the next workflow step for masking / cleaning options, and the step after that for sleep diary and start-stop file settings.
              </div>
            </div>
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
            <div style={{ fontWeight: 700, marginBottom: 10 }}>Full Recording Sample</div>
            {previewPoints.length === 0 ? (
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
                        Activity
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewPoints.slice(0, 200).map((row, index) => (
                      <tr key={`${row.timestamp}-${index}`}>
                        <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{row.timestamp}</td>
                        <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                          {formatValue(row.activity)}
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
  <div style={{ fontWeight: 700, marginBottom: 10 }}>Full Recording Preview Plot</div>

  {previewPoints.length === 0 ? (
    <div style={{ color: "#64748b" }}>No preview points were returned for this file.</div>
  ) : (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={previewPoints}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="timestamp"
            tick={false}
            minTickGap={40}
          />
          <YAxis />
          <Tooltip
            formatter={(value) => [value, "Activity"]}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Line
            type="monotone"
            dataKey="activity"
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
        {visiblePreviewCards.map((card) => (
          <div
            key={card.id}
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 16,
              padding: 16,
              background: "#f8fafc",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 6 }}>{card.title}</div>
            <div style={{ color: "#64748b", fontSize: 14, lineHeight: 1.5 }}>
              {card.description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}