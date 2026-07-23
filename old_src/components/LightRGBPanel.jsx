import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Brush,
} from "recharts";
import { runBackgroundFileJob } from "../services/backgroundJobClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}



function formatTimestampTick(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatTimestampLabel(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const channelColors = {
  "RED LIGHT": "#ef4444",
  "GREEN LIGHT": "#22c55e",
  "BLUE LIGHT": "#3b82f6",
  "LIGHT": "#0f172a",
  "AMB LIGHT": "#a855f7",
  "IR LIGHT": "#f97316",
  "UVA LIGHT": "#06b6d4",
  "UVB LIGHT": "#eab308",
};

export default function LightRGBPanel({ lightFile, initialPayload = null }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState(null);
  const [visibleChannels, setVisibleChannels] = useState([]);
  const [resampleFreq, setResampleFreq] = useState("5min");
  const [zoomKey, setZoomKey] = useState(0);

  const channels = payload?.rgb_summary?.channels_used || [];
  const yAxisLabel = payload?.rgb_summary?.y_axis_label || "Light intensity";
  const yAxisNote = payload?.rgb_summary?.light_scale_note || "";

  useEffect(() => {
    let cancelled = false;

    async function loadRgbPreview() {
      if (!lightFile) {
        setPayload(null);
        setVisibleChannels([]);
        return;
      }

      try {
        setLoading(true);
        setError("");

        const canUseInitialPayload =
          initialPayload &&
          initialPayload.rgb_resample_freq === resampleFreq &&
          Array.isArray(initialPayload.rgb_preview);
        const data = canUseInitialPayload
          ? initialPayload
          : await runBackgroundFileJob({
              startUrl: buildApiUrl("api/jobs/light/rgb-preview"),
              statusBaseUrl: buildApiUrl("api/jobs"),
              file: lightFile,
              fields: { resampleFreq },
              jobPrefix: "light-rgb",
            });

        if (cancelled) return;

        setPayload(data);

        const defaultChannels =
          (data?.rgb_summary?.channels_used || []).filter((ch) =>
            ["RED LIGHT", "GREEN LIGHT", "BLUE LIGHT"].includes(ch)
          );

        setVisibleChannels(
          defaultChannels.length > 0
            ? defaultChannels
            : data?.rgb_summary?.channels_used || []
        );
        setZoomKey((value) => value + 1);
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load RGB light preview.");
          setPayload(null);
          setVisibleChannels([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadRgbPreview();

    return () => {
      cancelled = true;
    };
  }, [lightFile, resampleFreq, initialPayload]);

  const chartData = payload?.rgb_preview || [];

  const toggleChannel = (channel) => {
    setVisibleChannels((prev) =>
      prev.includes(channel)
        ? prev.filter((c) => c !== channel)
        : [...prev, channel]
    );
  };

  const summaryCards = useMemo(() => {
    return payload?.rgb_summary?.channel_stats || {};
  }, [payload]);

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 20,
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>RGB / Multichannel Light Visualization</h3>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Visualize red, green, blue, and other available light channels before running light metrics.
      </p>

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

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Resample frequency</div>
          <select
            value={resampleFreq}
            onChange={(e) => setResampleFreq(e.target.value)}
            style={{
              padding: "10px 12px",
              borderRadius: 10,
              border: "1px solid #cbd5e1",
              background: "white",
            }}
          >
            <option value="1min">1 min</option>
            <option value="5min">5 min</option>
            <option value="15min">15 min</option>
            <option value="30min">30 min</option>
            <option value="1h">1 hour</option>
          </select>
        </div>
      </div>

      {loading && <div style={{ marginBottom: 16 }}>Loading RGB light preview…</div>}

      {!loading && payload?.light_preview_available && (
        <>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Channels</div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {channels.map((channel) => {
                const active = visibleChannels.includes(channel);
                return (
                  <button
                    key={channel}
                    type="button"
                    onClick={() => toggleChannel(channel)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 999,
                      border: "1px solid #cbd5e1",
                      background: active ? "#0f172a" : "white",
                      color: active ? "white" : "#0f172a",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    {channel}
                  </button>
                );
              })}
            </div>
          </div>

          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 16,
              padding: 16,
              background: "#f8fafc",
              marginBottom: 16,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 8 }}>
              <div style={{ fontWeight: 700 }}>Light Channel Plot</div>
              {chartData.length > 0 && (
                <button
                  type="button"
                  onClick={() => setZoomKey((value) => value + 1)}
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
            <div style={{ color: "#64748b", fontSize: 13, marginBottom: 12 }}>
              X-axis: recording time. Drag the range selector under the plot to zoom into a specific time window.
              <br />
              Y-axis: {yAxisLabel}{yAxisNote ? ` — ${yAxisNote}` : ""}
            </div>

            {chartData.length === 0 ? (
              <div style={{ color: "#64748b" }}>No RGB preview points available.</div>
            ) : (
              <div style={{ width: "100%", height: 340 }}>
                <ResponsiveContainer key={zoomKey} width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 48 }}>
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
                    <Tooltip labelFormatter={(label) => `Time: ${formatTimestampLabel(label)}`} />
                    {visibleChannels.map((channel) => (
                      <Line
                        key={channel}
                        type="monotone"
                        dataKey={channel}
                        stroke={channelColors[channel] || "#334155"}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                    <Brush dataKey="timestamp" height={26} travellerWidth={10} tickFormatter={formatTimestampTick} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            {Object.entries(summaryCards).map(([channel, stats]) => (
              <div
                key={channel}
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: 16,
                  padding: 14,
                  background: "#f8fafc",
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 8 }}>{channel}</div>
                <div style={{ color: "#475569", fontSize: 14, lineHeight: 1.6 }}>
                  {stats?.units && <div>Units: {stats.units}</div>}
                  <div>Mean: {stats?.mean != null ? Number(stats.mean).toFixed(2) : "NA"}</div>
                  <div>Min: {stats?.min != null ? Number(stats.min).toFixed(2) : "NA"}</div>
                  <div>Max: {stats?.max != null ? Number(stats.max).toFixed(2) : "NA"}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!loading && payload && !payload.light_preview_available && (
        <div
          style={{
            border: "1px solid #e2e8f0",
            borderRadius: 16,
            padding: 16,
            background: "#f8fafc",
            color: "#475569",
          }}
        >
          No multichannel light preview was available for this file.
        </div>
      )}
    </div>
  );
}
