import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}

function cardStyle(selected) {
  return {
    padding: 12,
    borderRadius: 14,
    border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
    background: selected ? "#0f172a" : "white",
    color: selected ? "white" : "#0f172a",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
    minHeight: 130,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  };
}

function toLocalDatetimeValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDisplayDatetime(value) {
  const local = toLocalDatetimeValue(value);
  return local ? local.replace("T", " ") : "Not detected";
}

function getPreviewBounds(previewData) {
  const points = previewData?.full_recording_preview || previewData?.light_preview || [];
  const summary = previewData?.summary || previewData?.light_summary || {};
  const start = summary.start || points[0]?.timestamp || points[0]?.time || "";
  const stop = summary.end || points[points.length - 1]?.timestamp || points[points.length - 1]?.time || "";
  return {
    start,
    stop,
    minLocal: toLocalDatetimeValue(start),
    maxLocal: toLocalDatetimeValue(stop),
  };
}

function normalizeDatetimeInput(value, bounds) {
  if (!value) return "";
  if (String(value).includes("T")) return value;
  const base = bounds?.minLocal?.slice(0, 10) || new Date().toISOString().slice(0, 10);
  return `${base}T${String(value).slice(0, 5)}`;
}

function validateDateWindow(start, stop, bounds) {
  if (!start || !stop) return "";
  const startDate = new Date(start);
  const stopDate = new Date(stop);
  const minDate = bounds?.start ? new Date(bounds.start) : null;
  const maxDate = bounds?.stop ? new Date(bounds.stop) : null;
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(stopDate.getTime())) return "Choose valid start and stop date/times.";
  if (stopDate <= startDate) return "Stop date/time must be after start date/time.";
  if (minDate && !Number.isNaN(minDate.getTime()) && startDate < minDate) return "Start date/time must be within the detected recording window.";
  if (maxDate && !Number.isNaN(maxDate.getTime()) && stopDate > maxDate) return "Stop date/time must be within the detected recording window.";
  return "";
}

const THRESHOLD_PRESETS = [
  { value: "", label: "No threshold / metric default" },
  { value: "1", label: "1 lux — very dim light" },
  { value: "10", label: "10 lux — dim indoor threshold" },
  { value: "50", label: "50 lux — low indoor light" },
  { value: "100", label: "100 lux — typical indoor bright-light cutoff" },
  { value: "250", label: "250 lux — moderate bright light" },
  { value: "500", label: "500 lux — bright indoor / outdoor exposure" },
  { value: "1000", label: "1000 lux — strong bright light" },
  { value: "2500", label: "2500 lux — daylight exposure" },
  { value: "custom", label: "Custom threshold…" },
];

const SUMMARY_BIN_OPTIONS = ["1h", "2h", "6h", "12h", "24h", "7D"];
const LMX_LENGTH_OPTIONS = ["1h", "2h", "5h", "10h", "12h"];

export const LIGHT_METRIC_DEFINITIONS = {
  exposure_level: {
    id: "exposure_level",
    label: "Exposure Level",
    shortLabel: "Exposure",
    summary: "Average, median, sum, or extreme light exposure within an optional clock-time window.",
    description:
      "Computes light exposure level for the selected channel. Use the aggregation setting to choose mean, median, sum, standard deviation, minimum, or maximum.",
  },
  summary_stats: {
    id: "summary_stats",
    label: "Summary Statistics",
    shortLabel: "Summary",
    summary: "Light summary statistics per time bin, such as mean, median, sum, standard deviation, min, and max.",
    description:
      "Groups light data into a selected bin length, such as 24h, and calculates one or more summary functions.",
  },
  tat: {
    id: "tat",
    label: "Time Above Threshold",
    shortLabel: "TAT",
    summary: "Total time spent above a selected lux threshold.",
    description:
      "Calculates the amount of time the selected light channel is above the threshold. Useful for bright-light exposure summaries.",
  },
  tatp: {
    id: "tatp",
    label: "Time Above Threshold Per Day",
    shortLabel: "TATp",
    summary: "Daily time spent above a selected lux threshold.",
    description:
      "Calculates time above threshold separately per day, which is useful for comparing daily bright-light exposure patterns.",
  },
  mlit: {
    id: "mlit",
    label: "Mean Light Timing Above Threshold",
    shortLabel: "MLiT",
    summary: "Average timing of light exposure above the selected threshold.",
    description:
      "Estimates the mean timing of above-threshold light exposure. Requires a lux threshold such as 10, 100, or 500.",
  },
  vat: {
    id: "vat",
    label: "Thresholded Light Series",
    shortLabel: "VAT",
    summary: "Creates a thresholded light exposure series using the selected lux threshold.",
    description:
      "Returns a binary/thresholded light exposure series. This is useful for inspecting when exposure exceeds the threshold.",
  },
  l5: {
    id: "l5",
    label: "L5: Least Bright 5 Hours",
    shortLabel: "L5",
    summary: "Least bright consolidated 5-hour window.",
    description:
      "Finds the least bright 5-hour period in the light recording for the selected channel.",
  },
  m10: {
    id: "m10",
    label: "M10: Most Bright 10 Hours",
    shortLabel: "M10",
    summary: "Most bright consolidated 10-hour window.",
    description:
      "Finds the most bright 10-hour period in the light recording for the selected channel.",
  },
  ra: {
    id: "ra",
    label: "Light Relative Amplitude",
    shortLabel: "Light RA",
    summary: "Relative amplitude between bright and dim light windows.",
    description:
      "Computes a light-based relative amplitude using M10 and L5 values for the selected channel.",
  },
  is: {
    id: "is",
    label: "Light Interdaily Stability",
    shortLabel: "Light IS",
    summary: "Day-to-day stability of the light exposure rhythm.",
    description:
      "Calculates interdaily stability for light exposure. Optional binarization can be applied before the metric.",
  },
  iv: {
    id: "iv",
    label: "Light Intradaily Variability",
    shortLabel: "Light IV",
    summary: "Fragmentation or transitions in the light exposure rhythm.",
    description:
      "Calculates intradaily variability for light exposure. Optional binarization can be applied before the metric.",
  },
  extremum_min: {
    id: "extremum_min",
    label: "Minimum Light Timing / Value",
    shortLabel: "Min light",
    summary: "Minimum light exposure timing and value.",
    description:
      "Finds the minimum light exposure point or window returned by the pyActigraphy light recording.",
  },
  extremum_max: {
    id: "extremum_max",
    label: "Maximum Light Timing / Value",
    shortLabel: "Max light",
    summary: "Maximum light exposure point or window returned by the pyActigraphy light recording.",
    description:
      "Finds the maximum light exposure point or window returned by the pyActigraphy light recording.",
  },
  lmx: {
    id: "lmx",
    label: "Custom LMX Window",
    shortLabel: "LMX",
    summary: "Custom least-bright or most-bright light window length.",
    description:
      "Runs a custom LMX window, such as 5h or 10h, and lets the user choose least-bright or most-bright mode.",
  },
};

const LIGHT_METRIC_GROUPS = [
  {
    id: "light_exposure_group",
    label: "Light Exposure Summaries",
    description:
      "General light exposure level and time-binned summaries. These are the most useful starting point for light data quality and descriptive reporting.",
    metrics: ["exposure_level", "summary_stats"],
  },
  {
    id: "threshold_timing_group",
    label: "Threshold & Timing Metrics",
    description:
      "Metrics based on a lux threshold, including time above threshold and the timing of above-threshold exposure.",
    metrics: ["tat", "tatp", "mlit", "vat"],
  },
  {
    id: "light_rhythm_group",
    label: "Light Rhythm Metrics",
    description:
      "Non-parametric rhythm metrics computed on light, including L5, M10, relative amplitude, stability, and variability.",
    metrics: ["l5", "m10", "ra", "is", "iv", "lmx"],
  },
  {
    id: "light_extrema_group",
    label: "Light Extremes",
    description:
      "Minimum and maximum light timing/value outputs for identifying extreme exposure periods.",
    metrics: ["extremum_min", "extremum_max"],
  },
];

const DEFAULT_LIGHT_SETTINGS = {
  channel: "",
  thresholdLux: "",
  startTime: "",
  stopTime: "",
  bins: "24h",
  agg: "mean",
  aggFuncs: "mean,median,sum,std,min,max",
  outputFormat: "minute",
  lmxLength: "5h",
  lowest: true,
  binarizeMetric: false,
};

function Section({ title, description, expanded, onToggle, summary, children }) {
  return (
    <div style={{ marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, overflow: "hidden", background: "#f8fafc" }}>
      <button type="button" onClick={onToggle} style={{ width: "100%", padding: 14, border: "none", background: "white", cursor: "pointer", textAlign: "left" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16 }}>{expanded ? "▾" : "▸"} {title}</div>
            {description && <div style={{ marginTop: 4, color: "#64748b", fontSize: 14, lineHeight: 1.45 }}>{description}</div>}
          </div>
          {summary && <div style={{ color: "#475569", fontSize: 13, whiteSpace: "nowrap", marginTop: 2 }}>{summary}</div>}
        </div>
      </button>
      {expanded && <div style={{ padding: 14, borderTop: "1px solid #e2e8f0" }}>{children}</div>}
    </div>
  );
}

export default function LightMetricsPanel({
  lightFile,
  selectedLightMetrics = [],
  setSelectedLightMetrics = () => {},
  lightMetricSettings = {},
  setLightMetricSettings = () => {},
  previewData = null,
}) {
  const [channels, setChannels] = useState([]);
  const [loadingChannels, setLoadingChannels] = useState(false);
  const [error, setError] = useState("");
  const [expandedMetric, setExpandedMetric] = useState(null);
  const [expandedGroup, setExpandedGroup] = useState("light_exposure_group");
  const [expandedSettings, setExpandedSettings] = useState({
    basic: false,
    threshold: false,
    advanced: false,
  });
  const [thresholdInputMode, setThresholdInputMode] = useState("preset");

  const settings = { ...DEFAULT_LIGHT_SETTINGS, ...(lightMetricSettings || {}) };
  const bounds = useMemo(() => getPreviewBounds(previewData), [previewData]);
  const selectedSet = useMemo(() => new Set(selectedLightMetrics || []), [selectedLightMetrics]);
  const hasThresholdMetrics = selectedLightMetrics.some((metricId) => ["tat", "tatp", "mlit", "vat", "is", "iv"].includes(metricId));
  const thresholdMatchesPreset = THRESHOLD_PRESETS.some((item) => item.value === String(settings.thresholdLux || "") && item.value !== "custom");
  const thresholdPreset = thresholdInputMode === "custom" || !thresholdMatchesPreset ? "custom" : String(settings.thresholdLux || "");
  const startDateTimeValue = normalizeDatetimeInput(settings.startTime, bounds);
  const stopDateTimeValue = normalizeDatetimeInput(settings.stopTime, bounds);
  const windowError = validateDateWindow(startDateTimeValue, stopDateTimeValue, bounds);

  useEffect(() => {
    let cancelled = false;

    async function loadChannels() {
      if (!lightFile) {
        setChannels([]);
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

        const nextChannels = data.channels || [];
        setChannels(nextChannels);
        if (!settings.channel && data.default_channel) {
          setLightMetricSettings((prev) => ({ ...DEFAULT_LIGHT_SETTINGS, ...(prev || {}), channel: data.default_channel }));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load light channels.");
          setChannels([]);
        }
      } finally {
        if (!cancelled) setLoadingChannels(false);
      }
    }

    loadChannels();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lightFile]);

  const updateSetting = (name, value) => {
    setLightMetricSettings((prev) => ({ ...DEFAULT_LIGHT_SETTINGS, ...(prev || {}), [name]: value }));
  };

  const toggleMetric = (metricId) => {
    setSelectedLightMetrics((prev) =>
      prev.includes(metricId) ? prev.filter((item) => item !== metricId) : [...prev, metricId]
    );
  };

  const toggleGroup = (metricIds) => {
    const allSelected = metricIds.every((id) => selectedSet.has(id));
    setSelectedLightMetrics((prev) => {
      if (allSelected) return prev.filter((id) => !metricIds.includes(id));
      return Array.from(new Set([...prev, ...metricIds]));
    });
  };

  const toggleSettingsSection = (key) => {
    setExpandedSettings((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>Light Analysis Setup</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Select light metrics in the same grouped workflow as activity and sleep metrics. Optional settings stay collapsed until the user opens them.
      </p>

      {!lightFile && (
        <div style={{ padding: 14, borderRadius: 14, border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e", marginBottom: 16 }}>
          No separate or embedded light file is selected. Light metrics can be selected, but generation will be skipped unless a light-capable file is available.
        </div>
      )}

      {loadingChannels && <div style={{ marginBottom: 12 }}>Loading light channels…</div>}
      {error && (
        <div style={{ marginBottom: 16, padding: 12, borderRadius: 12, border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", fontSize: 14 }}>
          {error}
        </div>
      )}

      <div style={{ border: "1px solid #dbeafe", borderRadius: 14, background: "#eff6ff", color: "#1e3a8a", padding: 14, marginBottom: 16, fontSize: 14, lineHeight: 1.55 }}>
        Recording window detected for light calendar inputs: <strong>{formatDisplayDatetime(bounds.start)}</strong> to <strong>{formatDisplayDatetime(bounds.stop)}</strong>.
      </div>

      <Section
        title="Basic light settings"
        description="Choose the light channel and simple aggregation options. Leave these collapsed to use pyActigraphy/default values."
        expanded={expandedSettings.basic}
        onToggle={() => toggleSettingsSection("basic")}
        summary={`${settings.channel || "Auto channel"} · ${settings.agg || "mean"}`}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Light channel</div>
            <select value={settings.channel} onChange={(e) => updateSetting("channel", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              <option value="">Auto/default channel</option>
              {channels.map((channel) => <option key={channel} value={channel}>{channel}</option>)}
            </select>
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Aggregation</div>
            <select value={settings.agg} onChange={(e) => updateSetting("agg", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              {["mean", "median", "sum", "std", "min", "max"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>TAT output format</div>
            <select value={settings.outputFormat} onChange={(e) => updateSetting("outputFormat", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              <option value="minute">minute</option>
              <option value="timedelta">timedelta</option>
              <option value="">None/default</option>
            </select>
          </label>
        </div>
      </Section>

      <Section
        title="Threshold and time-window options"
        description="Use these for TAT, TATp, MLiT, VAT, and optional light IS/IV binarization thresholds."
        expanded={expandedSettings.threshold}
        onToggle={() => toggleSettingsSection("threshold")}
        summary={`${settings.thresholdLux ? `${settings.thresholdLux} lux` : "No threshold"}${hasThresholdMetrics ? " · threshold metric selected" : ""}`}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Threshold preset</div>
            <select value={thresholdPreset} onChange={(e) => {
              if (e.target.value === "custom") {
                setThresholdInputMode("custom");
                updateSetting("thresholdLux", settings.thresholdLux || "100");
              } else {
                setThresholdInputMode("preset");
                updateSetting("thresholdLux", e.target.value);
              }
            }} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              {THRESHOLD_PRESETS.map((item) => <option key={item.value || "none"} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          {thresholdPreset === "custom" && (
            <label>
              <div style={{ fontWeight: 600, marginBottom: 5 }}>Custom threshold lux</div>
              <input type="number" min="0" max="200000" step="1" value={settings.thresholdLux} onChange={(e) => updateSetting("thresholdLux", e.target.value)} placeholder="0–200000" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
            </label>
          )}
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Start date/time</div>
            <input type="datetime-local" value={startDateTimeValue} min={bounds.minLocal || undefined} max={bounds.maxLocal || undefined} onChange={(e) => updateSetting("startTime", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Stop date/time</div>
            <input type="datetime-local" value={stopDateTimeValue} min={bounds.minLocal || undefined} max={bounds.maxLocal || undefined} onChange={(e) => updateSetting("stopTime", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
        </div>
        {windowError && <div style={{ color: "#b91c1c", marginTop: 10, fontSize: 14 }}>{windowError}</div>}
        <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginTop: 10 }}>
          The calendar fields are bounded by the detected recording start/end. Leave them blank when you want the metric to use the full recording/default daily window.
        </div>
      </Section>

      {LIGHT_METRIC_GROUPS.map((group) => {
        const selectedCount = group.metrics.filter((metricId) => selectedSet.has(metricId)).length;
        const allSelected = selectedCount === group.metrics.length;
        const isExpanded = expandedGroup === group.id;

        return (
          <div key={group.id} style={{ marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, overflow: "hidden", background: "#f8fafc" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10, alignItems: "center", padding: 14, background: "white", borderBottom: isExpanded ? "1px solid #e2e8f0" : "none" }}>
              <button type="button" onClick={() => setExpandedGroup(isExpanded ? null : group.id)} style={{ padding: 0, border: "none", background: "transparent", textAlign: "left", cursor: "pointer" }}>
                <div style={{ fontWeight: 800, fontSize: 17 }}>{isExpanded ? "▾" : "▸"} {group.label}</div>
                <div style={{ color: "#64748b", fontSize: 14, marginTop: 4, lineHeight: 1.45 }}>{group.description}</div>
              </button>
              <div style={{ color: "#475569", fontSize: 14 }}>{selectedCount}/{group.metrics.length} selected</div>
              <button type="button" onClick={() => toggleGroup(group.metrics)} style={{ padding: "9px 12px", borderRadius: 10, border: allSelected ? "1px solid #0f172a" : "1px solid #cbd5e1", background: allSelected ? "#0f172a" : "white", color: allSelected ? "white" : "#0f172a", cursor: "pointer", fontWeight: 700 }}>
                {allSelected ? "Clear group" : "Select group"}
              </button>
            </div>

            {isExpanded && (
              <div style={{ padding: 14 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
                  {group.metrics.map((metricId) => {
                    const metric = LIGHT_METRIC_DEFINITIONS[metricId];
                    const isSelected = selectedSet.has(metricId);
                    return (
                      <button key={metricId} type="button" onClick={() => toggleMetric(metricId)} style={cardStyle(isSelected)}>
                        <div>
                          <div style={{ fontWeight: 1000, fontSize: 17 }}>{metric.label}</div>
                          <div style={{ marginTop: 8, fontSize: 15, lineHeight: 1.45, color: isSelected ? "rgba(255,255,255,0.92)" : "#475569", minHeight: 38 }}>{metric.summary}</div>
                        </div>
                        <span
                          role="button"
                          tabIndex={0}
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedMetric(expandedMetric === metricId ? null : metricId);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              e.stopPropagation();
                              setExpandedMetric(expandedMetric === metricId ? null : metricId);
                            }
                          }}
                          style={{ marginTop: 10, color: isSelected ? "white" : "#2563eb", cursor: "pointer", fontSize: 15 }}
                        >
                          {expandedMetric === metricId ? "Hide details" : "Show details"}
                        </span>
                        {expandedMetric === metricId && (
                          <div style={{ marginTop: 10, fontSize: 15, lineHeight: 1.55, color: isSelected ? "rgba(255,255,255,0.92)" : "#475569" }}>
                            {metric.description}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })}

      <Section
        title="Advanced light metric settings"
        description="Optional controls for summary bins, custom LMX windows, and light IS/IV binarization."
        expanded={expandedSettings.advanced}
        onToggle={() => toggleSettingsSection("advanced")}
        summary="Optional"
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Summary bins</div>
            <select value={settings.bins} onChange={(e) => updateSetting("bins", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              {SUMMARY_BIN_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Summary statistics</div>
            <input value={settings.aggFuncs} onChange={(e) => updateSetting("aggFuncs", e.target.value)} placeholder="mean,median,sum,std,min,max" style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>LMX length</div>
            <select value={settings.lmxLength} onChange={(e) => updateSetting("lmxLength", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              {LMX_LENGTH_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
            <input type="checkbox" checked={Boolean(settings.lowest)} onChange={(e) => updateSetting("lowest", e.target.checked)} />
            Custom LMX uses least-bright window
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
            <input type="checkbox" checked={Boolean(settings.binarizeMetric)} onChange={(e) => updateSetting("binarizeMetric", e.target.checked)} />
            Binarize before light IS/IV
          </label>
        </div>
      </Section>
    </div>
  );
}
