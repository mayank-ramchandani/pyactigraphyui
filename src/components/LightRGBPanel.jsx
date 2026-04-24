import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
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

export default function LightRGBPanel({ lightFile }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState(null);
  const [visibleChannels, setVisibleChannels] = useState([]);
  const [resampleFreq, setResampleFreq] = useState("5min");

  const channels = payload?.rgb_summary?.channels_used || [];

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

        const formData = new FormData();
        formData.append("file", lightFile);
        formData.append("resampleFreq", resampleFreq);

        const res = await fetch(buildApiUrl("api/light/rgb-preview"), {
          method: "POST",
          body: formData,
        });

        const text = await res.text();
        const data = text ? JSON.parse(text) : {};

        if (!res.ok) {
          throw new Error(data?.detail || "Failed to load RGB light preview.");
        }

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
  }, [lightFile, resampleFreq]);

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
            <div style={{ fontWeight: 700, marginBottom: 12 }}>Light Channel Plot</div>

            {chartData.length === 0 ? (
              <div style={{ color: "#64748b" }}>No RGB preview points available.</div>
            ) : (
              <div style={{ width: "100%", height: 340 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" tick={false} minTickGap={40} />
                    <YAxis />
                    <Tooltip />
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