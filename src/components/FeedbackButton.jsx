import React, { useEffect, useMemo, useState } from "react";

export default function FeedbackButton({ buildApiUrl, user = null, context = {} }) {
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState("issue");
  const [email, setEmail] = useState(user?.email || "");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user?.email && !email) setEmail(user.email);
  }, [user, email]);

  const currentError = useMemo(
    () => context.analysisError || context.previewError || context.fileError || "",
    [context]
  );

  const submitFeedback = async (event) => {
    event.preventDefault();
    if (!message.trim()) {
      setStatus("Please describe the issue or suggestion before submitting.");
      return;
    }

    try {
      setSubmitting(true);
      setStatus("");
      const payload = {
        category,
        message: message.trim(),
        email: email.trim() || null,
        user_id: user?.id || null,
        user_email: user?.email || null,
        current_step: context.currentStep || null,
        file_name: context.fileName || null,
        file_type: context.fileType || null,
        file_size_mb: context.fileSizeMb || null,
        endpoint: context.endpoint || null,
        error_message: currentError || null,
        app_version: context.appVersion || null,
        backend_url: context.backendUrl || null,
        browser_info: window.navigator.userAgent,
      };

      const res = await fetch(buildApiUrl("api/feedback"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || "Could not submit feedback.");
      }

      setStatus("Thanks — your feedback was submitted.");
      setMessage("");
      setCategory("issue");
    } catch (err) {
      setStatus(err.message || "Could not submit feedback.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        style={{
          position: "fixed",
          right: 24,
          bottom: 24,
          zIndex: 100,
          border: "none",
          borderRadius: 999,
          background: "#0f172a",
          color: "white",
          padding: "12px 16px",
          fontWeight: 800,
          cursor: "pointer",
          boxShadow: "0 10px 30px rgba(15,23,42,0.25)",
        }}
      >
        Feedback
      </button>

      {open && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 101,
            background: "rgba(15,23,42,0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setOpen(false)}
        >
          <form
            onSubmit={submitFeedback}
            onClick={(event) => event.stopPropagation()}
            style={{
              width: "min(560px, 100%)",
              background: "white",
              borderRadius: 20,
              padding: 20,
              boxShadow: "0 24px 70px rgba(15,23,42,0.28)",
              display: "grid",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
              <div>
                <h2 style={{ margin: 0, color: "#0f172a" }}>Send feedback</h2>
                <p style={{ margin: "6px 0 0", color: "#64748b", fontSize: 14, lineHeight: 1.5 }}>
                  Report upload, preview, analysis, or deployment issues. Raw files are not sent through this form.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                style={{
                  border: "1px solid #cbd5e1",
                  background: "white",
                  borderRadius: 10,
                  padding: "6px 10px",
                  cursor: "pointer",
                  fontWeight: 800,
                }}
              >
                ×
              </button>
            </div>

            <label style={{ display: "grid", gap: 6, color: "#334155", fontWeight: 700, fontSize: 14 }}>
              Type
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                style={{ padding: 10, borderRadius: 10, border: "1px solid #cbd5e1" }}
              >
                <option value="issue">Issue / bug</option>
                <option value="suggestion">Suggestion</option>
                <option value="question">Question</option>
                <option value="other">Other</option>
              </select>
            </label>

            <label style={{ display: "grid", gap: 6, color: "#334155", fontWeight: 700, fontSize: 14 }}>
              Email, optional
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@example.com"
                style={{ padding: 10, borderRadius: 10, border: "1px solid #cbd5e1" }}
              />
            </label>

            <label style={{ display: "grid", gap: 6, color: "#334155", fontWeight: 700, fontSize: 14 }}>
              What happened?
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={6}
                placeholder="Tell us what you were trying to do and what went wrong."
                style={{ padding: 10, borderRadius: 10, border: "1px solid #cbd5e1", resize: "vertical" }}
              />
            </label>

            {(context.fileName || currentError) && (
              <div
                style={{
                  border: "1px solid #e2e8f0",
                  background: "#f8fafc",
                  borderRadius: 12,
                  padding: 10,
                  color: "#475569",
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                {context.fileName && <div><strong>File:</strong> {context.fileName}</div>}
                {context.fileType && <div><strong>Type:</strong> {context.fileType}</div>}
                {currentError && <div><strong>Current error:</strong> {currentError}</div>}
              </div>
            )}

            {status && (
              <div style={{ color: status.startsWith("Thanks") ? "#166534" : "#b91c1c", fontSize: 14 }}>
                {status}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                onClick={() => setOpen(false)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 12,
                  border: "1px solid #cbd5e1",
                  background: "white",
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: "10px 14px",
                  borderRadius: 12,
                  border: "none",
                  background: "#0f172a",
                  color: "white",
                  cursor: submitting ? "wait" : "pointer",
                  fontWeight: 700,
                }}
              >
                {submitting ? "Submitting..." : "Submit feedback"}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
