import React from "react";

export default function WorkflowSidebar({ workflow, currentStep }) {
  const currentStepNumber = Number(currentStep);

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 18,
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.04)",
      }}
    >
      <div
        style={{
          fontSize: 14,
          fontWeight: 700,
          color: "#334155",
          marginBottom: 6,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        Workflow
      </div>

      <div
        style={{
          fontSize: 12,
          color: "#64748b",
          lineHeight: 1.5,
          marginBottom: 16,
        }}
      >
        This workflow is sequential. Completed steps are shown for reference, but earlier steps are locked once you move forward.
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        {workflow.map((item, index) => {
          const stepNumber = Number(item.id);
          const isActive = item.id === currentStep;
          const isCompleted = stepNumber < currentStepNumber;
          const isUpcoming = stepNumber > currentStepNumber;
          const isLast = index === workflow.length - 1;

          return (
            <div
              key={item.id}
              style={{
                display: "grid",
                gridTemplateColumns: "36px 1fr",
                gap: 12,
                alignItems: "start",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  minHeight: isLast ? 36 : 72,
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 999,
                    background: isActive || isCompleted ? "#0f172a" : "white",
                    color: isActive || isCompleted ? "white" : "#0f172a",
                    border: isActive || isCompleted ? "none" : "1px solid #cbd5e1",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {isCompleted ? "✓" : item.id}
                </div>

                {!isLast && (
                  <div
                    style={{
                      width: 2,
                      flex: 1,
                      marginTop: 6,
                      background: isCompleted ? "#0f172a" : "#e2e8f0",
                      borderRadius: 999,
                      minHeight: 28,
                    }}
                  />
                )}
              </div>

              <div
                style={{
                  border: isActive
                    ? "1px solid #0f172a"
                    : isCompleted
                    ? "1px solid #cbd5e1"
                    : "1px solid #e2e8f0",
                  borderRadius: 16,
                  padding: 14,
                  background: isActive ? "#f8fafc" : isCompleted ? "#f8fafc" : "white",
                  opacity: isUpcoming ? 0.9 : 1,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                    alignItems: "flex-start",
                    marginBottom: 4,
                  }}
                >
                  <div
                    style={{
                      fontWeight: 600,
                      color: "#0f172a",
                      lineHeight: 1.35,
                    }}
                  >
                    {item.title}
                  </div>

                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: "4px 8px",
                      borderRadius: 999,
                      background: isActive
                        ? "#0f172a"
                        : isCompleted
                        ? "#e2e8f0"
                        : "#f1f5f9",
                      color: isActive
                        ? "white"
                        : isCompleted
                        ? "#334155"
                        : "#64748b",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {isActive ? "Current" : isCompleted ? "Done" : "Pending"}
                  </div>
                </div>

                {item.description && (
                  <div
                    style={{
                      fontSize: 12,
                      color: "#64748b",
                      lineHeight: 1.5,
                    }}
                  >
                    {item.description}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}