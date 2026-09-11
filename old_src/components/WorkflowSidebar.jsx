import React from "react";

export default function WorkflowSidebar({ workflow, currentStep, maxUnlockedStep, visitedSteps = [], onStepClick }) {
  const currentStepNumber = Number(currentStep);
  const unlockedStepNumber = Number(maxUnlockedStep || currentStep);

  const progressPercent = workflow.length
    ? Math.max(0, Math.min(100, (currentStepNumber / workflow.length) * 100))
    : 0;

  return (
    <div
      className="workflow-sidebar-card"
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 16,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
        display: "flex",
        flexDirection: "column",
        overflow: "visible",
      }}
    >
      <div style={{ flex: "0 0 auto", padding: "2px 2px 12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#334155", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Workflow
          </div>
          <div style={{ fontSize: 12, fontWeight: 800, color: "#0f172a", whiteSpace: "nowrap" }}>
            Step {currentStepNumber} of {workflow.length}
          </div>
        </div>

        <div style={{ height: 6, borderRadius: 999, background: "#e2e8f0", overflow: "hidden", marginBottom: 8 }}>
          <div
            style={{
              width: `${progressPercent}%`,
              height: "100%",
              borderRadius: 999,
              background: "#0f172a",
              transition: "width 180ms ease",
            }}
          />
        </div>

        <div style={{ fontSize: 12.5, color: "#475569", lineHeight: 1.5 }}>
          Jump to any unlocked step. Hover over a step to view its description.
        </div>
      </div>

      <div
        className="workflow-step-list"
        style={{
          display: "grid",
          gap: 8,
          paddingRight: 0,
          overflow: "visible",
        }}
      >
        {workflow.map((item) => {
          const stepNumber = Number(item.id);
          const isActive = stepNumber === currentStepNumber;
          const isVisited = (visitedSteps || []).includes(String(item.id)) && !isActive;
          const isUnlocked = stepNumber <= unlockedStepNumber;

          return (
            <button
              key={item.id}
              type="button"
              className={`workflow-step-button${isActive ? " is-active" : ""}${!isUnlocked ? " is-locked" : ""}`}
              disabled={!isUnlocked}
              onClick={() => isUnlocked && onStepClick?.(item.id)}
              aria-current={isActive ? "step" : undefined}
              aria-label={item.description ? `${item.title}. ${item.description}` : item.title}
              title={item.description ? `${item.title}: ${item.description}` : item.title}
              style={{
                display: "grid",
                gridTemplateColumns: "34px minmax(0, 1fr) auto",
                gap: 10,
                alignItems: "center",
                width: "100%",
                border: isActive ? "1px solid #0f172a" : "1px solid #e2e8f0",
                borderRadius: 12,
                padding: "10px 10px",
                background: isActive ? "#f8fafc" : "white",
                opacity: isUnlocked ? 1 : 0.5,
                textAlign: "left",
                cursor: isUnlocked ? "pointer" : "not-allowed",
                minHeight: 50,
                position: "relative",
                overflow: "visible",
              }}
            >
              <span
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: 999,
                  background: isActive || isVisited ? "#0f172a" : "white",
                  color: isActive || isVisited ? "white" : "#0f172a",
                  border: isActive || isVisited ? "1px solid #0f172a" : "1px solid #cbd5e1",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: 12,
                  boxSizing: "border-box",
                }}
              >
                {isVisited ? "✓" : item.id}
              </span>

              <span style={{ minWidth: 0 }}>
                <span style={{ display: "block", fontWeight: isActive ? 800 : 700, color: "#0f172a", lineHeight: 1.35, fontSize: 13.5 }}>
                  {item.title}
                </span>
              </span>

              <span
                style={{
                  fontSize: 10,
                  fontWeight: 800,
                  color: isActive ? "white" : "#94a3b8",
                  background: isActive ? "#0f172a" : "transparent",
                  borderRadius: 999,
                  padding: isActive ? "3px 6px" : 0,
                  whiteSpace: "nowrap",
                }}
              >
                {isActive ? "Current" : isUnlocked ? "" : "Locked"}
              </span>

              {item.description && (
                <span className="workflow-step-tooltip" role="tooltip" aria-hidden="true">
                  <span className="workflow-step-tooltip-title">{item.title}</span>
                  <span>{item.description}</span>
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
