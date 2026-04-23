import React, { useMemo, useState } from "react";

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
];

const acceptedCsvDescription = [
  "Any CSV is allowed",
  "You will map timestamp / activity / light / temperature columns after upload",
].join(". ");

function BubbleInfo({ label, content }) {
  const [open, setOpen] = useState(false);

  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: 6 }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span>{label}</span>
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: 999,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#e2e8f0",
          color: "#0f172a",
          fontSize: 12,
          fontWeight: 700,
          cursor: "default",
        }}
      >
        i
      </span>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "120%",
            left: 0,
            zIndex: 50,
            width: 320,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: "white",
            color: "#334155",
            fontSize: 13,
            lineHeight: 1.5,
            boxShadow: "0 8px 24px rgba(15,23,42,0.12)",
          }}
        >
          {content}
        </div>
      )}
    </span>
  );
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

  const fileInputs = useMemo(
    () => [
      {
        key: "actigraphy",
        title: "Actigraphy Files",
        button: "Choose Files",
        help: "Primary activity files. Native pyActigraphy formats and CSV are supported.",
      },
      {
        key: "light",
        title: "Light Data",
        button: "Optional Upload",
        help: "Optional additional light-exposure file if light is stored separately.",
      },
      {
        key: "temperature",
        title: "Temperature Data",
        button: "Optional Upload",
        help: "Optional additional temperature file if temperature is stored separately.",
      },
    ],
    []
  );

  const resetDownstreamState = () => {
    setPreviewLoaded?.(false);
    setPreviewData?.(null);
    setPreviewError?.("");
    setAnalysisError?.("");
    setResultsGenerated?.(false);
  };

  const detectLikelyCsv = (file) => file.name.toLowerCase().endsWith(".csv");

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
    }

    if (key === "actigraphy" && onActigraphyFilesChange) {
      onActigraphyFilesChange(files);
    } else {
      setUploadedFiles((prev) => ({
        ...prev,
        [key]: files,
      }));
    }

    resetDownstreamState();
    setCurrentStep("1");

    if (key === "actigraphy" && files.length > 0) {
      const first = files[0];
      if (detectLikelyCsv(first) && onCsvNeedsMapping) {
        onCsvNeedsMapping(first);
      }
    }
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
          display: "grid",
          gap: 10,
        }}
      >
        <div style={{ fontWeight: 700 }}>
          <BubbleInfo
            label="Accepted actigraphy files"
            content={`Supported file types currently enabled in the UI: ${acceptedActigraphyExtensions.join(", ")}`}
          />
        </div>

        <div style={{ fontWeight: 700 }}>
          <BubbleInfo
            label="CSV uploads"
            content={acceptedCsvDescription}
          />
        </div>

        <div style={{ color: "#475569", fontSize: 14, lineHeight: 1.6 }}>
          Masking excludes invalid or non-wear periods from analysis. Sleep diary files describe reported sleep timing and naps. Start/stop files define the effective recording interval when the device was actually worn.
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
            <div style={{ fontSize: 13, color: "#475569", marginTop: 8, lineHeight: 1.5 }}>
              {item.help}
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
                description: "Uses default preprocessing and standard metric defaults.",
              },
              {
                id: "custom",
                label: "Customized Analysis",
                description: "Lets the user manually choose algorithms, families, metrics, mappings, and parameters.",
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
        </div>
      )}
    </div>
  );
}