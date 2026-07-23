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

const supportFileExtensions = ".csv,.ods,.xls,.xlsx,.txt";
const ALL_FILES_ID = "__all__";

const SUPPORT_HELP = {
  startStop: {
    fileHint: "Expected columns: file_id/filename if per-file, plus start/stop, Start_time/Stop_time, onset/offset, or similar.",
    visualTitle: "Recording interval preview",
    intervalLabel: "Recording interval",
    startLabel: "Start time",
    stopLabel: "Stop time",
    emptyLabel: "No start/stop intervals selected yet.",
    plotHelp: "Use this to define the effective wear/recording window. Analysis will be truncated to the selected interval for the matching file.",
  },
  masking: {
    fileHint: "Expected columns: file_id/filename if per-file, plus start/stop intervals to exclude from analysis, such as non-wear or invalid periods.",
    visualTitle: "Mask / non-wear interval preview",
    intervalLabel: "Excluded interval",
    startLabel: "Mask / non-wear start",
    stopLabel: "Mask / non-wear stop",
    emptyLabel: "No mask or non-wear intervals selected yet.",
    plotHelp: "Use this to mark intervals that should be excluded, including non-wear or invalid activity periods, for the matching file.",
  },
  sleepDiary: {
    fileHint: "Expected columns: file_id/filename if per-file, plus state/type and start/stop, bedtime/waketime, or lights_off/rise_time.",
    visualTitle: "Sleep diary window preview",
    intervalLabel: "Diary sleep window",
    startLabel: "Bed / lights-off time",
    stopLabel: "Wake / rise time",
    emptyLabel: "No sleep diary windows selected yet.",
    plotHelp: "Use this to mark sleep diary windows while seeing where they fall in the selected recording.",
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

function axisValue(value) {
  if (!value) return value;
  return String(value).replace("T", " ").replace("Z", "");
}

function fileLabel(fileId) {
  if (!fileId || fileId === ALL_FILES_ID) return "All files";
  return fileId;
}

function intervalAppliesToSelectedFile(interval, selectedFileId) {
  const fileId = interval.fileId || interval.fileName || ALL_FILES_ID;
  return fileId === ALL_FILES_ID || !selectedFileId || fileId === selectedFileId;
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
  previewDataByFile = {},
  actigraphyFiles = [],
  onLoadPreviewForFile = null,
}) {
  const help = SUPPORT_HELP[type] || SUPPORT_HELP.masking;
  const optionDefaults = useMemo(() => defaultSettings(options), [options]);
  const mergedSettings = { ...optionDefaults, manualIntervals: [], ...settings };
  const firstFileName = actigraphyFiles?.[0]?.name || previewData?.preview_file_name || "";
  const [selectedFileId, setSelectedFileId] = useState(firstFileName || ALL_FILES_ID);
  const [draft, setDraft] = useState({
    state: type === "sleepDiary" ? "NIGHT" : type === "masking" ? "NOWEAR" : "",
    start: "",
    stop: "",
  });
  const [plotPickMode, setPlotPickMode] = useState("start");
  const [draftError, setDraftError] = useState("");
  const [plotZoomKey, setPlotZoomKey] = useState(0);
  const [plotLoading, setPlotLoading] = useState(false);
  const [plotError, setPlotError] = useState("");

  useEffect(() => {
    if (!actigraphyFiles?.length) {
      setSelectedFileId(ALL_FILES_ID);
      return;
    }
    setSelectedFileId((prev) => {
      if (prev && actigraphyFiles.some((file) => file.name === prev)) return prev;
      return actigraphyFiles[0].name;
    });
  }, [actigraphyFiles]);

  const selectedPreviewData = useMemo(() => {
    if (selectedFileId && previewDataByFile?.[selectedFileId]) return previewDataByFile[selectedFileId];
    if (previewData?.preview_file_name === selectedFileId) return previewData;
    if (actigraphyFiles.length <= 1) return previewData;
    return null;
  }, [actigraphyFiles.length, previewData, previewDataByFile, selectedFileId]);

  const plotPoints = selectedPreviewData?.full_recording_preview || [];
  const bounds = useMemo(() => getPreviewBounds(selectedPreviewData), [selectedPreviewData]);
  const hasPlot = plotPoints.length > 0;
  const visiblePlotIntervals = (mergedSettings.manualIntervals || []).filter((interval) => intervalAppliesToSelectedFile(interval, selectedFileId));

  const updateSettings = (patch) => {
    onSettingsChange({ ...mergedSettings, ...patch });
  };

  const updateOption = (id, value) => {
    updateSettings({ [id]: value });
  };

  const loadSelectedPlot = async () => {
    if (!onLoadPreviewForFile || !selectedFileId || selectedFileId === ALL_FILES_ID) return;
    setPlotError("");
    setPlotLoading(true);
    try {
      await onLoadPreviewForFile(selectedFileId);
    } catch (err) {
      setPlotError(err.message || "Could not load this file preview.");
    } finally {
      setPlotLoading(false);
    }
  };

  const addManualInterval = () => {
    setDraftError("");
    if (!selectedFileId || selectedFileId === ALL_FILES_ID) {
      setDraftError("Choose the file this interval belongs to, or use uploaded support files for global intervals.");
      return;
    }
    if (!draft.start || !draft.stop) {
      setDraftError("Choose both start and stop times.");
      return;
    }
    if (hasPlot && !intervalInBounds(draft.start, draft.stop, bounds)) {
      setDraftError("The selected interval must be within the selected file's detected recording start/end and stop must be after start.");
      return;
    }
    if (!hasPlot && parseDatetime(draft.stop) <= parseDatetime(draft.start)) {
      setDraftError("Stop must be after start. For overnight intervals, choose the next calendar date for the stop time.");
      return;
    }

    const start = new Date(draft.start);
    const stop = new Date(draft.stop);
    const next = [
      ...(mergedSettings.manualIntervals || []),
      {
        fileId: selectedFileId,
        fileName: selectedFileId,
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
        <strong>pyActigraphy-style support file workflow:</strong> upload a file with intervals, manually add intervals with the calendar fields, or click points on the selected file's activity plot. {help.fileHint} Uploaded files are parsed on the backend; manual intervals are sent with a file ID so each interval only applies to the matching file.
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

      {type === "masking" && (
        <div style={{ marginTop: 16, border: "1px solid #cbd5e1", borderRadius: 16, padding: 16, background: "#f8fafc" }}>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Missing-data and valid-day rules</div>
          <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginBottom: 12 }}>
            Missing epochs and excluded non-wear remain unavailable; they are never converted to zero activity. The standard rules are 16 analyzable hours per valid day, at least 2 consecutive valid days for multi-day rhythm/SRI metrics, and 80% coverage for sleep-window summaries.
          </div>

          <label style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 12, borderRadius: 12, border: "1px solid #dbeafe", background: "#eff6ff" }}>
            <input
              type="checkbox"
              checked={Boolean(mergedSettings.customizeDataQualityThresholds)}
              onChange={(event) => updateSettings({ customizeDataQualityThresholds: event.target.checked })}
              style={{ marginTop: 3 }}
            />
            <span>
              <span style={{ display: "block", fontWeight: 700, color: "#1e3a8a" }}>Modify the standard data-quality thresholds</span>
              <span style={{ display: "block", marginTop: 3, color: "#475569", fontSize: 13 }}>
                Leave this off for the project standard. Turn it on only when the study protocol specifies different validity rules.
              </span>
            </span>
          </label>

          {mergedSettings.customizeDataQualityThresholds ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, marginTop: 14 }}>
              <label>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Minimum valid hours per day</div>
                <input
                  type="number"
                  min="1"
                  max="24"
                  step="0.5"
                  value={mergedSettings.minimumValidHoursPerDay ?? 16}
                  onChange={(event) => updateSettings({ minimumValidHoursPerDay: Number(event.target.value) })}
                  style={{ width: "100%", padding: "9px 10px", borderRadius: 10, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                />
                <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>Allowed range: 1–24 hours.</div>
              </label>
              <label>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Minimum consecutive valid days for rhythm/SRI</div>
                <input
                  type="number"
                  min="1"
                  max="365"
                  step="1"
                  value={mergedSettings.minimumValidDaysForRhythm ?? 2}
                  onChange={(event) => updateSettings({ minimumValidDaysForRhythm: Number(event.target.value) })}
                  style={{ width: "100%", padding: "9px 10px", borderRadius: 10, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                />
                <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>The days must form one uninterrupted calendar-day run.</div>
              </label>
              <label>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Minimum sleep-window coverage</div>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={mergedSettings.minimumSleepWindowCoverage ?? 0.8}
                  onChange={(event) => updateSettings({ minimumSleepWindowCoverage: Number(event.target.value) })}
                  style={{ width: "100%", padding: "9px 10px", borderRadius: 10, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                />
                <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>0.8 means 80% recorded/scored coverage.</div>
              </label>
            </div>
          ) : (
            <div style={{ marginTop: 12, color: "#166534", fontSize: 13, fontWeight: 700 }}>
              Standard thresholds active: 16 h/day · 2 consecutive valid days · 80% sleep-window coverage
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#ffffff" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 12, flexWrap: "wrap" }}>
          <div style={{ minWidth: 260, flex: 1 }}>
            <div style={{ fontWeight: 800 }}>Interactive interval selection</div>
            <div style={{ color: "#64748b", fontSize: 14, lineHeight: 1.5 }}>
              {help.plotHelp} Current file bounds: <strong>{formatDisplayDatetime(bounds.start)}</strong> to <strong>{formatDisplayDatetime(bounds.stop)}</strong>.
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap", justifyContent: "flex-end" }}>
            <label style={{ minWidth: 240 }}>
              <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 13 }}>Plot / interval file</div>
              <select value={selectedFileId} onChange={(e) => setSelectedFileId(e.target.value)} style={{ width: "100%", padding: "9px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
                {(actigraphyFiles || []).map((file) => <option key={file.name} value={file.name}>{file.name}</option>)}
              </select>
            </label>
            {onLoadPreviewForFile && selectedFileId && (
              <button type="button" onClick={loadSelectedPlot} disabled={plotLoading} style={{ padding: "9px 10px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", color: "#0f172a", cursor: plotLoading ? "wait" : "pointer", fontWeight: 700 }}>
                {plotLoading ? "Loading plot..." : hasPlot ? "Refresh plot" : "Load plot"}
              </button>
            )}
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

        {plotError && <div style={{ padding: 10, borderRadius: 10, border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", marginBottom: 12, fontSize: 14 }}>{plotError}</div>}

        {hasPlot ? (
          <>
            <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>
              Drag the small range selector under the plot to zoom into a fine-grained time window. Click the zoomed line to set start/stop points for <strong>{selectedFileId}</strong>.
            </div>
            <div style={{ height: 330, border: "1px solid #e2e8f0", borderRadius: 14, padding: 12, background: "#f8fafc", marginBottom: 16 }}>
              <ResponsiveContainer key={plotZoomKey} width="100%" height="100%">
                <LineChart data={plotPoints} onClick={applyPlotClick} margin={{ top: 10, right: 20, left: 5, bottom: 42 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" minTickGap={40} tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  {visiblePlotIntervals.map((interval, idx) => (
                    <ReferenceArea key={`interval-${idx}`} x1={axisValue(interval.start)} x2={axisValue(interval.stop)} ifOverflow="extendDomain" />
                  ))}
                  {draft.start && draft.stop && (
                    <ReferenceArea x1={axisValue(draft.start)} x2={axisValue(draft.stop)} ifOverflow="extendDomain" />
                  )}
                  <Line type="monotone" dataKey="activity" dot={false} strokeWidth={1.5} isAnimationActive={false} />
                  <Brush dataKey="timestamp" height={26} travellerWidth={10} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <div style={{ padding: 14, borderRadius: 14, border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e", marginBottom: 16 }}>
            Choose a file and load its activity preview to enable plot-based interval selection. Manual date/time entry still works, but the plot helps verify that intervals are inside that file.
          </div>
        )}

        <div style={{ fontWeight: 800, marginBottom: 10 }}>Add interval</div>
        <div style={{ display: "grid", gridTemplateColumns: type === "sleepDiary" || type === "masking" ? "1fr 1fr 1fr 1fr auto" : "1fr 1fr 1fr auto", gap: 10, alignItems: "end" }}>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>File ID</div>
            <select value={selectedFileId} onChange={(e) => setSelectedFileId(e.target.value)} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}>
              {(actigraphyFiles || []).map((file) => <option key={file.name} value={file.name}>{file.name}</option>)}
            </select>
          </label>
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
            <input type="datetime-local" value={draft.start} min={hasPlot ? bounds.minLocal || undefined : undefined} max={hasPlot ? bounds.maxLocal || undefined : undefined} onChange={(e) => setDraft((prev) => ({ ...prev, start: e.target.value }))} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{help.stopLabel}</div>
            <input type="datetime-local" value={draft.stop} min={hasPlot ? bounds.minLocal || undefined : undefined} max={hasPlot ? bounds.maxLocal || undefined : undefined} onChange={(e) => setDraft((prev) => ({ ...prev, stop: e.target.value }))} style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }} />
          </label>
          <button type="button" onClick={addManualInterval} style={{ padding: "11px 14px", borderRadius: 12, border: "none", background: "#0f172a", color: "white", fontWeight: 700, cursor: "pointer" }}>
            Add
          </button>
        </div>

        <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginTop: 8 }}>
          Overnight intervals work when the stop date/time is on the next calendar day, for example 2026-07-01 23:00 to 2026-07-02 02:00.
        </div>
        {draftError && <div style={{ color: "#b91c1c", marginTop: 10, fontSize: 14 }}>{draftError}</div>}

        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>{help.visualTitle}</div>
          {(mergedSettings.manualIntervals || []).length === 0 ? (
            <div style={{ color: "#64748b", fontSize: 14 }}>{help.emptyLabel}</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {(mergedSettings.manualIntervals || []).map((interval, idx) => (
                <div key={`${interval.fileId}-${interval.start}-${interval.stop}-${idx}`} style={{ display: "grid", gridTemplateColumns: "1.3fr 0.8fr 1.15fr 1.15fr 0.6fr auto", gap: 10, alignItems: "center", border: "1px solid #e2e8f0", borderRadius: 12, padding: 10, background: "#f8fafc", fontSize: 14 }}>
                  <div><strong>File ID</strong><br />{fileLabel(interval.fileId || interval.fileName)}</div>
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
