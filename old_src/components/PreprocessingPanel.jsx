import React, { useMemo, useState } from "react";
import { buildFileEntries, fileEntryLabel, formatFileSize } from "../services/fileIdentityUtils";

function BubbleInfo({ label, content }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span>{label}</span>
      <button
        type="button"
        aria-label={`More information about ${label}`}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen((value) => !value);
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        style={{
          width: 18,
          height: 18,
          borderRadius: 999,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#e2e8f0",
          color: "#0f172a",
          fontSize: 12,
          fontWeight: 800,
          border: "none",
          cursor: "pointer",
          padding: 0,
        }}
      >
        i
      </button>
      {open && (
        <div
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
          style={{
            position: "absolute",
            top: "125%",
            left: 0,
            zIndex: 50,
            width: 380,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: "white",
            color: "#334155",
            fontSize: 13,
            lineHeight: 1.5,
            boxShadow: "0 8px 24px rgba(15,23,42,0.14)",
          }}
        >
          {content}
        </div>
      )}
    </span>
  );
}

function NumberField({ label, value, onChange, min, max, step, help, info }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>
        {info ? <BubbleInfo label={label} content={info} /> : label}
      </div>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{ width: "100%", padding: "10px 11px", borderRadius: 10, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
      />
      <div style={{ color: "#64748b", fontSize: 12, marginTop: 5, lineHeight: 1.45 }}>{help}</div>
    </label>
  );
}

function formatHours(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `${Number(number.toFixed(2))} h`;
}

function InitialQcCard({ entry, payload, loading, error, settings }) {
  const mode = settings.validDayWindowMode || "calendar_day";
  const modePayload = payload?.modes?.[mode] || {};
  const windows = modePayload.windows || [];
  const threshold = Number(settings.minimumValidHoursPerDay ?? 16);
  const respectNonwear = Boolean(settings.respectNonwear);
  const effectiveHours = (row) => Number(respectNonwear ? row.analyzable_hours : row.recorded_hours) || 0;
  const validCount = windows.filter((row) => effectiveHours(row) + 1e-9 >= threshold).length;
  const invalidCount = Math.max(0, windows.length - validCount);
  const modeLabel = mode === "recording_anchored" ? "recording-aligned 24-hour windows" : "calendar days";

  return (
    <details style={{ border: "1px solid #e2e8f0", borderRadius: 14, background: "white", overflow: "hidden" }}>
      <summary style={{ cursor: "pointer", padding: 13, listStyle: "none" }}>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 12, alignItems: "center" }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 800, overflowWrap: "anywhere" }}>{fileEntryLabel(entry)}</div>
            <div style={{ color: "#64748b", fontSize: 12, marginTop: 3 }}>{formatFileSize(entry.file?.size)}</div>
          </div>
          <div style={{ textAlign: "right", fontSize: 13 }}>
            {loading ? (
              <span style={{ color: "#475569", fontWeight: 700 }}>Inspecting…</span>
            ) : error ? (
              <span style={{ color: "#991b1b", fontWeight: 800 }}>QC unavailable</span>
            ) : payload ? (
              <>
                <span style={{ color: validCount > 0 ? "#166534" : "#991b1b", fontWeight: 800 }}>{validCount} valid</span>
                <span style={{ color: "#64748b" }}> · {invalidCount} below threshold</span>
              </>
            ) : (
              <span style={{ color: "#64748b" }}>Queued</span>
            )}
          </div>
        </div>
      </summary>

      <div style={{ borderTop: "1px solid #e2e8f0", padding: 13 }}>
        {error && (
          <div style={{ border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", borderRadius: 10, padding: 10, fontSize: 13 }}>
            {error}
          </div>
        )}
        {!error && loading && <div style={{ color: "#475569", fontSize: 13 }}>Loading the file and calculating initial per-day coverage. Large raw recordings may take longer to inspect.</div>}
        {!error && payload && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, marginBottom: 12 }}>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Recorded</strong><br />{formatHours(payload.recorded_hours)}</div>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Initial gaps</strong><br />{formatHours(payload.recording_gap_hours)}</div>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Window basis</strong><br />{modeLabel}</div>
              <div style={{ background: "#f8fafc", borderRadius: 10, padding: 10 }}><strong>Threshold applied here</strong><br />{threshold} h</div>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 720, fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Quality window</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Recorded</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Gap</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Detected non-wear</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Used for validity</th>
                    <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #e2e8f0" }}>Valid</th>
                  </tr>
                </thead>
                <tbody>
                  {windows.map((row, index) => {
                    const hours = effectiveHours(row);
                    const valid = hours + 1e-9 >= threshold;
                    return (
                      <tr key={`${row.window_start || row.date}-${index}`}>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", overflowWrap: "anywhere" }}>{row.window_label || row.date}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(row.recorded_hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(row.recording_gap_hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(row.detected_nonwear_hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatHours(hours)}</td>
                        <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right", color: valid ? "#166534" : "#991b1b", fontWeight: 800 }}>{valid ? "Yes" : "No"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.5, marginTop: 10 }}>
              Initial QC is descriptive and occurs before start/stop restrictions and uploaded/manual masks. Final QC is recalculated during analysis.
            </div>
          </>
        )}
      </div>
    </details>
  );
}

export default function PreprocessingPanel({
  title = "2. Pre-processing",
  settings = {},
  onSettingsChange = () => {},
  actigraphyFiles = [],
  initialQcByFile = {},
  initialQcLoadingByFile = {},
  initialQcErrorByFile = {},
  participantFileMode = "separate",
  joinedParticipantKey = "__joined_participant__",
  joinedParticipantLabel = "Joined participant",
}) {
  const resolved = {
    customizeDataQualityThresholds: false,
    validDayWindowMode: "calendar_day",
    minimumValidHoursPerDay: 16,
    minimumValidDaysForRhythm: 2,
    minimumSleepWindowCoverage: 0.8,
    respectNonwear: true,
    ...settings,
  };
  const entries = useMemo(() => {
    if (participantFileMode === "join" && actigraphyFiles.length > 1) {
      const totalSize = actigraphyFiles.reduce((sum, file) => sum + (Number(file?.size) || 0), 0);
      return [{
        key: joinedParticipantKey,
        file: { name: joinedParticipantLabel || `Joined participant (${actigraphyFiles.length} files)`, size: totalSize },
        duplicateCount: 1,
        duplicateIndex: 1,
      }];
    }
    return buildFileEntries(actigraphyFiles);
  }, [actigraphyFiles, participantFileMode, joinedParticipantKey, joinedParticipantLabel]);
  const update = (patch) => onSettingsChange({ ...resolved, ...patch });
  const modeLabel = resolved.validDayWindowMode === "recording_anchored" ? "recording-aligned 24-hour window" : "calendar day";

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 18, lineHeight: 1.55 }}>
        Review initial data coverage, then choose the recommended preprocessing settings or customize them for your protocol or sensitivity analysis.
      </p>

      <div style={{ border: "1px solid #bfdbfe", borderRadius: 16, padding: 16, background: "#eff6ff", marginBottom: 16 }}>
        <div style={{ fontWeight: 800, color: "#1e3a8a", marginBottom: 8 }}>Initial data-coverage QC after file loading</div>
        <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.55, marginBottom: 12 }}>
          {participantFileMode === "join" && actigraphyFiles.length > 1
            ? "The joined participant timeline is inspected as one longitudinal recording, with real timestamp gaps retained as missing data. Expand it for the full table."
            : "Each uploaded recording is inspected before final preprocessing so you can see how much data is present in each candidate quality window. Expand a file for the full table."}
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          {entries.map((entry) => (
            <InitialQcCard
              key={entry.key}
              entry={entry}
              payload={initialQcByFile[entry.key]}
              loading={Boolean(initialQcLoadingByFile[entry.key])}
              error={initialQcErrorByFile[entry.key]}
              settings={resolved}
            />
          ))}
          {entries.length === 0 && <div style={{ color: "#64748b" }}>Upload an actigraphy file in Step 1 to run initial QC.</div>}
        </div>
      </div>

      <div style={{ border: "1px solid #dcfce7", borderRadius: 16, padding: 16, background: "#f0fdf4", marginBottom: 16 }}>
        <div style={{ fontWeight: 800, color: "#14532d", marginBottom: 8 }}>Recommended preprocessing settings</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
          <div style={{ background: "white", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>16 hours per quality window</div>
            <div style={{ color: "#475569", fontSize: 13, marginTop: 4 }}>Recommended minimum analyzable recording time; customizable below.</div>
          </div>
          <div style={{ background: "white", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>2 consecutive valid windows</div>
            <div style={{ color: "#475569", fontSize: 13, marginTop: 4 }}>Recommended minimum uninterrupted run for multi-day rhythm metrics and SRI eligibility.</div>
          </div>
          <div style={{ background: "white", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>
              <BubbleInfo
                label="80% sleep-window coverage"
                content="Sleep-window coverage is the proportion of expected epochs inside a diary or estimated sleep window that remain recorded and scorable after recording gaps, detected non-wear, and manual masks. A window below the configured threshold is excluded from TST, WASO, sleep efficiency, and other window-dependent summaries rather than being treated as complete data."
              />
            </div>
            <div style={{ color: "#475569", fontSize: 13, marginTop: 4 }}>Recommended minimum retained/scorable data within each sleep window.</div>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>How should a valid 24-hour period be defined?</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 10 }}>
          <label style={{ display: "block", border: resolved.validDayWindowMode === "calendar_day" ? "2px solid #2563eb" : "1px solid #cbd5e1", borderRadius: 14, padding: 13, cursor: "pointer", background: resolved.validDayWindowMode === "calendar_day" ? "#eff6ff" : "white" }}>
            <input type="radio" name="validDayWindowMode" checked={resolved.validDayWindowMode === "calendar_day"} onChange={() => update({ validDayWindowMode: "calendar_day" })} />
            <span style={{ marginLeft: 8, fontWeight: 800 }}>Calendar day (recommended)</span>
            <span style={{ display: "block", color: "#475569", fontSize: 13, lineHeight: 1.5, marginTop: 6 }}>Midnight-to-midnight windows preserve clock-day interpretation for daily summaries, L5/M10 timing, and day-level reporting.</span>
          </label>
          <label style={{ display: "block", border: resolved.validDayWindowMode === "recording_anchored" ? "2px solid #2563eb" : "1px solid #cbd5e1", borderRadius: 14, padding: 13, cursor: "pointer", background: resolved.validDayWindowMode === "recording_anchored" ? "#eff6ff" : "white" }}>
            <input type="radio" name="validDayWindowMode" checked={resolved.validDayWindowMode === "recording_anchored"} onChange={() => update({ validDayWindowMode: "recording_anchored" })} />
            <span style={{ marginLeft: 8, fontWeight: 800 }}>Recording-aligned 24-hour windows</span>
            <span style={{ display: "block", color: "#475569", fontSize: 13, lineHeight: 1.5, marginTop: 6 }}>Starts at the first retained timestamp. Useful as a sensitivity option for short recordings or protocols intentionally anchored to device deployment time.</span>
          </label>
        </div>
        <div style={{ marginTop: 10, border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e", borderRadius: 12, padding: 11, fontSize: 13, lineHeight: 1.55 }}>
          Example: a complete 4 PM-to-4 PM recording produces an 8-hour first calendar day and a 16-hour second calendar day, so the second day meets a 16-hour threshold. Recording-aligned mode instead treats the same recording as one full 24-hour quality window. Results and exports state which basis was used.
        </div>
      </div>

      <label style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 13, borderRadius: 12, border: "1px solid #dbeafe", background: "#eff6ff", marginBottom: 14 }}>
        <input type="checkbox" checked={Boolean(resolved.respectNonwear)} onChange={(event) => update({ respectNonwear: event.target.checked })} style={{ marginTop: 3 }} />
        <span>
          <span style={{ display: "block", fontWeight: 700, color: "#1e3a8a" }}>Respect detected or mapped non-wear (recommended)</span>
          <span style={{ display: "block", marginTop: 3, color: "#475569", fontSize: 13, lineHeight: 1.5 }}>Non-wear and missing epochs remain unavailable and are never converted to zero activity. Additional manual exclusions can be added on the Cleaning and Masking page.</span>
        </span>
      </label>

      <label style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 13, borderRadius: 12, border: "1px solid #dbeafe", background: "#eff6ff" }}>
        <input type="checkbox" checked={Boolean(resolved.customizeDataQualityThresholds)} onChange={(event) => update({ customizeDataQualityThresholds: event.target.checked })} style={{ marginTop: 3 }} />
        <span>
          <span style={{ display: "block", fontWeight: 700, color: "#1e3a8a" }}>Customize the recommended data-quality thresholds</span>
          <span style={{ display: "block", marginTop: 3, color: "#475569", fontSize: 13, lineHeight: 1.5 }}>Leave this off to use the recommended 16 hours, 2 consecutive valid windows, and 80% sleep-window coverage. Enable it when your protocol or sensitivity analysis requires different criteria.</span>
        </span>
      </label>

      {resolved.customizeDataQualityThresholds ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc" }}>
          <NumberField label="Recommended minimum valid hours per quality window" value={resolved.minimumValidHoursPerDay} onChange={(value) => update({ minimumValidHoursPerDay: value })} min="1" max="24" step="0.5" help={`Allowed range: 1–24 hours. A ${modeLabel} below this amount is invalid for day/window-based summaries.`} />
          <NumberField label="Recommended minimum consecutive valid windows for rhythm/SRI" value={resolved.minimumValidDaysForRhythm} onChange={(value) => update({ minimumValidDaysForRhythm: value })} min="1" max="365" step="1" help="Valid quality windows must form one uninterrupted run; separated valid windows do not satisfy this rule." />
          <NumberField label="Recommended minimum sleep-window coverage" value={resolved.minimumSleepWindowCoverage} onChange={(value) => update({ minimumSleepWindowCoverage: value })} min="0" max="1" step="0.05" help="Enter a proportion from 0 to 1. For example, 0.8 means at least 80% of expected epochs must remain scorable." info="This threshold is calculated separately for each sleep window. Expected epochs are compared with recorded and scorable epochs after gaps, non-wear, start/stop truncation, and masks are applied. Windows below the threshold are reported as unavailable rather than imputed." />
        </div>
      ) : (
        <div style={{ marginTop: 14, color: "#166534", fontSize: 13, fontWeight: 800 }}>
          Recommended thresholds active: 16 h/{modeLabel} · 2 consecutive valid windows · 80% sleep-window coverage
        </div>
      )}
    </div>
  );
}
