import React, { useEffect, useMemo, useState } from "react";
import { downloadBlob, downloadJson, resultPayloadToRows, rowsToCsv } from "../services/exportUtils";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}

function formatValue(value) {
  if (value == null || Number.isNaN(value)) return "";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
}

function renderResult(result) {
  if (!result) return null;

  if (result.kind === "scalar") {
    return (
      <div style={{ padding: 16, borderRadius: 12, background: "#f8fafc", border: "1px solid #e2e8f0", fontSize: 18, fontWeight: 700 }}>
        {formatValue(result.value)}
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
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatValue(result.values[idx])}</td>
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
                <th key={col} style={{ textAlign: "right", padding: 8, borderBottom: "1px solid #cbd5e1" }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, rowIdx) => (
              <tr key={`${row.index}-${rowIdx}`}>
                <td style={{ padding: 8, borderTop: "1px solid #e2e8f0" }}>{row.index}</td>
                {row.values.map((value, colIdx) => (
                  <td key={`${rowIdx}-${colIdx}`} style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatValue(value)}</td>
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
  const [lmxLength, setLmxLength] = useState("5h");
  const [lowest, setLowest] = useState(true);
  const [binarizeMetric, setBinarizeMetric] = useState(false);

  const [truncateStart, setTruncateStart] = useState("");
  const [truncateStop, setTruncateStop] = useState("");
  const [dailyStartTime, setDailyStartTime] = useState("");
  const [dailyStopTime, setDailyStopTime] = useState("");
  const [manipResampleFreq, setManipResampleFreq] = useState("5min");
  const [manipBinarize, setManipBinarize] = useState(false);
  const [filterMethod, setFilterMethod] = useState("none");
  const [filterWindow, setFilterWindow] = useState("15min");

  const [loadingChannels, setLoadingChannels] = useState(false);
  const [loadingResult, setLoadingResult] = useState(false);
  const [loadingManipulation, setLoadingManipulation] = useState(false);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState(null);
  const [manipulationPayload, setManipulationPayload] = useState(null);

  const metricOptions = useMemo(
    () => [
      { id: "exposure_level", label: "Exposure Level" },
      { id: "summary_stats", label: "Summary Statistics" },
      { id: "tat", label: "Time Above Threshold" },
      { id: "tatp", label: "Time Above Threshold Per Day" },
      { id: "mlit", label: "Mean Light Timing Above Threshold" },
      { id: "l5", label: "L5: Least Bright 5 Hours" },
      { id: "m10", label: "M10: Most Bright 10 Hours" },
      { id: "ra", label: "Relative Amplitude" },
      { id: "is", label: "Interdaily Stability" },
      { id: "iv", label: "Intradaily Variability" },
      { id: "extremum_min", label: "Minimum Light Timing/Value" },
      { id: "extremum_max", label: "Maximum Light Timing/Value" },
      { id: "lmx", label: "Custom LMX Window" },
      { id: "vat", label: "Thresholded Light Series (VAT)" },
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

        const res = await fetch(buildApiUrl("api/light/channels"), { method: "POST", body: formData });
        const text = await res.text();
        const data = text ? JSON.parse(text) : {};

        if (!res.ok) throw new Error(data?.detail || "Failed to load light channels.");
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
        if (!cancelled) setLoadingChannels(false);
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
      formData.append("lmxLength", lmxLength);
      formData.append("lowest", String(lowest));
      formData.append("binarize", String(binarizeMetric));

      const res = await fetch(buildApiUrl("api/light/analyze"), { method: "POST", body: formData });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};

      if (!res.ok) throw new Error(data?.detail || "Failed to run light analysis.");
      setPayload(data);
    } catch (err) {
      setError(err.message || "Failed to run light analysis.");
    } finally {
      setLoadingResult(false);
    }
  };

  const onRunManipulation = async () => {
    if (!lightFile) return;

    try {
      setLoadingManipulation(true);
      setError("");
      setManipulationPayload(null);

      const formData = new FormData();
      formData.append("file", lightFile);
      formData.append("channels", selectedChannel);
      formData.append("truncateStart", truncateStart);
      formData.append("truncateStop", truncateStop);
      formData.append("dailyStartTime", dailyStartTime);
      formData.append("dailyStopTime", dailyStopTime);
      formData.append("resampleFreq", manipResampleFreq);
      formData.append("binarize", String(manipBinarize));
      formData.append("thresholdLux", thresholdLux);
      formData.append("filterMethod", filterMethod);
      formData.append("filterWindow", filterWindow);

      const res = await fetch(buildApiUrl("api/light/manipulate"), { method: "POST", body: formData });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};

      if (!res.ok) throw new Error(data?.detail || "Failed to manipulate light data.");
      setManipulationPayload(data);
    } catch (err) {
      setError(err.message || "Failed to manipulate light data.");
    } finally {
      setLoadingManipulation(false);
    }
  };

  const exportLightCsv = () => {
    if (!payload?.result) return;
    downloadBlob(rowsToCsv(resultPayloadToRows(payload.result)), `light_${metricId}_${selectedChannel || "channel"}.csv`, "text/csv;charset=utf-8");
  };

  const exportLightJson = () => {
    if (payload) downloadJson(payload, `light_${metricId}_${selectedChannel || "channel"}.json`);
  };

  const exportManipulationCsv = () => {
    if (!manipulationPayload?.preview) return;
    downloadBlob(rowsToCsv(manipulationPayload.preview), `light_manipulated_${selectedChannel || "channel"}.csv`, "text/csv;charset=utf-8");
  };

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>5. Light Analysis & Manipulation</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Run pyLight-style metrics and create manipulated previews using masking, truncation, resampling, binarization, and filtering.
      </p>

      {loadingChannels && <div style={{ marginBottom: 12 }}>Loading light channels…</div>}

      {error && (
        <div style={{ marginBottom: 16, padding: 12, borderRadius: 12, border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", fontSize: 14 }}>
          {error}
        </div>
      )}

      <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Light Metrics</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Metric</div>
            <select value={metricId} onChange={(e) => setMetricId(e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
              {metricOptions.map((opt) => <option key={opt.id} value={opt.id}>{opt.label}</option>)}
            </select>
          </div>

          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Channel</div>
            <select value={selectedChannel} onChange={(e) => setSelectedChannel(e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
              {channels.map((channel) => <option key={channel} value={channel}>{channel}</option>)}
            </select>
          </div>

          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Threshold (lux)</div>
            <input value={thresholdLux} onChange={(e) => setThresholdLux(e.target.value)} placeholder="Optional, required for MLiT/VAT/binarization" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </div>

          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Aggregation</div>
            <select value={agg} onChange={(e) => setAgg(e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
              {["mean", "median", "sum", "std", "min", "max"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>

          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Start time</div>
            <input value={startTime} onChange={(e) => setStartTime(e.target.value)} placeholder="HH:MM:SS" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </div>

          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Stop time</div>
            <input value={stopTime} onChange={(e) => setStopTime(e.target.value)} placeholder="HH:MM:SS" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </div>

          {metricId === "summary_stats" && (
            <>
              <div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Bins</div>
                <input value={bins} onChange={(e) => setBins(e.target.value)} placeholder="24h" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
              </div>
              <div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Statistics</div>
                <input value={aggFuncs} onChange={(e) => setAggFuncs(e.target.value)} placeholder="mean,median,sum,std,min,max" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
              </div>
            </>
          )}

          {["tat", "tatp"].includes(metricId) && (
            <div>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>Output format</div>
              <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
                {["minute", "timedelta", "None"].map((fmt) => <option key={fmt} value={fmt === "None" ? "" : fmt}>{fmt}</option>)}
              </select>
            </div>
          )}

          {metricId === "lmx" && (
            <>
              <div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>LMX length</div>
                <input value={lmxLength} onChange={(e) => setLmxLength(e.target.value)} placeholder="5h or 10h" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
              </div>
              <label style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 28 }}>
                <input type="checkbox" checked={lowest} onChange={(e) => setLowest(e.target.checked)} />
                Least bright window
              </label>
            </>
          )}

          {["is", "iv"].includes(metricId) && (
            <label style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 28 }}>
              <input type="checkbox" checked={binarizeMetric} onChange={(e) => setBinarizeMetric(e.target.checked)} />
              Binarize before metric
            </label>
          )}
        </div>

        <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button onClick={onRunAnalysis} disabled={!lightFile || !selectedChannel || loadingResult} style={{ padding: "10px 16px", borderRadius: 12, background: !lightFile || !selectedChannel || loadingResult ? "#94a3b8" : "#0f172a", color: "white", border: "none", cursor: !lightFile || !selectedChannel || loadingResult ? "not-allowed" : "pointer", fontWeight: 600 }}>
            {loadingResult ? "Running..." : "Run Light Analysis"}
          </button>
          <button onClick={exportLightCsv} disabled={!payload} style={{ padding: "10px 16px", borderRadius: 12, background: "white", border: "1px solid #cbd5e1", cursor: payload ? "pointer" : "not-allowed", opacity: payload ? 1 : 0.5 }}>
            Export Light CSV
          </button>
          <button onClick={exportLightJson} disabled={!payload} style={{ padding: "10px 16px", borderRadius: 12, background: "white", border: "1px solid #cbd5e1", cursor: payload ? "pointer" : "not-allowed", opacity: payload ? 1 : 0.5 }}>
            Export Light JSON
          </button>
        </div>

        {payload && (
          <div style={{ marginTop: 20 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Result: {payload.metric_id} · {payload.channel}</div>
            {renderResult(payload.result)}
          </div>
        )}
      </div>

      <div style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc" }}>
        <h3 style={{ marginTop: 0 }}>Light Data Manipulation</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
          <input value={truncateStart} onChange={(e) => setTruncateStart(e.target.value)} placeholder="Truncate start: YYYY-MM-DD HH:MM:SS" style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          <input value={truncateStop} onChange={(e) => setTruncateStop(e.target.value)} placeholder="Truncate stop: YYYY-MM-DD HH:MM:SS" style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          <input value={dailyStartTime} onChange={(e) => setDailyStartTime(e.target.value)} placeholder="Daily mask start: HH:MM:SS" style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          <input value={dailyStopTime} onChange={(e) => setDailyStopTime(e.target.value)} placeholder="Daily mask stop: HH:MM:SS" style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          <input value={manipResampleFreq} onChange={(e) => setManipResampleFreq(e.target.value)} placeholder="Resample freq, e.g. 5min" style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          <input value={filterWindow} onChange={(e) => setFilterWindow(e.target.value)} placeholder="Filter window, e.g. 15min" style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          <select value={filterMethod} onChange={(e) => setFilterMethod(e.target.value)} style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
            <option value="none">No filter</option>
            <option value="mean">Rolling mean</option>
            <option value="median">Rolling median</option>
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input type="checkbox" checked={manipBinarize} onChange={(e) => setManipBinarize(e.target.checked)} />
            Binarize using threshold above
          </label>
        </div>

        <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button onClick={onRunManipulation} disabled={!lightFile || !selectedChannel || loadingManipulation} style={{ padding: "10px 16px", borderRadius: 12, background: !lightFile || !selectedChannel || loadingManipulation ? "#94a3b8" : "#0f172a", color: "white", border: "none", cursor: !lightFile || !selectedChannel || loadingManipulation ? "not-allowed" : "pointer", fontWeight: 600 }}>
            {loadingManipulation ? "Applying..." : "Apply Light Manipulation"}
          </button>
          <button onClick={exportManipulationCsv} disabled={!manipulationPayload} style={{ padding: "10px 16px", borderRadius: 12, background: "white", border: "1px solid #cbd5e1", cursor: manipulationPayload ? "pointer" : "not-allowed", opacity: manipulationPayload ? 1 : 0.5 }}>
            Export Manipulated Light CSV
          </button>
        </div>

        {manipulationPayload && (
          <div style={{ marginTop: 20 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Manipulated light preview</div>
            <div style={{ color: "#475569", marginBottom: 10, fontSize: 14 }}>
              Rows: {manipulationPayload.summary?.rows} / original {manipulationPayload.summary?.original_rows}; Start: {manipulationPayload.summary?.start}; End: {manipulationPayload.summary?.end}
            </div>
            <div style={{ overflowX: "auto", maxHeight: 300, overflowY: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {Object.keys(manipulationPayload.preview?.[0] || {}).map((key) => (
                      <th key={key} style={{ padding: 8, borderBottom: "1px solid #cbd5e1", textAlign: key === "timestamp" ? "left" : "right" }}>{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(manipulationPayload.preview || []).slice(0, 200).map((row, idx) => (
                    <tr key={`${row.timestamp}-${idx}`}>
                      {Object.entries(row).map(([key, value]) => (
                        <td key={key} style={{ padding: 8, borderTop: "1px solid #e2e8f0", textAlign: key === "timestamp" ? "left" : "right" }}>{formatValue(value)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
