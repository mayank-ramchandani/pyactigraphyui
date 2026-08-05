import React, { useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}

function formatDate(value) {
  if (!value) return "Unknown time";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 ** 2)).toFixed(2)} MB`;
}

function categoryLabel(value) {
  const labels = {
    issue: "Issue / bug",
    suggestion: "Suggestion",
    question: "Question",
    other: "Other",
  };
  return labels[value] || value || "Uncategorized";
}

export default function FeedbackAdminPanel() {
  const [token, setToken] = useState(() => window.sessionStorage.getItem("feedbackAdminToken") || "");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [records, setRecords] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const categorySummary = useMemo(() => {
    const entries = Object.entries(metadata?.category_counts || {});
    return entries.sort((a, b) => b[1] - a[1]);
  }, [metadata]);

  const authHeaders = () => ({ "X-Feedback-Admin-Token": token.trim() });

  const loadFeedback = async () => {
    if (!token.trim()) {
      setStatus("Enter the FEEDBACK_ADMIN_TOKEN configured on the backend.");
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      window.sessionStorage.setItem("feedbackAdminToken", token.trim());
      const query = new URLSearchParams({ limit: "1000" });
      if (category) query.set("category", category);
      if (search.trim()) query.set("search", search.trim());
      const response = await fetch(buildApiUrl(`api/admin/feedback?${query.toString()}`), {
        headers: authHeaders(),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data?.detail || `Could not load feedback (${response.status}).`);
      setRecords(data.records || []);
      setMetadata(data);
      setStatus(`${data.matching_count || 0} matching report${data.matching_count === 1 ? "" : "s"}.`);
    } catch (error) {
      setRecords([]);
      setMetadata(null);
      setStatus(error.message || "Could not load feedback.");
    } finally {
      setLoading(false);
    }
  };

  const downloadExport = async (format) => {
    if (!token.trim()) {
      setStatus("Enter the FEEDBACK_ADMIN_TOKEN before exporting.");
      return;
    }
    setStatus("");
    try {
      const response = await fetch(buildApiUrl(`api/admin/feedback/export?format=${format}`), {
        headers: authHeaders(),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.detail || `Could not export feedback (${response.status}).`);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || `feedback.${format === "jsonl" ? "jsonl" : "csv"}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus(`Downloaded ${filename}.`);
    } catch (error) {
      setStatus(error.message || "Could not export feedback.");
    }
  };

  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: "32px 18px", color: "#0f172a" }}>
      <div style={{ width: "min(1180px, 100%)", margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 20, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: ".08em", color: "#475569" }}>PYACTIGRAPHY UI</div>
            <h1 style={{ margin: "6px 0 8px", fontSize: 34 }}>Feedback review</h1>
            <p style={{ margin: 0, color: "#475569", lineHeight: 1.55, maxWidth: 760 }}>
              Search submitted reports, inspect the complete UI and diagnostic context, and export all feedback as CSV or JSONL. The administrator token is retained only for this browser tab.
            </p>
          </div>
          <a href="/" style={{ color: "#0f172a", fontWeight: 800 }}>Return to application</a>
        </div>

        <section style={{ marginTop: 24, background: "white", border: "1px solid #e2e8f0", borderRadius: 18, padding: 18 }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(250px, 1fr) 180px minmax(220px, 1fr)", gap: 12 }}>
            <label style={{ display: "grid", gap: 6, fontWeight: 700 }}>
              Administrator token
              <input
                type="password"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder="FEEDBACK_ADMIN_TOKEN"
                style={{ padding: 11, borderRadius: 10, border: "1px solid #cbd5e1" }}
              />
            </label>
            <label style={{ display: "grid", gap: 6, fontWeight: 700 }}>
              Category
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                style={{ padding: 11, borderRadius: 10, border: "1px solid #cbd5e1", background: "white" }}
              >
                <option value="">All categories</option>
                <option value="issue">Issue / bug</option>
                <option value="suggestion">Suggestion</option>
                <option value="question">Question</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label style={{ display: "grid", gap: 6, fontWeight: 700 }}>
              Search all stored fields
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") loadFeedback();
                }}
                placeholder="Filename, error, request ID, setting…"
                style={{ padding: 11, borderRadius: 10, border: "1px solid #cbd5e1" }}
              />
            </label>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14 }}>
            <button type="button" onClick={loadFeedback} disabled={loading} style={primaryButtonStyle}>
              {loading ? "Loading…" : "Load feedback"}
            </button>
            <button type="button" onClick={() => downloadExport("csv")} style={secondaryButtonStyle}>Download CSV</button>
            <button type="button" onClick={() => downloadExport("jsonl")} style={secondaryButtonStyle}>Download JSONL</button>
          </div>
          {status && <div style={{ marginTop: 12, color: status.startsWith("Could") || status.startsWith("Enter") ? "#b91c1c" : "#166534" }}>{status}</div>}
        </section>

        {metadata && (
          <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12, marginTop: 16 }}>
            <SummaryCard label="Matching reports" value={metadata.matching_count || 0} />
            <SummaryCard label="Feedback file size" value={formatBytes(metadata.file_size_bytes)} />
            <SummaryCard label="Persistent storage" value={metadata.storage_persistent ? "Configured" : "Temporary / local"} />
            <SummaryCard label="Retention" value={`${metadata.retention_days || 30} days`} />
            <SummaryCard label="Storage path" value={metadata.storage_path || "Unknown"} compact />
          </section>
        )}

        {categorySummary.length > 0 && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
            {categorySummary.map(([name, count]) => (
              <span key={name} style={{ background: "#e2e8f0", borderRadius: 999, padding: "7px 11px", fontSize: 13, fontWeight: 800 }}>
                {categoryLabel(name)}: {count}
              </span>
            ))}
          </div>
        )}

        <section style={{ display: "grid", gap: 14, marginTop: 20 }}>
          {records.map((record) => (
            <article key={record.id || `${record.created_at}-${record.message}`} style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 18, padding: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
                <div>
                  <span style={{ display: "inline-block", background: "#dbeafe", color: "#1e3a8a", borderRadius: 999, padding: "5px 9px", fontSize: 12, fontWeight: 800 }}>
                    {categoryLabel(record.category)}
                  </span>
                  <h2 style={{ margin: "10px 0 6px", fontSize: 20 }}>{record.message || "No message supplied"}</h2>
                  <div style={{ color: "#64748b", fontSize: 13 }}>{formatDate(record.created_at)}</div>
                </div>
                <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.6, minWidth: 260 }}>
                  {record.email && <div><strong>Contact:</strong> {record.email}</div>}
                  {record.file_name && <div><strong>File:</strong> {record.file_name}</div>}
                  {record.current_step && <div><strong>Step:</strong> {record.current_step}</div>}
                  {record.request_id && <div><strong>Request ID:</strong> {record.request_id}</div>}
                </div>
              </div>
              {record.error_message && (
                <div style={{ marginTop: 13, border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", borderRadius: 12, padding: 12, whiteSpace: "pre-wrap" }}>
                  <strong>Current error:</strong> {record.error_message}
                </div>
              )}
              <details style={{ marginTop: 14 }}>
                <summary style={{ cursor: "pointer", fontWeight: 800 }}>Complete stored context</summary>
                <pre style={{ margin: "10px 0 0", padding: 14, borderRadius: 12, background: "#0f172a", color: "#e2e8f0", overflow: "auto", fontSize: 12, lineHeight: 1.5 }}>
                  {JSON.stringify(record, null, 2)}
                </pre>
              </details>
            </article>
          ))}
          {!loading && metadata && records.length === 0 && (
            <div style={{ textAlign: "center", color: "#64748b", padding: 36 }}>No feedback matched the current filters.</div>
          )}
        </section>
      </div>
    </main>
  );
}

function SummaryCard({ label, value, compact = false }) {
  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 15 }}>
      <div style={{ color: "#64748b", fontSize: 12, fontWeight: 800, textTransform: "uppercase", letterSpacing: ".04em" }}>{label}</div>
      <div style={{ marginTop: 7, fontWeight: 850, fontSize: compact ? 13 : 21, overflowWrap: "anywhere" }}>{String(value)}</div>
    </div>
  );
}

const primaryButtonStyle = {
  border: "none",
  borderRadius: 11,
  background: "#0f172a",
  color: "white",
  padding: "10px 15px",
  fontWeight: 800,
  cursor: "pointer",
};

const secondaryButtonStyle = {
  border: "1px solid #cbd5e1",
  borderRadius: 11,
  background: "white",
  color: "#0f172a",
  padding: "10px 15px",
  fontWeight: 800,
  cursor: "pointer",
};
