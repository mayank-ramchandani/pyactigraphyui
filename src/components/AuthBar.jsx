import React, { useEffect, useState } from "react";
import { supabase, supabaseConfigured } from "../services/supabaseClient";

export default function AuthBar({ onUserChange = () => {} }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    let mounted = true;

    if (!supabaseConfigured || !supabase) {
      onUserChange(null);
      return undefined;
    }

    supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) return;
      if (error) {
        setAuthError(error.message);
        onUserChange(null);
        return;
      }
      const currentUser = data?.session?.user || null;
      setUser(currentUser);
      onUserChange(currentUser);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      const currentUser = session?.user || null;
      setUser(currentUser);
      onUserChange(currentUser);
      setAuthError("");
    });

    return () => {
      mounted = false;
      subscription?.subscription?.unsubscribe?.();
    };
  }, [onUserChange]);

  const signInWithGoogle = async () => {
    if (!supabaseConfigured || !supabase) return;
    try {
      setLoading(true);
      setAuthError("");
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: window.location.origin,
        },
      });
      if (error) setAuthError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    if (!supabaseConfigured || !supabase) return;
    try {
      setLoading(true);
      setAuthError("");
      const { error } = await supabase.auth.signOut();
      if (error) setAuthError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        alignItems: "center",
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 16,
        padding: "12px 14px",
        marginBottom: 16,
      }}
    >
      <div>
        <div style={{ fontWeight: 700, color: "#0f172a" }}>Account</div>
        <div style={{ color: authError ? "#b91c1c" : "#64748b", fontSize: 13, marginTop: 2 }}>
          {!supabaseConfigured
            ? "Google login and saved runs are disabled until Supabase env variables are added."
            : user
            ? `Signed in as ${user.email || "Google user"}. Completed analyses can be saved to your run history.`
            : "Sign in with Google to save previous analysis runs. Raw uploaded files are not saved by default."}
          {authError ? ` ${authError}` : ""}
        </div>
      </div>

      {supabaseConfigured && (
        <button
          type="button"
          onClick={user ? signOut : signInWithGoogle}
          disabled={loading}
          style={{
            padding: "9px 14px",
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: user ? "white" : "#0f172a",
            color: user ? "#0f172a" : "white",
            cursor: loading ? "wait" : "pointer",
            fontWeight: 700,
            whiteSpace: "nowrap",
          }}
        >
          {loading ? "Please wait..." : user ? "Sign out" : "Sign in with Google"}
        </button>
      )}
    </div>
  );
}
