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
        style={{ width: "100%", padding: "10px 11px", borderRadius: 10, border: "1px solid #cbd5e1", boxSizing: "border-box" }}
      />
      <div style={{ color: "#64748b", fontSize: 12, marginTop: 5, lineHeight: 1.45 }}>{help}</div>
    </label>
  );
}

export default function PreprocessingPanel({
  title = "2. Pre-processing",
  settings = {},
  onSettingsChange = () => {},
}) {
  const resolved = {
    customizeDataQualityThresholds: false,
    minimumValidHoursPerDay: 16,
    minimumValidDaysForRhythm: 2,
    minimumSleepWindowCoverage: 0.8,
    respectNonwear: true,
    ...settings,
  };

  const update = (patch) => onSettingsChange({ ...resolved, ...patch });

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 18, lineHeight: 1.55 }}>
        Define the recording-quality rules used before activity, rhythm, and sleep metrics are calculated. The standard values remain active unless you explicitly enable customization.
      </p>

      <div style={{ border: "1px solid #dcfce7", borderRadius: 16, padding: 16, background: "#f0fdf4", marginBottom: 16 }}>
        <div style={{ fontWeight: 800, color: "#14532d", marginBottom: 8 }}>Project-standard preprocessing rules</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
          <div style={{ background: "white", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>16 hours/day</div>
            <div style={{ color: "#475569", fontSize: 13, marginTop: 4 }}>Minimum analyzable recording time for a valid calendar day.</div>
          </div>
          <div style={{ background: "white", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>2 consecutive days</div>
            <div style={{ color: "#475569", fontSize: 13, marginTop: 4 }}>Minimum uninterrupted run for multi-day rhythm metrics and SRI eligibility.</div>
          </div>
          <div style={{ background: "white", border: "1px solid #bbf7d0", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>
              <BubbleInfo
                label="80% sleep-window coverage"
                content="Sleep-window coverage is the proportion of expected epochs inside a diary or estimated sleep window that remain recorded and scorable after recording gaps, detected non-wear, and manual masks. A window below the configured threshold is excluded from TST, WASO, sleep efficiency, and other window-dependent summaries rather than being treated as complete data."
              />
            </div>
            <div style={{ color: "#475569", fontSize: 13, marginTop: 4 }}>Minimum retained/scorable data within each sleep window.</div>
          </div>
        </div>
      </div>

      <label style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 13, borderRadius: 12, border: "1px solid #dbeafe", background: "#eff6ff", marginBottom: 14 }}>
        <input
          type="checkbox"
          checked={Boolean(resolved.respectNonwear)}
          onChange={(event) => update({ respectNonwear: event.target.checked })}
          style={{ marginTop: 3 }}
        />
        <span>
          <span style={{ display: "block", fontWeight: 700, color: "#1e3a8a" }}>Respect detected or mapped non-wear</span>
          <span style={{ display: "block", marginTop: 3, color: "#475569", fontSize: 13, lineHeight: 1.5 }}>
            Non-wear and missing epochs remain unavailable and are never converted to zero activity. Additional manual exclusions can be added on the Cleaning and Masking page.
          </span>
        </span>
      </label>

      <label style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: 13, borderRadius: 12, border: "1px solid #dbeafe", background: "#eff6ff" }}>
        <input
          type="checkbox"
          checked={Boolean(resolved.customizeDataQualityThresholds)}
          onChange={(event) => update({ customizeDataQualityThresholds: event.target.checked })}
          style={{ marginTop: 3 }}
        />
        <span>
          <span style={{ display: "block", fontWeight: 700, color: "#1e3a8a" }}>Modify the standard data-quality thresholds</span>
          <span style={{ display: "block", marginTop: 3, color: "#475569", fontSize: 13, lineHeight: 1.5 }}>
            Leave this off to use 16 hours, 2 consecutive days, and 80% coverage. Enable it only when a study protocol or sensitivity analysis requires different rules.
          </span>
        </span>
      </label>

      {resolved.customizeDataQualityThresholds ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginTop: 16, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc" }}>
          <NumberField
            label="Minimum valid hours per day"
            value={resolved.minimumValidHoursPerDay}
            onChange={(value) => update({ minimumValidHoursPerDay: value })}
            min="1"
            max="24"
            step="0.5"
            help="Allowed range: 1–24 hours. A calendar day below this amount is invalid for day-based summaries."
          />
          <NumberField
            label="Minimum consecutive valid days for rhythm/SRI"
            value={resolved.minimumValidDaysForRhythm}
            onChange={(value) => update({ minimumValidDaysForRhythm: value })}
            min="1"
            max="365"
            step="1"
            help="Days must form one uninterrupted calendar-day run; separated valid days do not satisfy this rule."
          />
          <NumberField
            label="Minimum sleep-window coverage"
            value={resolved.minimumSleepWindowCoverage}
            onChange={(value) => update({ minimumSleepWindowCoverage: value })}
            min="0"
            max="1"
            step="0.05"
            help="Enter a proportion from 0 to 1. For example, 0.8 means at least 80% of expected epochs must remain scorable."
            info="This threshold is calculated separately for each sleep window. Expected epochs are compared with recorded and scorable epochs after gaps, non-wear, start/stop truncation, and masks are applied. Windows below the threshold are reported as unavailable rather than imputed."
          />
        </div>
      ) : (
        <div style={{ marginTop: 14, color: "#166534", fontSize: 13, fontWeight: 800 }}>
          Standard thresholds active: 16 h/day · 2 consecutive valid days · 80% sleep-window coverage
        </div>
      )}
    </div>
  );
}
