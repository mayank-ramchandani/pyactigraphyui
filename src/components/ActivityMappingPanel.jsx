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
    label: "Custom ENMO (legacy)",
    units: "mg",
    description: "Retains the earlier direct ENMO mapping for comparison. The recommended processed `acc` option should normally be used for raw recordings.",
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
        {isPreview ? "Preview activity signal" : "Activity metric / magnitude of acceleration"}
      </div>
      <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.5, marginBottom: 10 }}>
        {isPreview
          ? "This only controls the plotted preview. It does not change the activity basis selected later for analysis."
          : "Choose one of four supported activity-basis options. The selected epoch-level series becomes the basis for all chosen rest/activity metrics and is also used as the initial Activity Preview setting."}
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
      {["auto", "accelerometer", "mad", "enmo"].includes(value) && !isPreview && (
        <div style={{ color: "#9a3412", fontSize: 12, marginTop: 8, lineHeight: 1.45 }}>
          Count-based thresholds are not automatically equivalent to mg. For RA, IS, IV, M10, and L5, continuous analysis without count binarization is usually the clearer starting point.
        </div>
      )}
    </div>
  );
}
