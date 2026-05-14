import React, { useMemo, useState } from "react";

const supportFileExtensions = ".csv,.ods,.xls,.xlsx,.txt";

const SUPPORT_HELP = {
  startStop: {
    fileHint: "Expected columns: start/stop, Start_time/Stop_time, onset/offset, or similar.",
    visualTitle: "Recording interval preview",
    intervalLabel: "Recording interval",
    startLabel: "Start time",
    stopLabel: "Stop time",
    emptyLabel: "No start/stop intervals selected yet.",
  },
  masking: {
    fileHint: "Expected columns: start/stop intervals to exclude from analysis, such as non-wear or invalid periods.",
    visualTitle: "Mask interval preview",
    intervalLabel: "Mask interval",
    startLabel: "Mask start",
    stopLabel: "Mask stop",
    emptyLabel: "No mask intervals selected yet.",
  },
  sleepDiary: {
    fileHint: "Expected columns: state/type plus start/stop, bedtime/waketime, or lights_off/rise_time.",
    visualTitle: "Sleep diary window preview",
    intervalLabel: "Diary sleep window",
    startLabel: "Bed / lights-off time",
    stopLabel: "Wake / rise time",
    emptyLabel: "No sleep diary windows selected yet.",
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

function formatDuration(start, stop) {
  const a = new Date(start);
  const b = new Date(stop);
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime()) || b <= a) return "—";
  return `${((b - a) / 3600000).toFixed(2)} h`;
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
}) {
  const help = SUPPORT_HELP[type] || SUPPORT_HELP.masking;
  const optionDefaults = useMemo(() => defaultSettings(options), [options]);
  const mergedSettings = { ...optionDefaults, manualIntervals: [], ...settings };
  const [draft, setDraft] = useState({ state: type === "sleepDiary" ? "NIGHT" : "", start: "", stop: "" });

  const updateSettings = (patch) => {
    onSettingsChange({ ...mergedSettings, ...patch });
  };

  const updateOption = (id, value) => {
    updateSettings({ [id]: value });
  };

  const addManualInterval = () => {
    if (!draft.start || !draft.stop) return;
    const start = new Date(draft.start);
    const stop = new Date(draft.stop);
    if (Number.isNaN(start.getTime()) || Number.isNaN(stop.getTime()) || stop <= start) return;
    const next = [
      ...(mergedSettings.manualIntervals || []),
      {
        state: draft.state || (type === "sleepDiary" ? "NIGHT" : type.toUpperCase()),
        start: start.toISOString(),
        stop: stop.toISOString(),
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

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      <p style={{ color: "#64748b", lineHeight: 1.6 }}>{description}</p>

      <div
        style={{
          border: "1px solid #dbeafe",
          background: "#eff6ff",
          borderRadius: 14,
          padding: 14,
          color: "#1e3a8a",
          lineHeight: 1.55,
          fontSize: 14,
          marginBottom: 14,
        }}
      >
        <strong>pyActigraphy-style support file workflow:</strong> upload a file with intervals, or manually add intervals below. {help.fileHint} Uploaded files are parsed on the backend; manual intervals are sent with the analysis request.
      </div>

      <label
        style={{
          display: "block",
          border: "2px dashed #cbd5e1",
          borderRadius: 16,
          padding: 20,
          background: "#f8fafc",
          cursor: "pointer",
          marginTop: 12,
        }}
      >
        <div style={{ fontWeight: 700 }}>Upload supporting files</div>
        <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
          {files?.length ? `${files.length} file(s) selected` : "No files selected"}
        </div>

        <input
          type="file"
          multiple
          accept={supportFileExtensions}
          style={{ display: "none" }}
          onChange={(e) => onFilesChange(Array.from(e.target.files || []))}
        />

        <div
          style={{
            marginTop: 12,
            display: "inline-block",
            padding: "8px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
            background: "white",
          }}
        >
          Choose Files
        </div>
      </label>

      {options.length > 0 && (
        <div
          style={{
            marginTop: 16,
            border: "1px solid #e2e8f0",
            borderRadius: 16,
            padding: 16,
            background: "#f8fafc",
            display: "grid",
            gap: 10,
          }}
        >
          <div style={{ fontWeight: 700 }}>Options</div>
          {options.map((opt) => (
            <label key={opt.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input
                type="checkbox"
                checked={Boolean(mergedSettings[opt.id])}
                onChange={(e) => updateOption(opt.id, e.target.checked)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      )}

      <div
        style={{
          marginTop: 16,
          border: "1px solid #e2e8f0",
          borderRadius: 16,
          padding: 16,
          background: "#ffffff",
        }}
      >
        <div style={{ fontWeight: 800, marginBottom: 10 }}>Manually select intervals</div>
        <div style={{ display: "grid", gridTemplateColumns: type === "sleepDiary" ? "1fr 1fr 1fr auto" : "1fr 1fr auto", gap: 10, alignItems: "end" }}>
          {type === "sleepDiary" && (
            <label>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Diary state</div>
              <select
                value={draft.state}
                onChange={(e) => setDraft((prev) => ({ ...prev, state: e.target.value }))}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
              >
                <option value="NIGHT">Night sleep</option>
                <option value="NAP">Nap</option>
                <option value="NOWEAR">No wear</option>
                <option value="ACTIVE">Active / out of bed</option>
              </select>
            </label>
          )}
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{help.startLabel}</div>
            <input
              type="datetime-local"
              value={draft.start}
              onChange={(e) => setDraft((prev) => ({ ...prev, start: e.target.value }))}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
            />
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{help.stopLabel}</div>
            <input
              type="datetime-local"
              value={draft.stop}
              onChange={(e) => setDraft((prev) => ({ ...prev, stop: e.target.value }))}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
            />
          </label>
          <button
            type="button"
            onClick={addManualInterval}
            style={{ padding: "11px 14px", borderRadius: 12, border: "none", background: "#0f172a", color: "white", fontWeight: 700, cursor: "pointer" }}
          >
            Add
          </button>
        </div>

        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>{help.visualTitle}</div>
          {(mergedSettings.manualIntervals || []).length === 0 ? (
            <div style={{ color: "#64748b", fontSize: 14 }}>{help.emptyLabel}</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {(mergedSettings.manualIntervals || []).map((interval, idx) => (
                <div
                  key={`${interval.start}-${interval.stop}-${idx}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1.2fr 1.2fr 0.7fr auto",
                    gap: 10,
                    alignItems: "center",
                    border: "1px solid #e2e8f0",
                    borderRadius: 12,
                    padding: 10,
                    background: "#f8fafc",
                    fontSize: 14,
                  }}
                >
                  <div><strong>{help.intervalLabel}</strong><br />{toLocalDatetimeValue(interval.start).replace("T", " ")}</div>
                  <div><strong>Stop</strong><br />{toLocalDatetimeValue(interval.stop).replace("T", " ")}</div>
                  <div><strong>Duration</strong><br />{formatDuration(interval.start, interval.stop)}</div>
                  <button
                    type="button"
                    onClick={() => removeManualInterval(idx)}
                    style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #fecaca", background: "#fff1f2", color: "#991b1b", cursor: "pointer" }}
                  >
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
