import React from "react";

export const ACTIVITY_MAPPING_OPTIONS = [
  {
    id: "auto",
    label: "Recommended source / processed `acc`",
    units: "",
    description: "Uses source/device activity when the file already contains it. Raw .bin, .cwa, and .gt3x files use the epoch-level accelerometer `acc` activity basis.",
  },
  {
    id: "accelerometer",
    label: "Processed acceleration (`acc` basis)",
    units: "mg",
    description: "Uses the Oxford accelerometer `acc` column when available; large raw files use the compatible memory-safe processed-acceleration path recorded in diagnostics.",
  },
  {
    id: "mad",
    label: "MAD",
    units: "mg",
    description: "Mean amplitude deviation of vector magnitude within each 30-second epoch. Available only when raw X/Y/Z samples or a MAD column are available.",
  },
  {
    id: "enmo",
    label: "ENMO",
    units: "mg",
    description: "Uses the epoch mean of positive Euclidean Norm Minus One from calibrated vector magnitude.",
  },
  {
    id: "pim",
    label: "PIM",
    units: "mg·s/epoch",
    description: "Proportional-integrating mode. Integrates the absolute dynamic vector-magnitude signal across each epoch, preserving movement intensity and duration.",
  },
  {
    id: "zcm",
    label: "ZCM",
    units: "crossings/epoch",
    description: "Counts level crossings of a positive threshold in unfiltered |vector magnitude - 1 g|, emphasizing movement frequency.",
  },
  {
    id: "tat",
    label: "TAT",
    units: "s/epoch",
    description: "Time above threshold. Reports the seconds per epoch for which unfiltered |vector magnitude - 1 g| exceeds the selected threshold.",
  },
];

export function activityMappingLabel(value) {
  const option = ACTIVITY_MAPPING_OPTIONS.find((item) => item.id === value) || ACTIVITY_MAPPING_OPTIONS[0];
  return option.units ? `${option.label} (${option.units})` : option.label;
}

export default function ActivityMappingPanel({
  value = "auto",
  onChange = () => {},
  compact = false,
  context = "analysis",
  title = "",
  signalSettings = { thresholdMethod: "adaptive", thresholdMg: 4 },
  onSignalSettingsChange = () => {},
}) {
  const selected = ACTIVITY_MAPPING_OPTIONS.find((item) => item.id === value) || ACTIVITY_MAPPING_OPTIONS[0];
  const isPreview = context === "preview";

  return (
    <div
      style={{
        border: "1px solid #bfdbfe",
        borderRadius: compact ? 12 : 16,
        padding: compact ? 12 : 16,
        background: "#eff6ff",
      }}
    >
      {title && !compact && <h2 style={{ marginTop: 0, marginBottom: 10 }}>{title}</h2>}
      <div style={{ fontWeight: 800, marginBottom: 6 }}>
        {isPreview ? "Preview activity signal" : "Activity representation / metric"}
      </div>
      <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.5, marginBottom: 10 }}>
        {isPreview
          ? "This only controls the plotted preview. It does not change the activity basis selected later for analysis."
          : "Choose one of seven supported activity representations. Raw-signal processing is metric-specific; the resulting epoch-level series becomes the basis for the selected rest/activity analyses."}
      </div>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={{
          width: "100%",
          padding: "10px 12px",
          borderRadius: 10,
          border: "1px solid #93c5fd",
          background: "white",
          fontWeight: 700,
        }}
      >
        {ACTIVITY_MAPPING_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>{activityMappingLabel(option.id)}</option>
        ))}
      </select>
      <div style={{ color: "#1e3a8a", fontSize: 13, marginTop: 8, lineHeight: 1.45 }}>
        {selected.description}
      </div>
      {["zcm", "tat"].includes(value) && !isPreview && (
        <div style={{ marginTop: 14, padding: 12, border: "1px solid #fdba74", borderRadius: 12, background: "#fff7ed" }}>
          <div style={{ fontWeight: 800, color: "#9a3412", marginBottom: 8 }}>Threshold definition</div>
          <label style={{ display: "block", color: "#7c2d12", fontSize: 13, lineHeight: 1.5 }}>
            Method
            <select
              value={signalSettings?.thresholdMethod || "adaptive"}
              onChange={(event) => onSignalSettingsChange({ ...signalSettings, thresholdMethod: event.target.value })}
              style={{ display: "block", width: "100%", marginTop: 5, padding: "9px 10px", borderRadius: 9, border: "1px solid #fdba74", background: "white" }}
            >
              <option value="adaptive">Adaptive (SD of the recording)</option>
              <option value="fixed">Fixed threshold</option>
            </select>
          </label>
          {signalSettings?.thresholdMethod === "fixed" && (
            <label style={{ display: "block", color: "#7c2d12", fontSize: 13, lineHeight: 1.5, marginTop: 10 }}>
              Threshold (mg)
              <input
                type="number"
                min="0"
                step="0.1"
                value={signalSettings?.thresholdMg ?? ""}
                onChange={(event) => onSignalSettingsChange({ ...signalSettings, thresholdMg: event.target.value })}
                style={{ display: "block", width: "100%", boxSizing: "border-box", marginTop: 5, padding: "9px 10px", borderRadius: 9, border: "1px solid #fdba74", background: "white" }}
              />
            </label>
          )}
          <div style={{ color: "#9a3412", fontSize: 12, lineHeight: 1.45, marginTop: 8 }}>
            Adaptive uses one recording-level SD threshold and requires a second streaming pass through raw data. Joined-participant ZCM/TAT requires a fixed threshold so every source uses the same definition.
          </div>
        </div>
      )}
      {["auto", "accelerometer", "mad", "enmo", "pim", "zcm", "tat"].includes(value) && !isPreview && (
        <div style={{ color: "#9a3412", fontSize: 12, marginTop: 8, lineHeight: 1.45 }}>
          Thresholds are tied to the selected signal scale (counts, mg, mg·s/epoch, crossings/epoch, or s/epoch). The chosen value and binarization setting are retained with the analysis configuration.
        </div>
      )}
    </div>
  );
}
