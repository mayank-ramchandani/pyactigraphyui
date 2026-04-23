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

function extractFileType(name) {
  const parts = name?.split(".") || [];
  return parts.length > 1 ? parts.pop().toLowerCase() : "unknown";
}

export default function Dashboard() {
  const [currentStep, setCurrentStep] = useState("1");
  const [maxUnlockedStep, setMaxUnlockedStep] = useState("1");

  const [uploadedFiles, setUploadedFiles] = useState({
    actigraphy: [],
    sleepDiary: [],
    light: [],
    temperature: [],
    startStop: [],
  });

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

  const [selectedMetrics, setSelectedMetrics] = useState(
    getDefaultSelectedMetrics(metricRegistry)
  );
  const [selectedAlgorithm, setSelectedAlgorithm] = useState(
    getDefaultAlgorithm(algorithmRegistry)
  );

  const [sharedValues, setSharedValues] = useState({});
  const [metricOverrides, setMetricOverrides] = useState({});
  const [algorithmParams, setAlgorithmParams] = useState({});

  const [activityChannel, setActivityChannel] = useState("VM");
  const [activityTransform, setActivityTransform] = useState("none");
  const [lightTransform, setLightTransform] = useState("none");

  const [csvNeedsMapping, setCsvNeedsMapping] = useState(false);
  const [csvMapping, setCsvMapping] = useState({
    timestamp_col: "",
    activity_col: "",
    light_col: "",
    temperature_col: "",
    nonwear_col: "",
  });
  const [csvSeparator, setCsvSeparator] = useState(",");

  const [resultsGenerated, setResultsGenerated] = useState(false);
  const [selectedResultMetric, setSelectedResultMetric] = useState("");
  const [qcWarnings, setQcWarnings] = useState([]);
  const [summaryResults, setSummaryResults] = useState({});

  const actigraphyFile = uploadedFiles.actigraphy?.[0] || null;
  const lightFile = uploadedFiles.light?.[0] || null;

  const workflowSteps = useMemo(
    () =>
      getVisibleWorkflowSteps(appConfig, {
        enableCleaning: !!appConfig?.features?.masking?.enabled,
        enableDiary: true,
      }),
    []
  );

  const currentStepIndex = workflowSteps.findIndex((step) => step.id === currentStep);
  const currentStepNumber = Number(currentStep);

  const goToStep = (stepId) => {
    if (Number(stepId) <= Number(maxUnlockedStep)) {
      setCurrentStep(stepId);
    }
  };

  const unlockAndGoToStep = (stepId) => {
    const target = Number(stepId);
    const unlocked = Number(maxUnlockedStep);
    if (target > unlocked) {
      setMaxUnlockedStep(String(target));
    }
    setCurrentStep(String(stepId));
  };

  const goNext = () => {
    if (currentStepIndex < workflowSteps.length - 1) {
      const nextStep = workflowSteps[currentStepIndex + 1];
      unlockAndGoToStep(nextStep.id);
    }
  };

  const goPrevious = () => {
    if (currentStepIndex > 0) {
      const prevStep = workflowSteps[currentStepIndex - 1];
      goToStep(prevStep.id);
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
    if (analysisMode === "standard") {
      return getDefaultSelectedMetrics(metricRegistry);
    }
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
    [
      selectedMetrics,
      selectedFamilies,
      analysisScope,
      selectedAlgorithm,
      sharedValues,
      metricOverrides,
      algorithmParams,
    ]
  );

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

  const handleActigraphyFilesChange = (files) => {
    setUploadedFiles((prev) => ({
      ...prev,
      actigraphy: files,
    }));

    setPreviewLoaded(false);
    setPreviewData(null);
    setPreviewError("");
    setResultsGenerated(false);
    setSummaryResults({});
    setQcWarnings([]);
    setAnalysisError("");

    const first = files?.[0];
    const isCsv = first?.name?.toLowerCase().endsWith(".csv");
    setCsvNeedsMapping(Boolean(isCsv));

    if (!isCsv) {
      setCsvMapping({
        timestamp_col: "",
        activity_col: "",
        light_col: "",
        temperature_col: "",
        nonwear_col: "",
      });
      unlockAndGoToStep("3");
    } else {
      unlockAndGoToStep("2");
    }
  };

  const handleCsvNeedsMapping = () => {
    setCsvNeedsMapping(true);
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
      formData.append("csvMapping", JSON.stringify(csvMapping));
      formData.append("csvSeparator", csvSeparator);

      if (lightFile) {
        formData.append("lightFile", lightFile);
      }

      const res = await fetch(buildApiUrl("api/preview/basic"), {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to load preview.");
      }

      setPreviewData(data);
      setPreviewLoaded(true);
      unlockAndGoToStep("3");
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
      formData.append("csvMapping", JSON.stringify(csvMapping));
      formData.append("csvSeparator", csvSeparator);

      const res = await fetch(buildApiUrl("api/analyze/basic"), {
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
      unlockAndGoToStep("9");
    } catch (err) {
      setAnalysisError(err.message || "Failed to generate results.");
      setResultsGenerated(false);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const detectedInputType =
    previewData?.detected_input_type || extractFileType(actigraphyFile?.name) || "unknown";

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
        onContinue={() => unlockAndGoToStep("4")}
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
        onContinue={() => unlockAndGoToStep("5")}
      />
    );
  } else if (currentStep === "5") {
    content = (
      <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>{appConfig.panels.cleaning.title}</h2>
        <p style={{ color: "#64748b", lineHeight: 1.6 }}>{appConfig.uiText.maskingHelp}</p>
      </div>
    );
  } else if (currentStep === "6") {
    content = (
      <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>{appConfig.panels.sleepDiary.title}</h2>
        <p style={{ color: "#64748b", lineHeight: 1.6 }}>{appConfig.uiText.diaryHelp}</p>
        <div style={{ fontSize: 14, color: "#475569", marginTop: 12 }}>
          Uploaded files: {(uploadedFiles.sleepDiary || []).length}
        </div>
      </div>
    );
  } else if (currentStep === "7") {
    content = (
      <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>{appConfig.panels.startStop.title}</h2>
        <p style={{ color: "#64748b", lineHeight: 1.6 }}>{appConfig.uiText.sstHelp}</p>
        <div style={{ fontSize: 14, color: "#475569", marginTop: 12 }}>
          Uploaded files: {(uploadedFiles.startStop || []).length}
        </div>
      </div>
    );
  } else if (currentStep === "8") {
    content = (
      <div style={{ display: "grid", gap: 20 }}>
        <MetricsPanel
          title={appConfig.panels.metrics.title}
          metricRegistry={metricRegistry}
          algorithmRegistry={algorithmRegistry}
          analysisFamilyRegistry={analysisFamilyRegistry}
          sharedParamRegistry={sharedParamRegistry}
          selectedMetrics={selectedMetrics}
          setSelectedMetrics={setSelectedMetrics}
          selectedFamilies={selectedFamilies}
          setSelectedFamilies={setSelectedFamilies}
          analysisScope={analysisScope}
          setAnalysisScope={setAnalysisScope}
          selectedAlgorithm={selectedAlgorithm}
          setSelectedAlgorithm={setSelectedAlgorithm}
          setCurrentStep={setCurrentStep}
          sharedValues={sharedValues}
          setSharedValues={setSharedValues}
          metricOverrides={metricOverrides}
          setMetricOverrides={setMetricOverrides}
          algorithmParams={algorithmParams}
          setAlgorithmParams={setAlgorithmParams}
          analysisMode={analysisMode}
          inputType={detectedInputType}
        />
      </div>
    );
  } else if (currentStep === "9") {
    content = (
      <ResultsPanel
        title={appConfig.panels.results.title}
        resultsGenerated={resultsGenerated}
        onGenerate={handleGenerateResults}
        selectedResultMetric={selectedResultMetric}
        setSelectedResultMetric={setSelectedResultMetric}
        selectedMetrics={resolvedSelectedMetrics}
        summaryResults={summaryResults}
        qcWarnings={qcWarnings}
        metricRegistry={metricRegistry}
        algorithmRegistry={algorithmRegistry}
        selectedAlgorithm={selectedAlgorithm}
        analysisConfig={resolvedAnalysisConfig}
        analysisError={analysisError}
        analysisLoading={analysisLoading}
        analysisMode={analysisMode}
      />
    );
  } else {
    content = (
      <ExportPanel
        title={appConfig.panels.export.title}
        exports={exportRegistry.exports}
        enabled={resultsGenerated}
        summaryResults={summaryResults}
      />
    );
  }

  const canGoPrevious = currentStepIndex > 0;
  const canGoNext = currentStepIndex < workflowSteps.length - 1 && currentStepNumber < Number(maxUnlockedStep) + 1;

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
          Sequential, page-based actigraphy workflow with CSV mapping, native readers, light preview, and registry-driven analysis setup.
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