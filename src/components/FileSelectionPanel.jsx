import React, { useState } from "react";

const acceptedActigraphyExtensions = [
  ".agd",
  ".atr",
  ".awd",
  ".bba",
  ".csv",
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
  const parts = name.toLowerCase().split(".");
  return parts.length > 1 ? `.${parts.pop()}` : "";
}

export default function FileSelectionPanel({
  title,
  uploadedFiles,
  setUploadedFiles,
  setCurrentStep,
  analysisMode,
  setAnalysisMode,
  setPreviewLoaded,
  setPreviewData,
  setPreviewError,
  setAnalysisError,
  setResultsGenerated,
  fileError,
  setFileError,
  onActigraphyFilesChange,
  onCsvNeedsMapping,
}) {
  const [uploadError, setUploadError] = useState("");

  const fileInputs = [
    { key: "actigraphy", title: "Actigraphy Files", button: "Choose Files" },
    { key: "sleepDiary", title: "Sleep Diary", button: "Optional Upload" },
    { key: "light", title: "Light Data", button: "Optional Upload" },
    { key: "temperature", title: "Temperature Data", button: "Optional Upload" },
    { key: "masking", title: "Cleaning / Masking", button: "Optional Upload" },
    { key: "startStop", title: "Start / Stop File", button: "Optional Upload" },
  ];

  const handleFiles = async (key, fileList) => {
    const files = Array.from(fileList || []);
    setUploadError("");
    setFileError?.("");

    if (key === "actigraphy" && files.length > 0) {
      const invalid = files.find((file) => {
        const lower = file.name.toLowerCase();
        return !acceptedActigraphyExtensions.some((ext) => lower.endsWith(ext));
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

    if (key === "actigraphy" && onActigraphyFilesChange) {
      onActigraphyFilesChange(files);
    } else {
      setUploadedFiles((prev) => ({
        ...prev,
        [key]: files,
      }));
    }

    setPreviewLoaded?.(false);
    setPreviewData?.(null);
    setPreviewError?.("");
    setAnalysisError?.("");
    setResultsGenerated?.(false);
    setCurrentStep("1");
  };

  return (
    <div
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 20,
        padding: 20,
      }}
    >
      <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
      <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16 }}>
        Upload raw actigraphy data and optional supporting files before previewing.
      </p>

      <div
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: 16,
          padding: 16,
          background: "#f8fafc",
          marginBottom: 16,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Accepted actigraphy files</div>
        <div style={{ color: "#475569", fontSize: 14, lineHeight: 1.6 }}>
          Native and tabular formats currently enabled: {acceptedActigraphyExtensions.join(", ")}.
          <br />
          Manual mapping is optional for generic CSV/TXT-style uploads.
        </div>
      </div>

      {(uploadError || fileError) && (
        <div
          style={{
            marginBottom: 16,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#991b1b",
            fontSize: 14,
          }}
        >
          {uploadError || fileError}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        {fileInputs.map((item) => (
          <label
            key={item.key}
            style={{
              border: "2px dashed #cbd5e1",
              borderRadius: 16,
              padding: 20,
              background: "#f8fafc",
              cursor: "pointer",
            }}
          >
            <div style={{ fontWeight: 700 }}>{item.title}</div>
            <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
              {uploadedFiles[item.key]?.length
                ? `${uploadedFiles[item.key].length} file(s) selected`
                : "No files selected"}
            </div>

            <input
              type="file"
              multiple
              accept={item.key === "actigraphy" ? acceptedActigraphyExtensions.join(",") : undefined}
              style={{ display: "none" }}
              onChange={(e) => handleFiles(item.key, e.target.files)}
            />

            <div
              style={{
                marginTop: 12,
                display: "inline-block",
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #cbd5e1",
                background: "white",
              }}
            >
              {item.button}
            </div>
          </label>
        ))}
      </div>

      <div
        style={{
          marginTop: 20,
          border: "1px solid #e2e8f0",
          borderRadius: 16,
          padding: 16,
          background: "#f8fafc",
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Analysis Type</div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            {
              id: "standard",
              label: "Standard / Default Analysis",
              description: "Uses default preprocessing and standard metric defaults.",
            },
            {
              id: "custom",
              label: "Customized Analysis",
              description: "Lets you manually choose algorithms, families, metrics, mappings, and parameters.",
            },
          ].map((mode) => {
            const selected = analysisMode === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => {
                  setAnalysisMode(mode.id);
                  setCurrentStep("1");
                }}
                style={{
                  padding: "12px 14px",
                  borderRadius: 14,
                  border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
                  background: selected ? "#0f172a" : "white",
                  color: selected ? "white" : "#0f172a",
                  cursor: "pointer",
                  textAlign: "left",
                  maxWidth: 340,
                }}
              >
                <div style={{ fontWeight: 700 }}>{mode.label}</div>
                <div
                  style={{
                    fontSize: 13,
                    marginTop: 6,
                    color: selected ? "rgba(255,255,255,0.9)" : "#475569",
                  }}
                >
                  {mode.description}
                </div>
              </button>
            );
          })}
        </div>

        <div style={{ marginTop: 12 }}>
          <button
            type="button"
            onClick={onCsvNeedsMapping}
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              border: "1px solid #cbd5e1",
              background: "white",
              cursor: "pointer",
            }}
          >
            Open Manual Mapping
          </button>
        </div>
      </div>
    </div>
  );
}