import React from "react";

function palette(severity) {
  if (severity === "strong_warning") {
    return { border: "#fdba74", background: "#fff7ed", color: "#9a3412", title: "Strong sampling-rate warning" };
  }
  if (severity === "warning") {
    return { border: "#fde68a", background: "#fffbeb", color: "#92400e", title: "Sampling-rate warning" };
  }
  return { border: "#bfdbfe", background: "#eff6ff", color: "#1e3a8a", title: "Different native sampling rates detected" };
}

function formatRate(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "Unknown";
  return `${Number(number.toFixed(3))} Hz`;
}

export default function SamplingHarmonizationNotice({ harmonization, compact = false }) {
  if (!harmonization?.native_rates_differ || !harmonization?.message) return null;

  const theme = palette(harmonization.severity);
  const sourceRates = harmonization.source_rates || [];
  const epochSeconds = Number(harmonization.processed_epoch_seconds);

  return (
    <div
      style={{
        border: `1px solid ${theme.border}`,
        borderRadius: 14,
        padding: 13,
        background: theme.background,
        color: theme.color,
        fontSize: 13,
        lineHeight: 1.55,
        marginBottom: 14,
      }}
    >
      <div style={{ fontWeight: 800, marginBottom: 5 }}>{theme.title}</div>
      <div>{harmonization.message}</div>
      <div style={{ marginTop: 8, fontWeight: 700 }}>
        Analytical epoch: {Number.isFinite(epochSeconds) ? `${Number(epochSeconds.toFixed(3))} s` : "common epoch"}
        {harmonization.raw_frequency_resampled === false ? " · raw Hz not resampled" : ""}
      </div>
      {!compact && sourceRates.length > 0 && (
        <div style={{ marginTop: 9, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 520 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 6, borderBottom: `1px solid ${theme.border}` }}>Source</th>
                <th style={{ textAlign: "right", padding: 6, borderBottom: `1px solid ${theme.border}` }}>Native rate</th>
                <th style={{ textAlign: "left", padding: 6, borderBottom: `1px solid ${theme.border}` }}>Activity basis</th>
              </tr>
            </thead>
            <tbody>
              {sourceRates.map((item, index) => (
                <tr key={`${item.source_file || "source"}-${index}`}>
                  <td style={{ padding: 6, borderTop: `1px solid ${theme.border}`, overflowWrap: "anywhere" }}>{item.source_file || `Source ${index + 1}`}</td>
                  <td style={{ padding: 6, borderTop: `1px solid ${theme.border}`, textAlign: "right" }}>{formatRate(item.native_sample_rate_hz)}</td>
                  <td style={{ padding: 6, borderTop: `1px solid ${theme.border}` }}>{item.activity_basis || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
