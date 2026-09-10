import React, { useState } from "react";

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
        style={{ width: "100%", padding: "10px 11px", borderRadius: 10, border: "1px solid #cbd5e1", boxSizing: "border-box", background: "white", color: "#0f172a" }}
      />
      <div style={{ color: "#64748b", fontSize: 12, marginTop: 5, lineHeight: 1.45 }}>{help}</div>
    </label>
  );
}

export function resolveAnalysisSettings(settings = {}) {
  return {
    customizeDataQualityThresholds: false,
    validDayWindowMode: "calendar_day",
    minimumValidHoursPerDay: 16,
    minimumValidDaysForRhythm: 2,
    minimumSleepWindowCoverage: 0.8,
    respectNonwear: true,
    ...settings,
  };
}

export default function AnalysisSettingsPanel({ settings = {}, onSettingsChange = () => {} }) {
  const resolved = resolveAnalysisSettings(settings);
  const update = (patch) => onSettingsChange({ ...resolved, ...patch });
  const modeLabel = resolved.validDayWindowMode === "recording_anchored" ? "recording-aligned 24-hour window" : "calendar day";

  return (
    <div style={{ border: "1px solid #dbeafe", borderRadius: 16, padding: 16, background: "#f8fbff", marginBottom: 20 }}>
      <div style={{ fontWeight: 800, color: "#1e3a8a", marginBottom: 6, fontSize: 17 }}>Analysis settings</div>
      <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.55, marginBottom: 16 }}>
        Use the recommended data-quality settings below, or customize them for your study protocol or sensitivity analysis. These settings are applied during final analysis and are reported in exported provenance.
      </div>

      <div style={{ border: "1px solid #dcfce7", borderRadius: 16, padding: 16, background: "#f0fdf4", marginBottom: 16 }}>
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
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "white" }}>
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
