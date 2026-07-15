import React from "react";

export const ACTIVITY_MAPPING_OPTIONS = [
  {
    id: "original",
    label: "Original / device activity",
    units: "",
    description: "Preserves the file's existing activity signal or the reader's normal default.",
  },
  {
    id: "enmo",
    label: "ENMO",
    units: "mg",
    description: "Euclidean Norm Minus One from calibrated X/Y/Z acceleration, averaged into 30-second epochs.",
  },
  {
    id: "mad",
    label: "MAD",
    units: "mg",
    description: "Mean amplitude deviation of vector magnitude within each 30-second epoch.",
  },
];

export function activityMappingLabel(value) {
  const option = ACTIVITY_MAPPING_OPTIONS.find((item) => item.id === value) || ACTIVITY_MAPPING_OPTIONS[0];
  return option.units ? `${option.label} (${option.units})` : option.label;
}

export default function ActivityMappingPanel({
  value = "original",
  onChange = () => {},
  compact = false,
}) {
  const selected = ACTIVITY_MAPPING_OPTIONS.find((item) => item.id === value) || ACTIVITY_MAPPING_OPTIONS[0];

  return (
    <div
      style={{
        border: "1px solid #bfdbfe",
        borderRadius: compact ? 12 : 16,
        padding: compact ? 12 : 16,
        background: "#eff6ff",
      }}
    >
      <div style={{ fontWeight: 800, marginBottom: 6 }}>Activity mapping</div>
      <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.5, marginBottom: 10 }}>
        ENMO and MAD are available for raw GENEActiv <code>.bin</code> and raw ActiGraph <code>.gt3x</code> files. ENMO may also be available in Oxford accelerometer time-series files. Unsupported mappings return a clear file-level error rather than substituting another signal.
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
      {value !== "original" && (
        <div style={{ color: "#9a3412", fontSize: 12, marginTop: 8, lineHeight: 1.45 }}>
          Sleep-scoring thresholds originally validated for device counts may not transfer directly to {activityMappingLabel(value)}. Circadian and non-parametric metrics can still be calculated, but threshold-based results should be interpreted with the selected mapping in mind.
        </div>
      )}
    </div>
  );
}
