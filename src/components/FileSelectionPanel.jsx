import React, { useState } from "react";

const acceptedActigraphyExtensions = [
  ".agd",
  ".atr",
  ".awd",
  ".bba",
  ".csv",
  ".dqt",
  ".mesa",
  ".mtn",
  ".rpx",
  ".tal",
];

const requiredCsvColumns = [
  "subject_id",
  "Date",
  "Time",
  "Timestamp",
  "AxisXCounts",
  "AxisYCounts",
  "AxisZCounts",
  "VM",
];

const validateCsvHeader = async (file) => {
  const text = await file.text();
  const firstLine = text.split(/\r?\n/)[0]?.trim() || "";
  const headers = firstLine.split(",").map((header) => header.trim());

  const missing = requiredCsvColumns.filter((column) => !headers.includes(column));
  if (missing.length > 0) {
    return `Missing required CSV columns: ${missing.join(", ")}`;
  }

  const ordered = requiredCsvColumns.every((column, index) => headers[index] === column);
  if (!ordered) {
    return `CSV columns must begin in this order: ${requiredCsvColumns.join(", ")}`;
  }

  return "";
};

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
}) {
  const [uploadError, setUploadError] = useState("");

  const fileInputs = [
    { key: "actigraphy", title: "Actigraphy Files", button: "Choose Files" },
    { key: "sleepDiary", title: "Sleep Diary", button: "Optional Upload" },
    { key: "light", title: "Light Data", button: "Optional Upload" },
    { key: "temperature", title: "Temperature Data", button: "Optional Upload" },
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
        const message = `Unsupported file format: ${invalid.name}. Accepted actigraphy files currently enabled in this UI: ${acceptedActigraphyExtensions.join(", ")}`;
        setUploadError(message);
        setFileError?.(message);
        return;
      }

      for (const file of files) {
        if (file.name.toLowerCase().endsWith(".csv")) {
          const csvError = await validateCsvHeader(file);
          if (csvError) {
            setUploadError(csvError);
            setFileError?.(csvError);
            return;
          }
        }
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

  const hasActigraphyFile = (uploadedFiles.actigraphy || []).length > 0;

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
          Native formats currently enabled: {acceptedActigraphyExtensions.join(", ")}.
          <br />
          For CSV uploads, the file must begin with these columns in order:
          <br />
          <span style={{ fontFamily: "monospace", fontSize: 13 }}>
            {requiredCsvColumns.join(", ")}
          </span>
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

      {hasActigraphyFile && (
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
                description: "Uses default preprocessing, but still shows all metric and algorithm choices.",
              },
              {
                id: "custom",
                label: "Customized Analysis",
                description: "Lets the user manually choose preprocessing, metrics, algorithms, and parameters.",
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
                    flex: 1,
                    minWidth: 260,
                    textAlign: "left",
                    padding: 14,
                    borderRadius: 14,
                    border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
                    background: selected ? "#0f172a" : "white",
                    color: selected ? "white" : "#0f172a",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>{mode.label}</div>
                  <div style={{ fontSize: 13, opacity: selected ? 0.9 : 0.75 }}>
                    {mode.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}