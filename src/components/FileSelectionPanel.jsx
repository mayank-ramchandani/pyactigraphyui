import React, { useState } from "react";

const acceptedActigraphyExtensions = [
  ".agd",
  ".atr",
  ".awd",
  ".bba",
  ".bin",
  ".csv",
  ".cwa",
  ".dqt",
  ".gt3x",
  ".mesa",
  ".mtn",
  ".rpx",
  ".tal",
  ".txt",
  ".gz",
];

function getExtension(name) {
  const parts = String(name || "").toLowerCase().split(".");
  return parts.length > 1 ? `.${parts.pop()}` : "";
}

export default function FileSelectionPanel({
  title,
  uploadedFiles,
  setCurrentStep = () => {},
  analysisMode,
  setAnalysisMode,
  participantFileMode = "separate",
  setParticipantFileMode = () => {},
  setPreviewLoaded,
  setPreviewData,
  setPreviewError,
  setAnalysisError,
  setResultsGenerated,
  fileError,
  setFileError,
  onActigraphyFilesChange,
  onCsvNeedsMapping,
  showManualMapping = false,
  setShowManualMapping = () => {},
}) {
  const [uploadError, setUploadError] = useState("");
  const [uploadHelpOpen, setUploadHelpOpen] = useState(false);
  const actigraphyFiles = uploadedFiles.actigraphy || [];
  const hasCsvActigraphy = actigraphyFiles.length > 0 && actigraphyFiles.every((file) => getExtension(file.name) === ".csv");

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || []);
    setUploadError("");
    setFileError?.("");

    if (files.length > 0) {
      const invalid = files.find((file) => {
        const lower = file.name.toLowerCase();
        return !acceptedActigraphyExtensions.some((extension) => lower.endsWith(extension));
      });

      if (invalid) {
        const message = `Unsupported file format: ${invalid.name}. Accepted actigraphy files: ${acceptedActigraphyExtensions.join(", ")}`;
        setUploadError(message);
        setFileError?.(message);
        return;
      }

      const extensions = [...new Set(files.map((file) => getExtension(file.name)))];
      if (extensions.length > 1) {
        const message = "Please upload only one actigraphy file type at a time. Multiple files are allowed, but they must all have the same extension.";
        setUploadError(message);
        setFileError?.(message);
        return;
      }
    }

    onActigraphyFilesChange?.(files);
    setPreviewLoaded?.(false);
    setPreviewData?.(null);
    setPreviewError?.("");
    setAnalysisError?.("");
    setResultsGenerated?.(false);
    setCurrentStep("1");
  };

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Upload actigraphy recordings here. Sleep diaries, masks, start/stop files, light files, and other sensor files are added later in the step where they are used.
      </p>

      {(uploadError || fileError) && (
        <div style={{ marginBottom: 16, padding: 12, borderRadius: 12, border: "1px solid #fecaca", background: "#fef2f2", color: "#991b1b", fontSize: 14 }}>
          {uploadError || fileError}
        </div>
      )}

      <label
        onMouseEnter={() => setUploadHelpOpen(true)}
        onMouseLeave={() => setUploadHelpOpen(false)}
        style={{ display: "block", position: "relative", border: "2px dashed #cbd5e1", borderRadius: 16, padding: 24, background: "#f8fafc", cursor: "pointer" }}
      >
        {uploadHelpOpen && (
          <div
            role="tooltip"
            style={{
              position: "absolute",
              left: "50%",
              bottom: "calc(100% + 10px)",
              transform: "translateX(-50%)",
              zIndex: 100,
              width: "min(620px, calc(100vw - 64px))",
              padding: 14,
              borderRadius: 14,
              border: "1px solid #bfdbfe",
              background: "white",
              color: "#334155",
              boxShadow: "0 12px 30px rgba(15,23,42,0.16)",
              fontSize: 13,
              lineHeight: 1.5,
              textAlign: "left",
              pointerEvents: "none",
            }}
          >
            <div style={{ fontWeight: 800, color: "#1e3a8a", marginBottom: 4 }}>Accepted actigraphy files</div>
            <div>Supported actigraphy file types: {acceptedActigraphyExtensions.join(", ")}. ActiGraph .gt3x and GENEActiv .bin recordings are inspected for embedded light later on the Other Sensors page.</div>
            <div style={{ fontWeight: 800, color: "#1e3a8a", marginTop: 10, marginBottom: 4 }}>Multiple files allowed</div>
            <div>Multiple actigraphy files can be uploaded together when they use the same extension. Choose whether they are separate recordings or files from one participant that should be joined by their real timestamps. Joined mode applies throughout the workflow. Each file is processed independently to a common analytical epoch before joining. Different native accelerometer sampling rates are retained in provenance and trigger metric-specific information or warnings; incompatible source/device activity is rejected.</div>
          </div>
        )}
        <div style={{ fontWeight: 800, fontSize: 17 }}>Actigraphy files</div>
        <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
          {actigraphyFiles.length ? `${actigraphyFiles.length} file(s) selected` : "No actigraphy files selected"}
        </div>
        {actigraphyFiles.length > 0 && (
          <div style={{ marginTop: 8, color: "#475569", fontSize: 13, lineHeight: 1.5 }}>
            {actigraphyFiles.map((file) => file.name).join(", ")}
          </div>
        )}
        <input
          type="file"
          multiple
          accept={acceptedActigraphyExtensions.join(",")}
          style={{ display: "none" }}
          onChange={(event) => handleFiles(event.target.files)}
        />
        <div style={{ marginTop: 14, display: "inline-block", padding: "9px 13px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", fontWeight: 700 }}>
          Choose actigraphy files
        </div>
      </label>

      {actigraphyFiles.length > 1 && (
        <div style={{ marginTop: 20, border: "1px solid #bfdbfe", borderRadius: 16, padding: 16, background: "#eff6ff" }}>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>How should these files be treated?</div>
          <div style={{ color: "#475569", fontSize: 13, lineHeight: 1.5, marginBottom: 12 }}>
            Choose this before continuing because it controls the entire workflow, not only the final Results page. Changing the mode later resets loaded previews and manually drawn intervals so file-scoped selections are not accidentally reused with a different timeline.
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 10 }}>
            <label style={{ display: "block", border: participantFileMode === "separate" ? "2px solid #2563eb" : "1px solid #cbd5e1", borderRadius: 14, padding: 13, cursor: "pointer", background: participantFileMode === "separate" ? "white" : "#f8fafc" }}>
              <input type="radio" name="participantFileModeImport" checked={participantFileMode === "separate"} onChange={() => setParticipantFileMode("separate")} />
              <span style={{ marginLeft: 8, fontWeight: 800 }}>Analyze files separately</span>
              <span style={{ display: "block", color: "#475569", fontSize: 13, lineHeight: 1.5, marginTop: 6 }}>Use this when files are different participants or should produce independent previews, QC, and metric results.</span>
            </label>
            <label style={{ display: "block", border: participantFileMode === "join" ? "2px solid #2563eb" : "1px solid #cbd5e1", borderRadius: 14, padding: 13, cursor: "pointer", background: participantFileMode === "join" ? "white" : "#f8fafc" }}>
              <input type="radio" name="participantFileModeImport" checked={participantFileMode === "join"} onChange={() => setParticipantFileMode("join")} />
              <span style={{ marginLeft: 8, fontWeight: 800 }}>Join as one participant timeline</span>
              <span style={{ display: "block", color: "#475569", fontSize: 13, lineHeight: 1.5, marginTop: 6 }}>Use only when every uploaded file belongs to the same participant. Each recording is processed independently to the common analytical epoch, then activity and light are joined by real timestamps. Gaps remain missing, duplicate boundaries are de-duplicated, and different native accelerometer sampling rates are explicitly assessed before the join.</span>
            </label>
          </div>
        </div>
      )}

      {hasCsvActigraphy && (
        <div style={{ marginTop: 20, border: "1px solid #dbeafe", borderRadius: 16, padding: 16, background: "#eff6ff" }}>
          <label style={{ display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showManualMapping}
              onChange={(event) => {
                const checked = event.target.checked;
                setShowManualMapping(checked);
                if (checked) onCsvNeedsMapping?.();
              }}
              style={{ marginTop: 3 }}
            />
            <span>
              <strong>Manually map CSV columns</strong>
              <span style={{ display: "block", color: "#475569", fontSize: 14, lineHeight: 1.5, marginTop: 4 }}>
                Use this only when automatic detection does not correctly identify timestamp, activity, light, temperature, or non-wear columns. The mapping form remains on this importing page.
              </span>
            </span>
          </label>
        </div>
      )}

      <div style={{ marginTop: 20, border: "1px solid #e2e8f0", borderRadius: 16, padding: 16, background: "#f8fafc" }}>
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Analysis type</div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            {
              id: "standard",
              label: "Standard / Default Analysis",
              description: "Uses the standard preprocessing rules and default metric selections while still allowing review of every stage.",
            },
            {
              id: "custom",
              label: "Customized Analysis",
              description: "Lets you change preprocessing thresholds, algorithms, metrics, mappings, and advanced parameters.",
            },
          ].map((mode) => {
            const selected = analysisMode === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => setAnalysisMode(mode.id)}
                style={{
                  padding: "12px 14px",
                  borderRadius: 14,
                  border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
                  background: selected ? "#0f172a" : "white",
                  color: selected ? "white" : "#0f172a",
                  cursor: "pointer",
                  textAlign: "left",
                  maxWidth: 360,
                }}
              >
                <div style={{ fontWeight: 700 }}>{mode.label}</div>
                <div style={{ fontSize: 13, marginTop: 6, color: selected ? "rgba(255,255,255,0.9)" : "#475569" }}>
                  {mode.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
