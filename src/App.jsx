import React from "react";
import Dashboard from "./pages/Dashboard";
import FeedbackAdminPanel from "./components/FeedbackAdminPanel";

export default function App() {
  const feedbackAdmin = new URLSearchParams(window.location.search).get("feedback-admin");
  return feedbackAdmin === "1" ? <FeedbackAdminPanel /> : <Dashboard />;
}
