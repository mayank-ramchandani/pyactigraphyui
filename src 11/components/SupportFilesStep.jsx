import React, { useMemo, useState } from "react";
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

const supportFileExtensions = ".csv,.ods,.xls,.xlsx,.txt";

const SUPPORT_HELP = {
  startStop: {
    fileHint: "Expected columns: start/stop, Start_time/Stop_time, onset/offset, or similar.",
    visualTitle: "Recording interval preview",
    intervalLabel: "Recording interval",
    startLabel: "Start time",
    stopLabel: "Stop time",
    emptyLabel: "No start/stop intervals selected yet.",
    plotHelp: "Use this to define the effective wear/recording window. Analysis will be truncated to the selected interval.",
  },
  masking: {
    fileHint: "Expected columns: start/stop intervals to exclude from analysis, such as non-wear or invalid periods.",
    visualTitle: "Mask / non-wear interval preview",
    intervalLabel: "Excluded interval",
    startLabel: "Mask / non-wear start",
    stopLabel: "Mask / non-wear stop",
    emptyLabel: "No mask or non-wear intervals selected yet.",
    plotHelp: "Use this to mark intervals that should be excluded, including non-wear or invalid activity periods.",
  },
  sleepDiary: {
    fileHint: "Expected columns: state/type plus start/stop, bedtime/waketime, or lights_off/rise_time.",
    visualTitle: "Sleep diary window preview",
    intervalLabel: "Diary sleep window",
    startLabel: "Bed / lights-off time",
    stopLabel: "Wake / rise time",
    emptyLabel: "No sleep diary windows selected yet.",
    plotHelp: "Use this to mark sleep diary windows while seeing where they fall in the recording.",
  },
};

function defaultSettings(options) {
  return Object.fromEntries(options.map((opt) => [opt.id, opt.defaultValue ?? false]));
}

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

function formatDuration(start, stop) {
  const a = parseDatetime(start);
  const b = parseDatetime(stop);
  if (!a || !b || b <= a) return "—";
  return `${((b - a) / 3600000).toFixed(2)} h`;
}

function formatDisplayDatetime(value) {
  const local = toLocalDatetimeValue(value);
  return local ? local.replace("T", " ") : "—";
}

function getPreviewBounds(previewData) {
  const points = previewData?.full_recording_preview || [];
  const summary = previewData?.summary || {};
  const start = summary.start || points[0]?.timestamp || "";
  const stop = summary.end || points[points.length - 1]?.timestamp || "";
  return {
    start,
    stop,
    minLocal: toLocalDatetimeValue(start),
    maxLocal: toLocalDatetimeValue(stop),
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

export default function SupportFilesStep({
  title,
  description,
  type = "masking",
  files,
  onFilesChange,
  options = [],
  settings = {},
  onSettingsChange = () => {},
  previewData = null,
}) {
  const help = SUPPORT_HELP[type] || SUPPORT_HELP.masking;
  const optionDefaults = useMemo(() => defaultSettings(options), [options]);
  const mergedSettings = { ...optionDefaults, manualIntervals: [], ...settings };
  const [draft, setDraft] = useState({ state: type === "sleepDiary" ? "NIGHT" : type === "masking" ? "NOWEAR" : "", start: "", stop: "" });
  const [plotPickMode, setPlotPickMode] = useState("start");
  const [draftError, setDraftError] = useState("");
  const [plotZoomKey, setPlotZoomKey] = useState(0);

  const plotPoints = previewData?.full_recording_preview || [];
  const bounds = useMemo(() => getPreviewBounds(previewData), [previewData]);
  const hasPlot = plotPoints.length > 0;

  const updateSettings = (patch) => {
    onSettingsChange({ ...mergedSettings, ...patch });
  };

  const updateOption = (id, value) => {
    updateSettings({ [id]: value });
  };

  const addManualInterval = () => {
    setDraftError("");
    if (!draft.start || !draft.stop) {
      setDraftError("Choose both start and stop times.");
      return;
    }
    if (!intervalInBounds(draft.start, draft.stop, bounds)) {
      setDraftError("The selected interval must be within the detected recording start/end and stop must be after start.");
      return;
    }

    const start = new Date(draft.start);
    const stop = new Date(draft.stop);
    const next = [
      ...(mergedSettings.manualIntervals || []),
      {
        state: draft.state || (type === "sleepDiary" ? "NIGHT" : type === "masking" ? "NOWEAR" : type.toUpperCase()),
        start: start.toISOString(),
        stop: stop.toISOString(),
        source: "manual_ui",
      },
    ];
    updateSettings({ manualIntervals: next });
    setDraft((prev) => ({ ...prev, start: "", stop: "" }));
  };

  const removeManualInterval = (idx) => {
    updateSettings({
      manualIntervals: (mergedSettings.manualIntervals || []).filter((_, i) => i !== idx),
    });
  };

  const applyPlotClick = (payload) => {
    const timestamp = payload?.activeLabel || payload?.activePayload?.[0]?.payload?.timestamp;
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
      return next;
    });
    setPlotPickMode((prev) => (prev === "start" ? "stop" : "start"));
  };

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      <p style={{ color: "#64748b", lineHeight: 1.6 }}>{description}</p>

      <div style={{ border: "1px solid #dbeafe", background: "#eff6ff", borderRadius: 14, padding: 14, color: "#1e3a8a", lineHeight: 1.55, fontSize: 14, marginBottom: 14 }}>
        <strong>pyActigraphy-style support file workflow:</strong> upload a file with intervals, manually add intervals with the calendar fields, or click points on the activity plot. {help.fileHint} Uploaded files are parsed on the backend; manual intervals are sent with the analysis request.
      </div>

      <label style={{ display: "block", border: "2px dashed #cbd5e1", borderRadius: 16, padding: 20, background: "#f8fafc", cursor: "pointer", marginTop: 12 }}>
        <div style={{ fontWeight: 700 }}>Upload supporting files</div>
        <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
          {files?.length ? `${files.length} file(s) selected` : "No files selected"}
        </div>

        <input type="file" multiple accept={supportFileExtensions} style={{ display: "none" }} onChange={(e) => onFilesChange(Array.from(e.target.files || []))} />

        <div style={{ marginTop: 12, display: "inline-block", padding: "8px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
          Choose Files
        </div>
      </label>

      {options.length > 0 && (
        <div style={{ marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc", display: "grid", gap: 10 }}>
          <div style={{ fontWeight: 700 }}>Options</div>
          {options.map((opt) => (
            <label key={opt.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input type="checkbox" checked={Boolean(mergedSettings[opt.id])} onChange={(e) => updateOption(opt.id, e.target.checked)} />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      )}

      <div style={{ marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#ffffff" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <div style={{ fontWeight: 800 }}>Interactive interval selection</div>
            <div style={{ color: "#64748b", fontSize: 14, lineHeight: 1.5 }}>
              {help.plotHelp} Calendar inputs are limited to the detected recording window: <strong>{formatDisplayDatetime(bounds.start)}</strong> to <strong>{formatDisplayDatetime(bounds.stop)}</strong>.
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
            <span style={{ color: "#64748b", fontSize: 14 }}>Plot click sets:</span>
            {[
              { id: "start", label: "Start" },
              { id: "stop", label: "Stop" },
            ].map((item) => (
              <button key={item.id} type="button" onClick={() => setPlotPickMode(item.id)} style={{ padding: "8px 10px", borderRadius: 10, border: plotPickMode === item.id ? "1px solid #0f172a" : "1px solid #cbd5e1", background: plotPickMode === item.id ? "#0f172a" : "white", color: plotPickMode === item.id ? "white" : "#0f172a", cursor: "pointer", fontWeight: 700 }}>
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
            <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>
              Drag the small range selector under the plot to zoom into a fine-grained time window. Click the zoomed line to set start/stop points.
            </div>
            <div style={{ height: 330, border: "1px solid #e2e8f0", borderRadius: 14, padding: 12, background: "#f8fafc", marginBottom: 16 }}>
              <ResponsiveContainer key={plotZoomKey} width="100%" height="100%">
                <LineChart data={plotPoints} onClick={applyPlotClick} margin={{ top: 10, right: 20, left: 5, bottom: 42 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" minTickGap={40} tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  {(mergedSettings.manualIntervals || []).map((interval, idx) => (
                    <ReferenceArea key={`interval-${idx}`} x1={interval.start ? String(interval.start).replace("T", " ").replace("Z", "") : interval.start} x2={interval.stop ? String(interval.stop).replace("T", " ").replace("Z", "") : interval.stop} ifOverflow="extendDomain" />
                  ))}
                  {draft.start && draft.stop && (
                    <ReferenceArea x1={String(draft.start).replace("T", " ")} x2={String(draft.stop).replace("T", " ")} ifOverflow="extendDomain" />
                  )}
                  <Line type="monotone" dataKey="activity" dot={false} strokeWidth={1.5} isAnimationActive={false} />
                  <Brush dataKey="timestamp" height={26} travellerWidth={10} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <div style={{ padding: 14, borderRadius: 14, border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e", marginBottom: 16 }}>
            Load the activity preview first to enable plot-based interval selection.
          </div>
        )}

        <div style={{ fontWeight: 800, marginBottom: 10 }}>Add interval</div>
        <div style={{ display: "grid", gridTemplateColumns: type === "sleepDiary" || type === "masking" ? "1fr 1fr 1fr auto" : "1fr 1fr auto", gap: 10, alignItems: "end" }}>
          {type === "sleepDiary" && (
            <label>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Diary state</div>
              <select value={draft.state} onChange={(e) => setDraft((prev) => ({ ...prev, state: e.target.value }))} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
                <option value="NIGHT">Night sleep</option>
                <option value="NAP">Nap</option>
                <option value="NOWEAR">No wear</option>
                <option value="ACTIVE">Active / out of bed</option>
              </select>
            </label>
          )}
          {type === "masking" && (
            <label>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Interval type</div>
              <select value={draft.state} onChange={(e) => setDraft((prev) => ({ ...prev, state: e.target.value }))} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}>
                <option value="NOWEAR">Non-wear / no wear</option>
                <option value="MASK">Mask / invalid</option>
                <option value="OFF_WRIST">Off-wrist</option>
              </select>
            </label>
          )}
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{help.startLabel}</div>
            <input type="datetime-local" value={draft.start} min={bounds.minLocal || undefined} max={bounds.maxLocal || undefined} onChange={(e) => setDraft((prev) => ({ ...prev, start: e.target.value }))} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{help.stopLabel}</div>
            <input type="datetime-local" value={draft.stop} min={bounds.minLocal || undefined} max={bounds.maxLocal || undefined} onChange={(e) => setDraft((prev) => ({ ...prev, stop: e.target.value }))} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
          <button type="button" onClick={addManualInterval} style={{ padding: "11px 14px", borderRadius: 12, border: "none", background: "#0f172a", color: "white", fontWeight: 700, cursor: "pointer" }}>
            Add
          </button>
        </div>

        {draftError && <div style={{ color: "#b91c1c", marginTop: 10, fontSize: 14 }}>{draftError}</div>}

        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>{help.visualTitle}</div>
          {(mergedSettings.manualIntervals || []).length === 0 ? (
            <div style={{ color: "#64748b", fontSize: 14 }}>{help.emptyLabel}</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {(mergedSettings.manualIntervals || []).map((interval, idx) => (
                <div key={`${interval.start}-${interval.stop}-${idx}`} style={{ display: "grid", gridTemplateColumns: "0.7fr 1.2fr 1.2fr 0.7fr auto", gap: 10, alignItems: "center", border: "1px solid #e2e8f0", borderRadius: 12, padding: 10, background: "#f8fafc", fontSize: 14 }}>
                  <div><strong>Type</strong><br />{interval.state || type.toUpperCase()}</div>
                  <div><strong>{help.intervalLabel}</strong><br />{formatDisplayDatetime(interval.start)}</div>
                  <div><strong>Stop</strong><br />{formatDisplayDatetime(interval.stop)}</div>
                  <div><strong>Duration</strong><br />{formatDuration(interval.start, interval.stop)}</div>
                  <button type="button" onClick={() => removeManualInterval(idx)} style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #fecaca", background: "#fff1f2", color: "#991b1b", cursor: "pointer" }}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
