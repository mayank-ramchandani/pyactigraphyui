import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}

function renderResult(result) {
  if (!result) return null;

  if (result.kind === "scalar") {
    return (
      <div
        style={{
          padding: 16,
          borderRadius: 12,
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          fontSize: 18,
          fontWeight: 700,
        }}
      >
        {String(result.value)}
      </div>
    );
  }

  if (result.kind === "series") {
    return (
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #cbd5e1" }}>Index</th>
              <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>Value</th>
            </tr>
          </thead>
          <tbody>
            {result.index.map((label, idx) => (
              <tr key={`${label}-${idx}`}>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{label}</td>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>
                  {String(result.values[idx])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (result.kind === "dataframe") {
    return (
      <div style={{ overflowX: "auto", maxHeight: 420, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #cbd5e1" }}>Index</th>
              {result.columns.map((col) => (
                <th key={col} style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, rowIdx) => (
              <tr key={`${row.index}-${rowIdx}`}>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{row.index}</td>
                {row.values.map((value, colIdx) => (
                  <td
                    key={`${rowIdx}-${colIdx}`}
                    style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}
                  >
                    {String(value)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return null;
}

export default function LightMetricsPanel({ lightFile }) {
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState("");
  const [metricId, setMetricId] = useState("exposure_level");
  const [thresholdLux, setThresholdLux] = useState("");
  const [startTime, setStartTime] = useState("");
  const [stopTime, setStopTime] = useState("");
  const [bins, setBins] = useState("24h");
  const [agg, setAgg] = useState("mean");
  const [aggFuncs, setAggFuncs] = useState("mean,median,sum,std,min,max");
  const [outputFormat, setOutputFormat] = useState("minute");

  const [loadingChannels, setLoadingChannels] = useState(false);
  const [loadingResult, setLoadingResult] = useState(false);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState(null);

  const metricOptions = useMemo(
    () => [
      { id: "exposure_level", label: "Exposure Level" },
      { id: "summary_stats", label: "Summary Statistics" },
      { id: "tat", label: "Time Above Threshold" },
    ],
    []
  );

  useEffect(() => {
    let cancelled = false;

    async function loadChannels() {
      if (!lightFile) {
        setChannels([]);
        setSelectedChannel("");
        return;
      }

      try {
        setLoadingChannels(true);
        setError("");

        const formData = new FormData();
        formData.append("file", lightFile);

        const res = await fetch(buildApiUrl("api/light/channels"), {
          method: "POST",
          body: formData,
        });

        const text = await res.text();
        const data = text ? JSON.parse(text) : {};

        if (!res.ok) {
          throw new Error(data?.detail || "Failed to load light channels.");
        }

        if (cancelled) return;

        setChannels(data.channels || []);
        setSelectedChannel(data.default_channel || "");
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load light channels.");
          setChannels([]);
          setSelectedChannel("");
        }
      } finally {
        if (!cancelled) {
          setLoadingChannels(false);
        }
      }
    }

    loadChannels();

    return () => {
      cancelled = true;
    };
  }, [lightFile]);

  const onRunAnalysis = async () => {
    if (!lightFile) return;

    try {
      setLoadingResult(true);
      setError("");
      setPayload(null);

      const formData = new FormData();
      formData.append("file", lightFile);
      formData.append("metricId", metricId);
      formData.append("channel", selectedChannel);
      formData.append("thresholdLux", thresholdLux);
      formData.append("startTime", startTime);
      formData.append("stopTime", stopTime);
      formData.append("bins", bins);
      formData.append("agg", agg);
      formData.append("aggFuncs", aggFuncs);
      formData.append("outputFormat", outputFormat);

      const res = await fetch(buildApiUrl("api/light/analyze"), {
        method: "POST",
        body: formData,
      });

      const text = await res.text();
      const data = text ? JSON.parse(text) : {};

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to run light analysis.");
      }

      setPayload(data);
    } catch (err) {
      setError(err.message || "Failed to run light analysis.");
    } finally {
      setLoadingResult(false);
    }
  };

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 20,
        marginTop: 16,
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: 8 }}>Light Metrics</h3>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Native pyLight metrics for the selected light-capable file.
      </p>

      {loadingChannels && <div style={{ marginBottom: 12 }}>Loading light channels…</div>}

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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Metric</div>
          <select
            value={metricId}
            onChange={(e) => setMetricId(e.target.value)}
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          >
            {metricOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Channel</div>
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          >
            {channels.map((channel) => (
              <option key={channel} value={channel}>{channel}</option>
            ))}
          </select>
        </div>

        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Threshold (lux)</div>
          <input
            value={thresholdLux}
            onChange={(e) => setThresholdLux(e.target.value)}
            placeholder="Optional, e.g. 10 or 100"
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          />
        </div>

        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Aggregation</div>
          <select
            value={agg}
            onChange={(e) => setAgg(e.target.value)}
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          >
            {["mean", "median", "sum", "std", "min", "max"].map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>

        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Start time</div>
          <input
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            placeholder="HH:MM:SS"
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          />
        </div>

        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Stop time</div>
          <input
            value={stopTime}
            onChange={(e) => setStopTime(e.target.value)}
            placeholder="HH:MM:SS"
            style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
          />
        </div>

        {metricId === "summary_stats" && (
          <>
            <div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Bins</div>
              <input
                value={bins}
                onChange={(e) => setBins(e.target.value)}
                placeholder="24h"
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
              />
            </div>

            <div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Statistics</div>
              <input
                value={aggFuncs}
                onChange={(e) => setAggFuncs(e.target.value)}
                placeholder="mean,median,sum,std,min,max"
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
              />
            </div>
          </>
        )}

        {metricId === "tat" && (
          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Output format</div>
            <select
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value)}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
            >
              {["minute", "timedelta", "None"].map((fmt) => (
                <option key={fmt} value={fmt === "None" ? "" : fmt}>{fmt}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        <button
          onClick={onRunAnalysis}
          disabled={!lightFile || !selectedChannel || loadingResult}
          style={{
            padding: "10px 16px",
            borderRadius: 12,
            background: !lightFile || !selectedChannel || loadingResult ? "#94a3b8" : "#0f172a",
            color: "white",
            border: "none",
            cursor: !lightFile || !selectedChannel || loadingResult ? "not-allowed" : "pointer",
            fontWeight: 600,
          }}
        >
          {loadingResult ? "Running..." : "Run Light Analysis"}
        </button>
      </div>

      {payload && (
        <div style={{ marginTop: 20 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>
            Result: {payload.metric_id} · {payload.channel}
          </div>
          {renderResult(payload.result)}
        </div>
      )}
    </div>
  );
}