import React from "react";

/** Available only for current-session analyses with the original upload File objects. */
export default function ProcessedActivityDownload({ batchResults = [], onDownload, downloadState = {} }) {
  const completed = batchResults
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => ["completed", "completed_with_warnings"].includes(item?.status));
  if (!completed.length) return null;
  return (
    <div style={{ border: "1px solid #cbd5e1", borderRadius: 14, padding: 16, background: "#f8fafc", marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <strong>Download Preprocessed Activity Data</strong>
        <span title="Download epoch-by-epoch activity after your selected filtering, magnitude and normalization, with both pre-QC and analysis-eligible values, timestamps, masks, non-wear and selected-interval flags, plus a JSON processing manifest. Recreates the output from the original uploaded files and the saved settings for this completed run." tabIndex={0} aria-label="Information about preprocessed data export" style={{ border: "1px solid #64748b", borderRadius: "100%", display: "inline-flex", alignItems: "center", justifyContent: "center", width: 19, height: 19, fontSize: 12, fontWeight: 800, cursor: "help" }}>i</span>
      </div>
      <p style={{ color: "#475569", fontSize: 13, margin: "7px 0 12px", lineHeight: 1.6 }}>
        Download a ZIP with a full-resolution <strong>epoch-level CSV</strong> and a <strong>processing settings and methods JSON</strong>. Blank analysis values indicate excluded epochs, not zero activity. Each completed recording is exported separately; joined-participant analyses produce one continuous timeline with gaps preserved.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {completed.map(({ item, index }) => {
          const running = downloadState?.index === index && downloadState?.status === "running";
          const unavailable = !item.exportContext?.files?.length;
          return (
            <button
              key={`${index}-${item.fileName}`}
              type="button"
              disabled={running || downloadState?.status === "running" || unavailable}
              title={unavailable ? "The original uploaded files are not available in this session. Re-upload and rerun the analysis before exporting." : `Export the processed time series for ${item.fileName}`}
              onClick={() => onDownload(item, index)}
              style={{ padding: "10px 13px", background: running ? "#e2e8f0" : "white", border: "1px solid #94a3b8", borderRadius: 10, color: "#0f172a", cursor: running || unavailable ? "not-allowed" : "pointer", fontWeight: 650, textAlign: "left" }}
            >
              {running ? "Preparing export…" : `↓ ${item.fileName}`}
            </button>
          );
        })}
      </div>
      {downloadState?.status === "running" && (
        <p role="status" style={{ color: "#334155", fontSize: 13, margin: "10px 0 0" }}>{downloadState.message || "Preparing the CSV and settings manifest…"}</p>
      )}
      {downloadState?.status === "error" && (
        <p role="alert" style={{ color: "#b91c1c", fontSize: 13, margin: "10px 0 0" }}>{downloadState.message}</p>
      )}
      {downloadState?.status === "complete" && (
        <p role="status" style={{ color: "#065f46", fontSize: 13, margin: "10px 0 0" }}>Download ready. The export includes the preprocessing/QC settings from that completed analysis.</p>
      )}
    </div>
  );
}
