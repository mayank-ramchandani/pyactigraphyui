import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  Brush,
} from "recharts";

function toLocalDatetimeValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function parseDatetime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDisplayDatetime(value) {
  const local = toLocalDatetimeValue(value);
  return local ? local.replace("T", " ") : "—";
}

function formatDuration(start, stop) {
  const a = parseDatetime(start);
  const b = parseDatetime(stop);
  if (!a || !b || b <= a) return "—";
  return `${((b - a) / 3600000).toFixed(2)} h`;
}

function getBounds(points, bounds) {
  const first = bounds?.start || points?.[0]?.timestamp || points?.[0]?.time || "";
  const last = bounds?.stop || bounds?.end || points?.[points.length - 1]?.timestamp || points?.[points.length - 1]?.time || "";
  return {
    start: first,
    stop: last,
    minLocal: bounds?.minLocal || toLocalDatetimeValue(first),
    maxLocal: bounds?.maxLocal || toLocalDatetimeValue(last),
  };
}

function intervalInBounds(start, stop, bounds) {
  const startDate = parseDatetime(start);
  const stopDate = parseDatetime(stop);
  const minDate = parseDatetime(bounds.start);
  const maxDate = parseDatetime(bounds.stop);
  if (!startDate || !stopDate || stopDate <= startDate) return false;
  if (minDate && startDate < minDate) return false;
  if (maxDate && stopDate > maxDate) return false;
  return true;
}

function axisValue(value) {
  if (!value) return value;
  return String(value).replace("T", " ").replace("Z", "");
}

export default function InteractiveIntervalSelector({
  title = "Interactive interval selection",
  description = "Use the plot, zoom control, or calendar fields to select start and stop times.",
  plotPoints = [],
  valueKey = "activity",
  valueLabel = "Activity",
  lineName = "Activity",
  bounds = null,
  intervals = [],
  onIntervalsChange = null,
  startValue = "",
  stopValue = "",
  onWindowChange = null,
  allowMultiple = true,
  intervalTypeOptions = null,
  defaultState = "INTERVAL",
  intervalLabel = "Analysis interval",
  emptyLabel = "No intervals selected yet.",
  plotHelp = "Drag the range selector under the plot to zoom. Click the zoomed line to set start and stop points.",
  addButtonLabel = "Add interval",
  applyButtonLabel = "Apply window",
  noPlotMessage = "Load the relevant preview first to enable plot-based interval selection.",
  enabled = true,
}) {
  const resolvedBounds = useMemo(() => getBounds(plotPoints || [], bounds), [plotPoints, bounds]);
  const [draft, setDraft] = useState({
    state: defaultState,
    start: toLocalDatetimeValue(startValue),
    stop: toLocalDatetimeValue(stopValue),
  });
  const [plotPickMode, setPlotPickMode] = useState("start");
  const [draftError, setDraftError] = useState("");
  const [plotZoomKey, setPlotZoomKey] = useState(0);

  const hasPlot = (plotPoints || []).length > 0;
  const rows = allowMultiple ? intervals || [] : (startValue && stopValue ? [{ state: defaultState, start: startValue, stop: stopValue, source: "selected_window" }] : []);

  useEffect(() => {
    if (!allowMultiple) {
      setDraft((prev) => ({
        ...prev,
        start: toLocalDatetimeValue(startValue),
        stop: toLocalDatetimeValue(stopValue),
      }));
    }
  }, [allowMultiple, startValue, stopValue]);

  const emitSingleWindow = (nextDraft) => {
    if (!allowMultiple && onWindowChange) {
      onWindowChange({ start: nextDraft.start || "", stop: nextDraft.stop || "" });
    }
  };

  const updateDraftField = (field, value) => {
    setDraftError("");
    setDraft((prev) => {
      const next = { ...prev, [field]: value };
      emitSingleWindow(next);
      return next;
    });
  };

  const applyPlotClick = (payload) => {
    if (!enabled) return;
    const timestamp = payload?.activeLabel || payload?.activePayload?.[0]?.payload?.timestamp || payload?.activePayload?.[0]?.payload?.time;
    const value = toLocalDatetimeValue(timestamp);
    if (!value) return;
    setDraftError("");
    setDraft((prev) => {
      const next = { ...prev, [plotPickMode]: value };
      if (plotPickMode === "start" && prev.stop && new Date(value) >= new Date(prev.stop)) {
        next.stop = "";
      }
      if (plotPickMode === "stop" && prev.start && new Date(value) <= new Date(prev.start)) {
        next.start = "";
      }
      emitSingleWindow(next);
      return next;
    });
    setPlotPickMode((prev) => (prev === "start" ? "stop" : "start"));
  };

  const addOrApply = () => {
    setDraftError("");
    if (!draft.start || !draft.stop) {
      setDraftError("Choose both start and stop date/times.");
      return;
    }
    if (!intervalInBounds(draft.start, draft.stop, resolvedBounds)) {
      setDraftError("The selected interval must be within the detected recording window and stop must be after start.");
      return;
    }

    if (!allowMultiple) {
      emitSingleWindow(draft);
      return;
    }

    const start = new Date(draft.start);
    const stop = new Date(draft.stop);
    const next = [
      ...(intervals || []),
      {
        state: draft.state || defaultState,
        start: start.toISOString(),
        stop: stop.toISOString(),
        source: "manual_ui",
      },
    ];
    if (onIntervalsChange) onIntervalsChange(next);
    setDraft((prev) => ({ ...prev, start: "", stop: "" }));
  };

  const removeInterval = (idx) => {
    if (!allowMultiple || !onIntervalsChange) return;
    onIntervalsChange((intervals || []).filter((_, i) => i !== idx));
  };

  const clearSingleWindow = () => {
    if (allowMultiple) return;
    setDraft((prev) => ({ ...prev, start: "", stop: "" }));
    if (onWindowChange) onWindowChange({ start: "", stop: "" });
  };

  return (
    <div style={{ marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#ffffff" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <div style={{ fontWeight: 800 }}>{title}</div>
          <div style={{ color: "#64748b", fontSize: 14, lineHeight: 1.5 }}>
            {description} Calendar inputs are limited to <strong>{formatDisplayDatetime(resolvedBounds.start)}</strong> to <strong>{formatDisplayDatetime(resolvedBounds.stop)}</strong>.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
          <span style={{ color: "#64748b", fontSize: 14 }}>Plot click sets:</span>
          {[
            { id: "start", label: "Start" },
            { id: "stop", label: "Stop" },
          ].map((item) => (
            <button key={item.id} type="button" disabled={!enabled} onClick={() => setPlotPickMode(item.id)} style={{ padding: "8px 10px", borderRadius: 10, border: plotPickMode === item.id ? "1px solid #0f172a" : "1px solid #cbd5e1", background: plotPickMode === item.id ? "#0f172a" : "white", color: plotPickMode === item.id ? "white" : "#0f172a", cursor: enabled ? "pointer" : "not-allowed", fontWeight: 700 }}>
              {item.label}
            </button>
          ))}
          {hasPlot && (
            <button type="button" onClick={() => setPlotZoomKey((prev) => prev + 1)} style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", color: "#0f172a", cursor: "pointer", fontWeight: 700 }}>
              Reset zoom
            </button>
          )}
        </div>
      </div>

      {hasPlot ? (
        <>
          <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>{plotHelp}</div>
          <div style={{ height: 330, border: "1px solid #e2e8f0", borderRadius: 14, padding: 12, background: "#f8fafc", marginBottom: 16 }}>
            <ResponsiveContainer key={plotZoomKey} width="100%" height="100%">
              <LineChart data={plotPoints} onClick={applyPlotClick} margin={{ top: 10, right: 20, left: 5, bottom: 42 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" minTickGap={40} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} label={{ value: valueLabel, angle: -90, position: "insideLeft", fontSize: 11 }} />
                <Tooltip />
                {rows.map((interval, idx) => (
                  <ReferenceArea key={`interval-${idx}`} x1={axisValue(interval.start)} x2={axisValue(interval.stop)} ifOverflow="extendDomain" />
                ))}
                {draft.start && draft.stop && (
                  <ReferenceArea x1={axisValue(draft.start)} x2={axisValue(draft.stop)} ifOverflow="extendDomain" />
                )}
                <Line name={lineName} type="monotone" dataKey={valueKey} dot={false} strokeWidth={1.5} isAnimationActive={false} />
                <Brush dataKey="timestamp" height={26} travellerWidth={10} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div style={{ padding: 14, borderRadius: 14, border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e", marginBottom: 16 }}>
          {noPlotMessage}
        </div>
      )}

      <div style={{ fontWeight: 800, marginBottom: 10 }}>{allowMultiple ? "Add interval" : "Selected time window"}</div>
      <div style={{ display: "grid", gridTemplateColumns: intervalTypeOptions ? "1fr 1fr 1fr auto" : "1fr 1fr auto", gap: 10, alignItems: "end" }}>
        {intervalTypeOptions && (
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Interval type</div>
            <select value={draft.state} disabled={!enabled} onChange={(e) => updateDraftField("state", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              {intervalTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
        )}
        <label>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Start date/time</div>
          <input type="datetime-local" disabled={!enabled} value={draft.start} min={resolvedBounds.minLocal || undefined} max={resolvedBounds.maxLocal || undefined} onChange={(e) => updateDraftField("start", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
        </label>
        <label>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Stop date/time</div>
          <input type="datetime-local" disabled={!enabled} value={draft.stop} min={resolvedBounds.minLocal || undefined} max={resolvedBounds.maxLocal || undefined} onChange={(e) => updateDraftField("stop", e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
        </label>
        <button type="button" disabled={!enabled} onClick={addOrApply} style={{ padding: "11px 14px", borderRadius: 12, border: "none", background: enabled ? "#0f172a" : "#94a3b8", color: "white", fontWeight: 700, cursor: enabled ? "pointer" : "not-allowed" }}>
          {allowMultiple ? addButtonLabel : applyButtonLabel}
        </button>
      </div>

      {!allowMultiple && (startValue || stopValue) && (
        <button type="button" onClick={clearSingleWindow} style={{ marginTop: 10, padding: "8px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", color: "#0f172a", cursor: "pointer" }}>
          Clear selected light window
        </button>
      )}

      {draftError && <div style={{ color: "#b91c1c", marginTop: 10, fontSize: 14 }}>{draftError}</div>}

      <div style={{ marginTop: 16 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>{intervalLabel}</div>
        {rows.length === 0 ? (
          <div style={{ color: "#64748b", fontSize: 14 }}>{emptyLabel}</div>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {rows.map((interval, idx) => (
              <div key={`${interval.start}-${interval.stop}-${idx}`} style={{ display: "grid", gridTemplateColumns: allowMultiple ? "0.7fr 1.2fr 1.2fr 0.7fr auto" : "1.2fr 1.2fr 0.7fr auto", gap: 10, alignItems: "center", border: "1px solid #e2e8f0", borderRadius: 12, padding: 10, background: "#f8fafc", fontSize: 14 }}>
                {allowMultiple && <div><strong>Type</strong><br />{interval.state || defaultState}</div>}
                <div><strong>Start</strong><br />{formatDisplayDatetime(interval.start)}</div>
                <div><strong>Stop</strong><br />{formatDisplayDatetime(interval.stop)}</div>
                <div><strong>Duration</strong><br />{formatDuration(interval.start, interval.stop)}</div>
                {allowMultiple ? (
                  <button type="button" onClick={() => removeInterval(idx)} style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #fecaca", background: "#fff1f2", color: "#991b1b", cursor: "pointer" }}>
                    Remove
                  </button>
                ) : (
                  <button type="button" onClick={clearSingleWindow} style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", color: "#0f172a", cursor: "pointer" }}>
                    Clear
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
