import React, { useMemo, useState } from "react";

import appConfig from "../config/appConfig.json";
import metricRegistry from "../config/metricRegistry.json";
import algorithmRegistry from "../config/algorithmRegistry.json";
import exportRegistry from "../config/exportRegistry.json";
import previewRegistry from "../config/previewRegistry.json";

import WorkflowSidebar from "../components/WorkflowSidebar";
import FileSelectionPanel from "../components/FileSelectionPanel";
import PreviewPanel from "../components/PreviewPanel";
import MetricsPanel from "../components/MetricsPanel";
import ResultsPanel from "../components/ResultsPanel";
import ExportPanel from "../components/ExportPanel";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

import {
  getDefaultAlgorithm,
  getDefaultSelectedMetrics,
  getVisibleWorkflowSteps,
} from "../services/configUtils";

export default function Dashboard() {
  const [currentStep, setCurrentStep] = useState("1");

  const [uploadedFiles, setUploadedFiles] = useState({
    actigraphy: [],
    sleepDiary: [],
    light: [],
    temperature: [],
  });

  const [analysisMode, setAnalysisMode] = useState("standard");
  const [fileError, setFileError] = useState("");

  const [selectedPreviewFile, setSelectedPreviewFile] = useState("");
  const [previewDayMode, setPreviewDayMode] = useState("all");
  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewData, setPreviewData] = useState(null);

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");

  const [selectedMetrics, setSelectedMetrics] = useState(
    getDefaultSelectedMetrics(metricRegistry)
  );
  const [selectedAlgorithm, setSelectedAlgorithm] = useState(
    getDefaultAlgorithm(algorithmRegistry)
  );

  const [activityChannel, setActivityChannel] = useState("VM");
  const [activityTransform, setActivityTransform] = useState("none");
  const [lightTransform, setLightTransform] = useState("none");
  const [resampleFreq, setResampleFreq] = useState("1min");

  const [binarize, setBinarize] = useState(true);
  const [threshold, setThreshold] = useState(4);

  const [resultsGenerated, setResultsGenerated] = useState(false);
  const [selectedResultMetric, setSelectedResultMetric] = useState("");
  const [qcWarnings, setQcWarnings] = useState([]);
  const [summaryResults, setSummaryResults] = useState({});

  const actigraphyFiles = useMemo(() => uploadedFiles.actigraphy || [], [uploadedFiles]);

  const resolvedSelectedMetrics = useMemo(() => {
    if (analysisMode === "standard") {
      return getDefaultSelectedMetrics(metricRegistry);
    }
    return selectedMetrics;
  }, [analysisMode, selectedMetrics]);

  const workflowSteps = useMemo(
    () =>
      getVisibleWorkflowSteps(appConfig, {
        enableCleaning: !!appConfig?.features?.masking?.enabled,
        enableDiary: !!appConfig?.features?.sleepDiary?.enabled,
      }),
    []
  );

  const handleActigraphyFilesChange = (files) => {
    setUploadedFiles((prev) => ({
      ...prev,
      actigraphy: files,
    }));

    const firstFileName = files?.[0]?.name || "";
    setSelectedPreviewFile(firstFileName);
    setPreviewLoaded(false);
    setPreviewData(null);
    setPreviewError("");
    setResultsGenerated(false);
    setSummaryResults({});
    setQcWarnings([]);
    setAnalysisError("");
    setCurrentStep("1");
  };

  const parseJsonResponse = async (res) => {
    const text = await res.text();

    if (!text) {
      throw new Error(`Empty response from server (${res.status})`);
    }

    try {
      return JSON.parse(text);
    } catch {
      throw new Error(`Server did not return valid JSON (${res.status})`);
    }
  };

  const onPreview = async () => {
    const actigraphyFile = uploadedFiles.actigraphy?.find(
      (file) => file.name === selectedPreviewFile
    );

    if (!actigraphyFile || !previewDayMode) return;

    try {
      setPreviewLoading(true);
      setPreviewError("");
      setPreviewLoaded(false);
      setPreviewData(null);

      const formData = new FormData();
      formData.append("file", actigraphyFile);
      formData.append("previewDayMode", previewDayMode);
      formData.append("activityChannel", activityChannel);
      formData.append("resampleFreq", resampleFreq);

      const res = await fetch(`${API_BASE_URL}/api/preview/basic`, {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to load preview.");
      }

      setPreviewData(data);
      setPreviewLoaded(true);
      setCurrentStep("2");
    } catch (err) {
      setPreviewError(err.message || "Failed to load preview.");
      setPreviewLoaded(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleGenerateResults = async () => {
    const actigraphyFile = uploadedFiles.actigraphy?.[0];
    if (!actigraphyFile) return;

    try {
      setAnalysisLoading(true);
      setAnalysisError("");
      setResultsGenerated(false);

      const metricsToUse =
        analysisMode === "standard"
          ? getDefaultSelectedMetrics(metricRegistry)
          : selectedMetrics;

      const formData = new FormData();
      formData.append("file", actigraphyFile);
      formData.append("selectedMetrics", JSON.stringify(metricsToUse));
      formData.append("selectedAlgorithm", selectedAlgorithm || "cole_kripke");
      formData.append("binarize", JSON.stringify(binarize));
      formData.append("threshold", String(threshold));
      formData.append("activityChannel", activityChannel);
      formData.append("activityTransform", activityTransform);
      formData.append("lightTransform", lightTransform);
      formData.append("resampleFreq", resampleFreq);
      formData.append("analysisMode", analysisMode);

      const res = await fetch(`${API_BASE_URL}/api/analyze/basic`, {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to generate results.");
      }

      const results = data.results || {};
      setSummaryResults(results);
      setQcWarnings(data.qcWarnings || []);
      setSelectedResultMetric(Object.keys(results)[0] || "");
      setResultsGenerated(true);
      setCurrentStep("6");
    } catch (err) {
      setAnalysisError(err.message || "Failed to generate results.");
      setResultsGenerated(false);
    } finally {
      setAnalysisLoading(false);
    }
  };

  return (
    <div
      style={{
        padding: 24,
        fontFamily: "Arial, sans-serif",
        background: "#f8fafc",
        minHeight: "100vh",
      }}
    >
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <h1 style={{ fontSize: 32, marginBottom: 8 }}>{appConfig.appName}</h1>
        <p style={{ color: "#475569", marginBottom: 24, lineHeight: 1.5 }}>
          Config-driven starter layout for actigraphy preview, metrics, results, and export.
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "280px 1fr",
            gap: 24,
            alignItems: "start",
          }}
        >
          {appConfig.layout.sidebarEnabled && (
            <div style={{ position: "sticky", top: 24 }}>
              <WorkflowSidebar workflow={workflowSteps} currentStep={currentStep} />
            </div>
          )}

          <div style={{ display: "grid", gap: 20 }}>
            <FileSelectionPanel
              title={appConfig.panels.fileSelection.title}
              uploadedFiles={uploadedFiles}
              setUploadedFiles={setUploadedFiles}
              setCurrentStep={setCurrentStep}
              analysisMode={analysisMode}
              setAnalysisMode={setAnalysisMode}
              setPreviewLoaded={setPreviewLoaded}
              setPreviewData={setPreviewData}
              setPreviewError={setPreviewError}
              setAnalysisError={setAnalysisError}
              setResultsGenerated={setResultsGenerated}
              fileError={fileError}
              setFileError={setFileError}
              onActigraphyFilesChange={handleActigraphyFilesChange}
            />

            <PreviewPanel
              title={appConfig.panels.preview.title}
              previewCards={previewRegistry.previewCards}
              previewLoaded={previewLoaded}
              previewLoading={previewLoading}
              previewError={previewError}
              previewData={previewData}
              actigraphyFiles={actigraphyFiles}
              selectedPreviewFile={selectedPreviewFile}
              setSelectedPreviewFile={setSelectedPreviewFile}
              previewDayMode={previewDayMode}
              setPreviewDayMode={setPreviewDayMode}
              onPreview={onPreview}
              uiText={appConfig.uiText}
            />

{appConfig.panels.cleaning?.enabled && (
  <div
    style={{
      background: "white",
      border: "1px solid #e2e8f0",
      borderRadius: 20,
      padding: 20,
    }}
  >
    <h2 style={{ marginTop: 0, marginBottom: 8 }}>
      {appConfig.panels.cleaning.title}
    </h2>
    <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>
      Choose how non-wear or inactive periods should be handled.
    </p>

    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ fontWeight: 700 }}>Masking mode</div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {["none", "manual", "automatic", "file"].map((mode) => (
          <button
            key={mode}
            type="button"
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              border: "1px solid #cbd5e1",
              background: "white",
              cursor: "pointer",
            }}
          >
            {mode === "none"
              ? "No masking"
              : mode === "manual"
              ? "Manual masking"
              : mode === "automatic"
              ? "Automatic masking"
              : "File-based masking"}
          </button>
        ))}
      </div>

      <div
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: 14,
          padding: 14,
          background: "#f8fafc",
          color: "#475569",
          fontSize: 14,
          lineHeight: 1.6,
        }}
      >
        {appConfig.uiText?.maskingHelp}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <button
          type="button"
          style={{
            padding: "10px 14px",
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: "white",
            cursor: "pointer",
          }}
        >
          Upload mask file
        </button>

        <button
          type="button"
          style={{
            padding: "10px 14px",
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: "white",
            cursor: "pointer",
          }}
        >
          Apply selected masking
        </button>
      </div>
    </div>
  </div>
)}

{appConfig.panels.diaryAndLogs?.enabled && (
  <div
    style={{
      background: "white",
      border: "1px solid #e2e8f0",
      borderRadius: 20,
      padding: 20,
    }}
  >
    <h2 style={{ marginTop: 0, marginBottom: 8 }}>
      {appConfig.panels.diaryAndLogs.title}
    </h2>
    <p style={{ color: "#64748b", marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>
      Add optional files that help define sleep periods and true recording boundaries.
    </p>

    <div style={{ display: "grid", gap: 14 }}>
      <div
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: 14,
          padding: 14,
          background: "#f8fafc",
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Sleep diary</div>
        <div style={{ color: "#475569", fontSize: 14, lineHeight: 1.6, marginBottom: 10 }}>
          {appConfig.uiText?.diaryHelp}
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            type="button"
            style={{
              padding: "10px 14px",
              borderRadius: 12,
              border: "1px solid #cbd5e1",
              background: "white",
              cursor: "pointer",
            }}
          >
            Upload sleep diary
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
            <input type="checkbox" />
            Include awake-in-bed state
          </label>
        </div>
      </div>

      <div
        style={{
          border: "1px solid #e2e8f0",
          borderRadius: 14,
          padding: 14,
          background: "#f8fafc",
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Start / Stop time file</div>
        <div style={{ color: "#475569", fontSize: 14, lineHeight: 1.6, marginBottom: 10 }}>
          {appConfig.uiText?.sstHelp}
        </div>
        <button
          type="button"
          style={{
            padding: "10px 14px",
            borderRadius: 12,
            border: "1px solid #cbd5e1",
            background: "white",
            cursor: "pointer",
          }}
        >
          Upload start / stop file
        </button>
      </div>
    </div>
  </div>
)}

            <MetricsPanel
              title={appConfig.panels.metrics.title}
              metricRegistry={metricRegistry}
              algorithmRegistry={algorithmRegistry}
              selectedMetrics={selectedMetrics}
              setSelectedMetrics={setSelectedMetrics}
              selectedAlgorithm={selectedAlgorithm}
              setSelectedAlgorithm={setSelectedAlgorithm}
              setCurrentStep={setCurrentStep}
              activityChannel={activityChannel}
              setActivityChannel={setActivityChannel}
              activityTransform={activityTransform}
              setActivityTransform={setActivityTransform}
              lightTransform={lightTransform}
              setLightTransform={setLightTransform}
              resampleFreq={resampleFreq}
              setResampleFreq={setResampleFreq}
              binarize={binarize}
              setBinarize={setBinarize}
              threshold={threshold}
              setThreshold={setThreshold}
              analysisMode={analysisMode}
            />

            <ResultsPanel
              title={appConfig.panels.results.title}
              resultCards={previewRegistry.resultCards}
              resultsGenerated={resultsGenerated}
              onGenerate={handleGenerateResults}
              selectedResultMetric={selectedResultMetric}
              setSelectedResultMetric={setSelectedResultMetric}
              selectedMetrics={resolvedSelectedMetrics}
              summaryResults={summaryResults}
              qcWarnings={qcWarnings}
              metricRegistry={metricRegistry}
              analysisError={analysisError}
              analysisLoading={analysisLoading}
              analysisMode={analysisMode}
            />

            <ExportPanel
              title={appConfig.panels.export.title}
              exportRegistry={exportRegistry}
              setCurrentStep={setCurrentStep}
              resultsGenerated={resultsGenerated}
            />
          </div>
        </div>
      </div>
    </div>
  );
}