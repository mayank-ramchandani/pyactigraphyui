import React, { useEffect, useState } from "react";
import { supabase, supabaseConfigured } from "../services/supabaseClient";

function formatDate(value) {
  if (!value) return "Unknown time";
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch (_err) {
    return value;
  }
}

export default function RunHistoryPanel({ user, refreshToken = 0, onLoadRun = () => {} }) {
  const [open, setOpen] = useState(false);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadRuns() {
      if (!supabaseConfigured || !supabase || !user) {
        setRuns([]);
        return;
      }

      try {
        setLoading(true);
        setError("");
        const { data, error: queryError } = await supabase
          .from("analysis_runs")
          .select("*")
          .eq("user_id", user.id)
          .order("created_at", { ascending: false })
          .limit(20);

        if (queryError) throw queryError;
        if (mounted) setRuns(data || []);
      } catch (err) {
        if (mounted) setError(err.message || "Could not load saved runs.");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadRuns();

    return () => {
      mounted = false;
    };
  }, [user, refreshToken]);

  if (!supabaseConfigured || !user) return null;

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 16,
        padding: 14,
        marginBottom: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 700, color: "#0f172a" }}>Previous runs</div>
          <div style={{ color: "#64748b", fontSize: 13 }}>
            {loading ? "Loading saved runs..." : `${runs.length} recent run${runs.length === 1 ? "" : "s"} saved to your account.`}
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
            background: "white",
            color: "#0f172a",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          {open ? "Hide" : "Show"}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: 10, color: "#b91c1c", fontSize: 13 }}>
          {error}
        </div>
      )}

      {open && (
        <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
          {runs.length === 0 && !loading && (
            <div style={{ color: "#64748b", fontSize: 14 }}>
              No saved runs yet. Your next completed analysis will appear here.
            </div>
          )}

          {runs.map((run) => {
            const metricCount = Object.keys(run.results || {}).length;
            return (
              <div
                key={run.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  gap: 12,
                  alignItems: "center",
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: 12,
                  background: "#f8fafc",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, color: "#0f172a" }}>
                    {run.original_filename || "Untitled run"}
                  </div>
                  <div style={{ color: "#64748b", fontSize: 13, marginTop: 3 }}>
                    {formatDate(run.created_at)} · {run.file_type || "unknown"} · {run.status || "completed"}
                    {metricCount ? ` · ${metricCount} metric${metricCount === 1 ? "" : "s"}` : ""}
                  </div>
                  {run.error_message && (
                    <div style={{ color: "#b91c1c", fontSize: 13, marginTop: 4 }}>
                      {run.error_message}
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => onLoadRun(run)}
                  disabled={!run.results || Object.keys(run.results || {}).length === 0}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 10,
                    border: "none",
                    background: run.results && Object.keys(run.results || {}).length > 0 ? "#0f172a" : "#94a3b8",
                    color: "white",
                    cursor: run.results && Object.keys(run.results || {}).length > 0 ? "pointer" : "not-allowed",
                    fontWeight: 700,
                  }}
                >
                  Load summary
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
