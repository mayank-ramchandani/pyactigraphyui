import React from "react";

import PreviewPanel from "./PreviewPanel";
import LightRGBPanel from "./LightRGBPanel";
import LightMetricsPanel from "./LightMetricsPanel";

const auxiliarySensorExtensions = ".csv,.csv.gz,.ods,.xls,.xlsx,.txt,.bin,.gt3x";

function UploadCard({ title, description, files = [], onFilesChange, buttonLabel, planned = false }) {
  return (
    <label
      style={{
        display: "block",
        border: planned ? "1px dashed #cbd5e1" : "2px dashed #cbd5e1",
        borderRadius: 16,
        padding: 18,
        background: planned ? "#f8fafc" : "white",
        cursor: "pointer",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: 800 }}>{title}</div>
          <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5, marginTop: 4 }}>{description}</div>
        </div>
        {planned && <span style={{ fontSize: 12, fontWeight: 800, borderRadius: 999, padding: "5px 9px", background: "#e2e8f0", color: "#475569" }}>Future analysis</span>}
      </div>
      <div style={{ fontSize: 13, color: "#475569", marginTop: 10 }}>
        {files.length ? `${files.length} file(s) attached: ${files.map((file) => file.name).join(", ")}` : "No separate file attached"}
      </div>
      <input
        type="file"
        multiple
        accept={auxiliarySensorExtensions}
        style={{ display: "none" }}
        onChange={(event) => onFilesChange(Array.from(event.target.files || []))}
      />
      <div style={{ marginTop: 12, display: "inline-block", padding: "8px 12px", borderRadius: 10, border: "1px solid #cbd5e1", background: "white", fontWeight: 700 }}>
        {buttonLabel}
      </div>
    </label>
  );
}

export default function OtherSensorsPanel({
  title,
  lightFiles = [],
  onLightFilesChange = () => {},
  temperatureFiles = [],
  onTemperatureFilesChange = () => {},
  previewProps = {},
  lightFile = null,
  lightPreviewLoaded = false,
  lightPreviewData = null,
  selectedLightMetrics = [],
  setSelectedLightMetrics = () => {},
  lightMetricSettings = {},
  setLightMetricSettings = () => {},
  lightSourceMessage = "",
  onLightInspection = () => {},
}) {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
        <h2 style={{ marginTop: 0, marginBottom: 8 }}>{title}</h2>
        <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16, lineHeight: 1.55 }}>
          Inspect light data embedded in the actigraphy recording or attach a separate light file. Temperature and additional sensor files can be attached for provenance, but their analysis is reserved for a future version.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
          <UploadCard
            title="Separate light data"
            description="Optional. Leave this empty to inspect light embedded in the selected actigraphy file."
            files={lightFiles}
            onFilesChange={onLightFilesChange}
            buttonLabel="Choose light files"
          />
          <UploadCard
            title="Temperature or other sensor data"
            description="Optional attachment for future sensor processing. These files are not currently analyzed or included in metric calculations."
            files={temperatureFiles}
            onFilesChange={onTemperatureFilesChange}
            buttonLabel="Attach sensor files"
            planned
          />
        </div>
      </div>

      <PreviewPanel {...previewProps} />

      {lightFile && lightPreviewLoaded && lightPreviewData?.light_preview_available && (
        <LightRGBPanel lightFile={lightFile} initialPayload={lightPreviewData} />
      )}

      <LightMetricsPanel
        lightFile={lightFile}
        selectedLightMetrics={selectedLightMetrics}
        setSelectedLightMetrics={setSelectedLightMetrics}
        lightMetricSettings={lightMetricSettings}
        setLightMetricSettings={setLightMetricSettings}
        previewData={lightPreviewData}
        lightSourceMessage={lightSourceMessage}
        onLightInspection={onLightInspection}
      />
    </div>
  );
}
