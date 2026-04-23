import React, { useMemo, useState } from "react";

import appConfig from "../config/appConfig.json";
import metricRegistry from "../config/metricRegistry.json";
import algorithmRegistry from "../config/algorithmRegistry.json";
import exportRegistry from "../config/exportRegistry.json";
import sharedParamRegistry from "../config/sharedParamRegistry.json";
import analysisFamilyRegistry from "../config/analysisFamilyRegistry.json";

import WorkflowSidebar from "../components/WorkflowSidebar";
import FileSelectionPanel from "../components/FileSelectionPanel";
import CsvMappingPanel from "../components/CsvMappingPanel";
import PreviewPanel from "../components/PreviewPanel";
import MetricsPanel from "../components/MetricsPanel";
import ResultsPanel from "../components/ResultsPanel";
import ExportPanel from "../components/ExportPanel";
import SupportFilesStep from "../components/SupportFilesStep";

import {
  getDefaultAlgorithm,
  getDefaultSelectedMetrics,
  getVisibleWorkflowSteps,
} from "../services/configUtils";
import { buildAnalysisPayload } from "../services/analysisConfigUtils";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}

function getExtension(name) {
  const parts = name?.toLowerCase().split(".") || [];
  return parts.length > 1 ? `.${parts.pop()}` : "";
}

export default function Dashboard() {
  const [currentStep, setCurrentStep] = useState("1");
  const [maxUnlockedStep, setMaxUnlockedStep] = useState("1");

  const [uploadedFiles, setUploadedFiles] = useState({
    actigraphy: [],
    masking: [],
    sleepDiary: [],
    light: [],
    temperature: [],
    startStop: [],
  });

  const [selectedPreviewFile, setSelectedPreviewFile] = useState("");
  const [selectedLightPreviewFile, setSelectedLightPreviewFile] = useState("");

  const [analysisMode, setAnalysisMode] = useState("standard");
  const [analysisScope, setAnalysisScope] = useState("metric");
  const [selectedFamilies, setSelectedFamilies] = useState([]);
  const [fileError, setFileError] = useState("");

  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewData, setPreviewData] = useState(null);

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");

  const [selectedMetrics, setSelectedMetrics] = useState(getDefaultSelectedMetrics(metricRegistry));
  const [selectedAlgorithm, setSelectedAlgorithm] = useState(getDefaultAlgorithm(algorithmRegistry));

  const [sharedValues, setSharedValues] = useState({});
  const [metricOverrides, setMetricOverrides] = useState({});
  const [algorithmParams, setAlgorithmParams] = useState({});

  const [activityChannel, setActivityChannel] = useState("VM");
  const [activityTransform, setActivityTransform] = useState("none");
  const [lightTransform, setLightTransform] = useState("none");

  const [csvMapping, setCsvMapping] = useState({
    timestamp_col: "",
    activity_col: "",
    light_col: "",
    temperature_col: "",
    nonwear_col: "",
  });
  const [csvSeparator, setCsvSeparator] = useState(",");
  const [showManualMapping, setShowManualMapping] = useState(false);

  const [resultsGenerated, setResultsGenerated] = useState(false);
  const [selectedResultMetric, setSelectedResultMetric] = useState("");
  const [qcWarnings, setQcWarnings] = useState([]);
  const [summaryResults, setSummaryResults] = useState({});

  const actigraphyFiles = uploadedFiles.actigraphy || [];
  const lightFiles = uploadedFiles.light || [];

  const actigraphyFile =
    actigraphyFiles.find((file) => file.name === selectedPreviewFile) ||
    actigraphyFiles[0] ||
    null;

  const lightFile =
    lightFiles.find((file) => file.name === selectedLightPreviewFile) ||
    lightFiles[0] ||
    null;

  const workflowSteps = useMemo(
    () =>
      getVisibleWorkflowSteps(appConfig, {
        enableCleaning: true,
        enableDiary: true,
      }),
    []
  );

  const currentStepIndex = workflowSteps.findIndex((step) => step.id === currentStep);

  const goToStep = (stepId) => {
    if (Number(stepId) <= Number(maxUnlockedStep)) setCurrentStep(stepId);
  };

  const unlockAndGoToStep = (stepId) => {
    const n = Number(stepId);
    if (n > Number(maxUnlockedStep)) setMaxUnlockedStep(String(n));
    setCurrentStep(String(stepId));
  };

  const goNext = () => {
    if (currentStepIndex < workflowSteps.length - 1) {
      const next = workflowSteps[currentStepIndex + 1];
      unlockAndGoToStep(next.id);
    }
  };

  const goPrevious = () => {
    if (currentStepIndex > 0) {
      const prev = workflowSteps[currentStepIndex - 1];
      goToStep(prev.id);
    }
  };

  const familyMetricIds = useMemo(() => {
    const familyLookup = Object.fromEntries(
      (analysisFamilyRegistry.families || []).map((family) => [family.id, family.metrics || []])
    );
    const merged = new Set();
    selectedFamilies.forEach((familyId) => {
      (familyLookup[familyId] || []).forEach((metricId) => merged.add(metricId));
    });
    return [...merged];
  }, [selectedFamilies]);

  const resolvedSelectedMetrics = useMemo(() => {
    if (analysisMode === "standard") return getDefaultSelectedMetrics(metricRegistry);
    return analysisScope === "family" ? familyMetricIds : selectedMetrics;
  }, [analysisMode, analysisScope, familyMetricIds, selectedMetrics]);

  const resolvedAnalysisConfig = useMemo(
    () =>
      buildAnalysisPayload({
        metricRegistry,
        sharedRegistry: sharedParamRegistry,
        algorithmRegistry,
        analysisFamilyRegistry,
        selectedMetrics,
        selectedFamilies,
        analysisScope,
        selectedAlgorithm,
        sharedValues,
        metricOverrides,
        algorithmParams,
      }),
    [selectedMetrics, selectedFamilies, analysisScope, selectedAlgorithm, sharedValues, metricOverrides, algorithmParams]
  );

  const parseJsonResponse = async (res) => {
    const text = await res.text();
    if (!text) throw new Error(`Empty response from server (${res.status})`);
    return JSON.parse(text);
  };

  const handleActigraphyFilesChange = (files) => {
    setUploadedFiles((prev) => ({ ...prev, actigraphy: files }));
    setSelectedPreviewFile(files?.[0]?.name || "");

    setPreviewLoaded(false);
    setPreviewData(null);
    setPreviewError("");
    setResultsGenerated(false);
    setSummaryResults({});
    setQcWarnings([]);
    setAnalysisError("");

    setShowManualMapping(false);
    setCsvMapping({
      timestamp_col: "",
      activity_col: "",
      light_col: "",
      temperature_col: "",
      nonwear_col: "",
    });

    unlockAndGoToStep("3");
  };

  const handleCsvNeedsMapping = () => {
    setShowManualMapping(true);
    unlockAndGoToStep("2");
  };

  const onPreview = async () => {
    if (!actigraphyFile) return;

    try {
      setPreviewLoading(true);
      setPreviewError("");
      setPreviewLoaded(false);
      setPreviewData(null);

      const formData = new FormData();
      formData.append("file", actigraphyFile);
      formData.append("activityChannel", activityChannel);
      formData.append("resampleFreq", "1min");
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);

      if (lightFile) formData.append("lightFile", lightFile);

      const res = await fetch(buildApiUrl("api/preview/basic"), {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);

      if (!res.ok) throw new Error(data?.detail || "Failed to load preview.");

      setPreviewData(data);
      setPreviewLoaded(true);
      unlockAndGoToStep("4");
    } catch (err) {
      setPreviewError(err.message || "Failed to load preview.");
      setPreviewLoaded(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleGenerateResults = async () => {
    if (!actigraphyFile) return;

    try {
      setAnalysisLoading(true);
      setAnalysisError("");
      setResultsGenerated(false);

      const formData = new FormData();
      formData.append("file", actigraphyFile);
      formData.append("activityChannel", activityChannel);
      formData.append("activityTransform", activityTransform);
      formData.append("lightTransform", lightTransform);
      formData.append("analysisMode", analysisMode);
      formData.append("analysisConfig", JSON.stringify(resolvedAnalysisConfig));
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);

      const res = await fetch(buildApiUrl("api/analyze/basic"), {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);

      if (!res.ok) throw new Error(data?.detail || "Failed to generate results.");

      const results = data.results || {};
      setSummaryResults(results);
      setQcWarnings(data.qcWarnings || []);
      setSelectedResultMetric(Object.keys(results)[0] || "");
      setResultsGenerated(true);
      unlockAndGoToStep("9");
    } catch (err) {
      setAnalysisError(err.message || "Failed to generate results.");
      setResultsGenerated(false);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const detectedInputType =
    previewData?.detected_input_type || getExtension(actigraphyFile?.name || "").replace(".", "") || "unknown";

  let content = null;

  if (currentStep === "1") {
    content = (
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
        onCsvNeedsMapping={handleCsvNeedsMapping}
      />
    );
  } else if (currentStep === "2") {
    content = (
      <CsvMappingPanel
        title={appConfig.panels.csvMapping.title}
        csvFile={actigraphyFile}
        csvMapping={csvMapping}
        setCsvMapping={setCsvMapping}
        csvSeparator={csvSeparator}
        setCsvSeparator={setCsvSeparator}
        onContinue={onPreview}
      />
    );
  } else if (currentStep === "3") {
    content = (
      <PreviewPanel
        title={appConfig.panels.preview.title}
        mode="activity"
        previewLoaded={previewLoaded}
        previewLoading={previewLoading}
        previewError={previewError}
        previewData={previewData}
        onPreview={onPreview}
        actigraphyFiles={actigraphyFiles}
        selectedPreviewFile={selectedPreviewFile}
        setSelectedPreviewFile={setSelectedPreviewFile}
        lightFiles={lightFiles}
        selectedLightPreviewFile={selectedLightPreviewFile}
        setSelectedLightPreviewFile={setSelectedLightPreviewFile}
      />
    );
  } else if (currentStep === "4") {
    content = (
      <PreviewPanel
        title={appConfig.panels.lightPreview.title}
        mode="light"
        previewLoaded={previewLoaded}
        previewLoading={previewLoading}
        previewError={previewError}
        previewData={previewData}
        onPreview={onPreview}
        actigraphyFiles={actigraphyFiles}
        selectedPreviewFile={selectedPreviewFile}
        setSelectedPreviewFile={setSelectedPreviewFile}
        lightFiles={lightFiles}
        selectedLightPreviewFile={selectedLightPreviewFile}
        setSelectedLightPreviewFile={setSelectedLightPreviewFile}
      />
    );
  } else {
      content = <div />;
  }

  const canGoPrevious = currentStepIndex > 0;
  const canGoNext = currentStepIndex < workflowSteps.length - 1;

  return (
    <div style={{ padding: 24, fontFamily: "Arial, sans-serif", background: "#f8fafc", minHeight: "100vh" }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <h1 style={{ fontSize: 32, marginBottom: 8 }}>{appConfig.appName}</h1>
        <p style={{ color: "#475569", marginBottom: 24, lineHeight: 1.5 }}>
          Sequential actigraphy workflow with optional tabular mapping, light preview, support files, and family-aware analysis.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 24, alignItems: "start" }}>
          {appConfig.layout.sidebarEnabled && (
            <div style={{ position: "sticky", top: 24 }}>
              <WorkflowSidebar
                workflow={workflowSteps}
                currentStep={currentStep}
                maxUnlockedStep={maxUnlockedStep}
                onStepClick={goToStep}
              />
            </div>
          )}

          <div style={{ display: "grid", gap: 16 }}>
            {content}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: 16,
                padding: 16,
              }}
            >
              <button
                type="button"
                onClick={goPrevious}
                disabled={!canGoPrevious}
                style={{
                  padding: "10px 16px",
                  borderRadius: 12,
                  background: canGoPrevious ? "white" : "#e2e8f0",
                  color: canGoPrevious ? "#0f172a" : "#94a3b8",
                  border: "1px solid #cbd5e1",
                  cursor: canGoPrevious ? "pointer" : "not-allowed",
                  fontWeight: 600,
                }}
              >
                Previous
              </button>

              <button
                type="button"
                onClick={goNext}
                disabled={!canGoNext}
                style={{
                  padding: "10px 16px",
                  borderRadius: 12,
                  background: canGoNext ? "#0f172a" : "#94a3b8",
                  color: "white",
                  border: "none",
                  cursor: canGoNext ? "pointer" : "not-allowed",
                  fontWeight: 600,
                }}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}