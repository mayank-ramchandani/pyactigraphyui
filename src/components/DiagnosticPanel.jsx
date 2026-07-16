import React from "react";

function formatNumber(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits).replace(/\.?0+$/, "") : "—";
}

function statusColor(status) {
  const normalized = String(status || "").toLowerCase();
  if (["passed", "completed"].includes(normalized)) return "#166534";
  if (["warning", "completed_with_warnings"].includes(normalized)) return "#9a3412";
  if (["failed", "error"].includes(normalized)) return "#991b1b";
  return "#475569";
}

function downloadDiagnostics(diagnostics, fileName = "diagnostics.json") {
  const blob = new Blob([JSON.stringify(diagnostics, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName.replace(/[^a-zA-Z0-9._-]+/g, "_");
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function ErrorDetails({ error, label = "Error" }) {
  if (!error) return null;
  return (
    <details style={{ marginTop: 8, border: "1px solid #fecaca", borderRadius: 10, padding: 10, background: "#fff7f7" }}>
      <summary style={{ cursor: "pointer", fontWeight: 700, color: "#991b1b" }}>
        {label}: {error.type || "Error"} · {error.message || "No message"}
      </summary>
      {error.traceback && (
        <pre style={{ margin: "10px 0 0", whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 300, overflowY: "auto", fontSize: 12 }}>
          {error.traceback}
        </pre>
      )}
    </details>
  );
}

export default function DiagnosticPanel({ diagnostics, title = "Diagnostic report", fileName = "diagnostics.json" }) {
  if (!diagnostics) {
    return (
      <div style={{ border: "1px dashed #cbd5e1", borderRadius: 12, padding: 12, color: "#64748b", marginTop: 12 }}>
        No structured backend diagnostics were returned. For a 413, gateway timeout, or container termination, check the client transport diagnostic and Azure/Nginx logs.
      </div>
    );
  }

  const stages = Array.isArray(diagnostics.stages) ? diagnostics.stages : [];
  const input = diagnostics.input_file || diagnostics.inputFile || {};
  const recording = diagnostics.recording || {};
  const data = recording.data || {};
  const activity = data.activity || {};
  const transport = diagnostics.transport || {};
  const raStage = stages.find((stage) => stage?.name === "metric.ra");
  const raComponents = raStage?.details?.ra_components || null;
  const sleepWindowStage = stages.find((stage) => stage?.name === "sleep.window_detection");
  const sleepWindowDetails = sleepWindowStage?.details || null;

  return (
    <div style={{ border: "1px solid #cbd5e1", borderRadius: 14, padding: 12, background: "#f8fafc", marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 800 }}>{title}</div>
          <div style={{ color: "#64748b", fontSize: 12, marginTop: 3 }}>
            Request ID: <code>{diagnostics.request_id || "not available (request may not have reached backend)"}</code>
          </div>
        </div>
        <button
          type="button"
          onClick={() => downloadDiagnostics(diagnostics, fileName)}
          style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #94a3b8", background: "white", cursor: "pointer", fontWeight: 700 }}
        >
          Download diagnostic JSON
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8, marginTop: 12 }}>
        <div><strong>Status:</strong> <span style={{ color: statusColor(diagnostics.status), fontWeight: 700 }}>{diagnostics.status || "unknown"}</span></div>
        <div><strong>Endpoint:</strong> {diagnostics.endpoint || transport.endpoint || "—"}</div>
        <div><strong>Total runtime:</strong> {formatNumber(diagnostics.total_duration_seconds)} s</div>
        <div><strong>File size:</strong> {input.size_mb != null ? `${formatNumber(input.size_mb)} MB` : transport.file_size_mb != null ? `${formatNumber(transport.file_size_mb)} MB` : "—"}</div>
        <div><strong>Reader:</strong> {transport.detected_input_type || recording.class || "—"}</div>
        <div><strong>Rows:</strong> {data?.index?.rows ?? activity.rows ?? "—"}</div>
        <div><strong>Valid activity rows:</strong> {activity.valid_rows ?? "—"}</div>
        <div><strong>Missing activity:</strong> {activity.missing_percent != null ? `${formatNumber(activity.missing_percent)}%` : "—"}</div>
      </div>

      {input.sha256 && (
        <div style={{ color: "#475569", fontSize: 12, marginTop: 10, overflowWrap: "anywhere" }}>
          <strong>SHA-256:</strong> <code>{input.sha256}</code>
        </div>
      )}

      {transport.message && (
        <div style={{ marginTop: 10, padding: 10, borderRadius: 10, background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412" }}>
          <strong>Transport failure:</strong> {transport.message}
          {transport.http_status ? ` (HTTP ${transport.http_status})` : ""}
          {transport.response_preview ? <div style={{ marginTop: 6, overflowWrap: "anywhere" }}>Response: {transport.response_preview}</div> : null}
        </div>
      )}

      <ErrorDetails error={diagnostics.error} label="Request error" />

      {raComponents && (
        <div style={{ marginTop: 12, padding: 11, borderRadius: 10, background: raComponents.ra_at_upper_boundary ? "#fff7ed" : "#f0fdf4", border: `1px solid ${raComponents.ra_at_upper_boundary ? "#fed7aa" : "#bbf7d0"}`, fontSize: 13 }}>
          <div style={{ fontWeight: 800, color: raComponents.ra_at_upper_boundary ? "#9a3412" : "#166534" }}>
            RA calculation details
          </div>
          <div style={{ marginTop: 5, display: "flex", gap: 14, flexWrap: "wrap" }}>
            <span><strong>RA:</strong> {formatNumber(raComponents.ra)}</span>
            <span><strong>M10:</strong> {formatNumber(raComponents.m10)}</span>
            <span><strong>L5:</strong> {formatNumber(raComponents.l5)}</span>
            <span><strong>Binarized:</strong> {raComponents.binarize ? "Yes" : "No"}</span>
            <span><strong>Threshold:</strong> {formatNumber(raComponents.threshold)}</span>
          </div>
          {raComponents.ra_at_upper_boundary && (
            <div style={{ marginTop: 5, color: "#9a3412" }}>RA equals 1 because L5 is zero while M10 is positive. Review the mapping, units, binarization, and threshold before interpreting it.</div>
          )}
        </div>
      )}

      {sleepWindowDetails && (
        <div style={{ marginTop: 10, padding: 11, borderRadius: 10, background: sleepWindowDetails.window_count > 0 ? "#f0fdf4" : "#fff7ed", border: `1px solid ${sleepWindowDetails.window_count > 0 ? "#bbf7d0" : "#fed7aa"}`, fontSize: 13 }}>
          <div style={{ fontWeight: 800, color: sleepWindowDetails.window_count > 0 ? "#166534" : "#9a3412" }}>Sleep-window detection</div>
          <div style={{ marginTop: 5 }}>
            <strong>Method:</strong> {sleepWindowDetails.method || "—"} · <strong>Windows:</strong> {sleepWindowDetails.window_count ?? 0}
          </div>
          {Array.isArray(sleepWindowDetails.notes) && sleepWindowDetails.notes.length > 0 && (
            <div style={{ marginTop: 5, color: "#475569" }}>{sleepWindowDetails.notes.join(" ")}</div>
          )}
        </div>
      )}

      {stages.length > 0 && (
        <details open style={{ marginTop: 12 }}>
          <summary style={{ cursor: "pointer", fontWeight: 800 }}>Pipeline stages ({stages.length})</summary>
          <div style={{ overflowX: "auto", marginTop: 8 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 820, fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: 7, borderBottom: "1px solid #cbd5e1" }}>Stage</th>
                  <th style={{ textAlign: "left", padding: 7, borderBottom: "1px solid #cbd5e1" }}>Category</th>
                  <th style={{ textAlign: "left", padding: 7, borderBottom: "1px solid #cbd5e1" }}>Status</th>
                  <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #cbd5e1" }}>Time</th>
                  <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #cbd5e1" }}>RSS after</th>
                  <th style={{ textAlign: "right", padding: 7, borderBottom: "1px solid #cbd5e1" }}>RSS Δ</th>
                  <th style={{ textAlign: "left", padding: 7, borderBottom: "1px solid #cbd5e1" }}>Outcome/error</th>
                </tr>
              </thead>
              <tbody>
                {stages.map((stage, index) => {
                  const suppressed = stage.suppressed_errors || [];
                  const outcome = stage.error?.message || stage.details?.outcome || (suppressed.length ? `${suppressed.length} suppressed exception(s)` : "");
                  return (
                    <tr key={stage.id || `${stage.name}-${index}`}>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", fontWeight: 700 }}>{stage.name}</td>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0" }}>{stage.category}</td>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", color: statusColor(stage.status), fontWeight: 700 }}>{stage.status}</td>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{formatNumber(stage.duration_seconds)} s</td>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{stage.memory_after?.rss_mb != null ? `${formatNumber(stage.memory_after.rss_mb)} MB` : "—"}</td>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", textAlign: "right" }}>{stage.rss_change_mb != null ? `${formatNumber(stage.rss_change_mb)} MB` : "—"}</td>
                      <td style={{ padding: 7, borderTop: "1px solid #e2e8f0", color: stage.status === "failed" ? "#991b1b" : "#475569", overflowWrap: "anywhere" }}>{outcome || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {stages.map((stage, index) => {
            const suppressed = stage.suppressed_errors || [];
            if (!stage.error && suppressed.length === 0) return null;
            return (
              <details key={`errors-${stage.id || index}`} style={{ marginTop: 8, border: "1px solid #e2e8f0", borderRadius: 10, padding: 9, background: "white" }}>
                <summary style={{ cursor: "pointer", fontWeight: 700 }}>{stage.name}: detailed errors</summary>
                <ErrorDetails error={stage.error} label="Stage error" />
                {suppressed.map((error, errorIndex) => (
                  <ErrorDetails key={`${error.operation}-${errorIndex}`} error={error} label={`Suppressed in ${error.operation || "operation"}`} />
                ))}
              </details>
            );
          })}
        </details>
      )}

      <details style={{ marginTop: 12 }}>
        <summary style={{ cursor: "pointer", fontWeight: 800 }}>Recording and runtime metadata</summary>
        <pre style={{ margin: "8px 0 0", padding: 10, borderRadius: 10, background: "#0f172a", color: "#e2e8f0", whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 420, overflowY: "auto", fontSize: 11 }}>
          {JSON.stringify({ input_file: diagnostics.input_file, recording: diagnostics.recording, environment: diagnostics.environment, events: diagnostics.events }, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export { downloadDiagnostics };
