import React, { useEffect, useMemo, useState } from "react";

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
import ActivityMappingPanel from "../components/ActivityMappingPanel";
import MetricsPanel from "../components/MetricsPanel";
import ResultsPanel from "../components/ResultsPanel";
import ExportPanel from "../components/ExportPanel";
import SupportFilesStep from "../components/SupportFilesStep";
import LightMetricsPanel from "../components/LightMetricsPanel";
import LightRGBPanel from "../components/LightRGBPanel";
import AuthBar from "../components/AuthBar";
import RunHistoryPanel from "../components/RunHistoryPanel";
import FeedbackButton from "../components/FeedbackButton";

import {
  getDefaultAlgorithm,
  getDefaultSelectedMetrics,
  getVisibleWorkflowSteps,
} from "../services/configUtils";
import { buildAnalysisPayload } from "../services/analysisConfigUtils";
import { supabase, supabaseConfigured } from "../services/supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/";
const ENABLE_AUTH_RUNS = import.meta.env.VITE_ENABLE_AUTH_RUNS === "true";

function buildApiUrl(path) {
  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${cleanPath}`;
}

function getExtension(name) {
  const parts = name?.toLowerCase().split(".") || [];
  return parts.length > 1 ? `.${parts.pop()}` : "";
}

function createApiError(message, res, data = null) {
  const error = new Error(message);
  error.httpStatus = res?.status || null;
  error.diagnostics = data?.diagnostics || {
    schema_version: "client-transport-1.0",
    request_id: null,
    endpoint: res?.url || null,
    status: "failed",
    transport: {
      http_status: res?.status || null,
      status_text: res?.statusText || null,
      content_type: res?.headers?.get?.("content-type") || null,
      message,
    },
  };
  return error;
}

function clientFailureDiagnostics(error, file, endpoint) {
  const existing = error?.diagnostics || {};
  return {
    schema_version: existing.schema_version || "client-transport-1.0",
    request_id: existing.request_id || null,
    endpoint: existing.endpoint || endpoint,
    source_file_name: existing.source_file_name || file?.name || null,
    status: existing.status || "failed",
    started_at: existing.started_at || new Date().toISOString(),
    finished_at: new Date().toISOString(),
    total_duration_seconds: existing.total_duration_seconds ?? null,
    error: existing.error || null,
    input_file: existing.input_file || {
      file_name: file?.name || null,
      extension: getExtension(file?.name),
      size_bytes: file?.size ?? null,
      size_mb: file?.size != null ? Number((file.size / (1024 * 1024)).toFixed(3)) : null,
      content_type: file?.type || null,
      sha256: null,
      sha256_status: "not_calculated_in_browser",
    },
    recording: existing.recording || {},
    stages: existing.stages || [],
    events: existing.events || [],
    environment: existing.environment || { browser: navigator.userAgent },
    transport: {
      ...(existing.transport || {}),
      endpoint,
      file_name: file?.name || null,
      file_size_mb: file?.size != null ? Number((file.size / (1024 * 1024)).toFixed(3)) : null,
      message: error?.message || "Request failed before structured backend diagnostics were returned.",
    },
  };
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
  const [selectedAnalysisFileNames, setSelectedAnalysisFileNames] = useState([]);

  const [analysisMode, setAnalysisMode] = useState("standard");
  const [analysisScope, setAnalysisScope] = useState("metric");
  const [selectedFamilies, setSelectedFamilies] = useState([]);
  const [fileError, setFileError] = useState("");

  const [previewLoaded, setPreviewLoaded] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [previewData, setPreviewData] = useState(null);
  const [activityPreviewByFile, setActivityPreviewByFile] = useState({});

  const [lightPreviewLoaded, setLightPreviewLoaded] = useState(false);
  const [lightPreviewData, setLightPreviewData] = useState(null);

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [analysisProgress, setAnalysisProgress] = useState({
    phase: "",
    current: 0,
    total: 0,
    percent: 0,
  });

  const [selectedMetrics, setSelectedMetrics] = useState(
    getDefaultSelectedMetrics(metricRegistry)
  );
  const [selectedAlgorithm, setSelectedAlgorithm] = useState(
    getDefaultAlgorithm(algorithmRegistry)
  );

  const [sharedValues, setSharedValues] = useState({});
  const [metricOverrides, setMetricOverrides] = useState({});
  const [algorithmParams, setAlgorithmParams] = useState({});
  const [sleepWindowSettings, setSleepWindowSettings] = useState({
    estimateWithoutDiary: true,
    method: "crespo_aot",
    minRestWindowHours: 3,
    maxRestWindowHours: 14,
    crespoParams: {
      mode: "default",
      zeta: 15,
      zeta_r: 30,
      zeta_a: 2,
      t: 0.33,
      alpha: "8h",
      beta: "1h",
      estimate_zeta: false,
      seq_length_max: 100,
      verbose: false,
    },
    roennebergParams: {
      mode: "default",
      trend_period: "24h",
      min_trend_period: "12h",
      threshold: 0.15,
      min_seed_period: "30Min",
      max_test_period: "12h",
      r_consec_below: "30Min",
      rsfreq: "",
    },
  });

  const [supportFileSettings, setSupportFileSettings] = useState({
    startStop: { apply: true, manualIntervals: [] },
    masking: { apply: true, manualIntervals: [], respectNonwear: true },
    sleepDiary: { apply: true, manualIntervals: [] },
  });
  const [analysisWindowSettings, setAnalysisWindowSettings] = useState({
    mode: "full",
    intervalPreset: "manual",
    specificDays: [],
    dailyStartTime: "",
    dailyStopTime: "",
    manualIntervals: [],
  });

  const [selectedLightMetrics, setSelectedLightMetrics] = useState(["exposure_level"]);
  const [lightMetricSettings, setLightMetricSettings] = useState({
    channel: "",
    thresholdLux: "",
    startTime: "",
    stopTime: "",
    bins: "24h",
    agg: "mean",
    aggFuncs: "mean,median,sum,std,min,max",
    outputFormat: "minute",
    lmxLength: "5h",
    lowest: true,
    binarizeMetric: false,
  });
  const [lightResults, setLightResults] = useState({});
  const [lightAnalysisError, setLightAnalysisError] = useState("");

  const [activityChannel, setActivityChannel] = useState("VM");
  const [activityMapping, setActivityMapping] = useState("original");
  const [activityTransform, setActivityTransform] = useState("none");
  const [lightTransform, setLightTransform] = useState("none");

  const [csvMapping, setCsvMapping] = useState({
    timestamp_col: "",
    time_col: "",
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
  const [supportFileSummary, setSupportFileSummary] = useState(null);
  const [multiFileResults, setMultiFileResults] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [runSaveStatus, setRunSaveStatus] = useState("");
  const [runHistoryRefresh, setRunHistoryRefresh] = useState(0);

  const actigraphyFiles = uploadedFiles.actigraphy || [];
  const lightFiles = uploadedFiles.light || [];

  const actigraphyFile =
    actigraphyFiles.find((file) => file.name === selectedPreviewFile) ||
    actigraphyFiles[0] ||
    null;

  const lightFile =
    lightFiles.find((file) => file.name === selectedLightPreviewFile) ||
    lightFiles[0] ||
    actigraphyFile ||
    null;

  const selectedAnalysisFiles = useMemo(() => {
    if (!actigraphyFiles.length) return [];
    const selectedNames = new Set(selectedAnalysisFileNames || []);
    return actigraphyFiles.filter((file) => selectedNames.has(file.name));
  }, [actigraphyFiles, selectedAnalysisFileNames]);

  useEffect(() => {
    if (!actigraphyFiles.length) {
      setSelectedAnalysisFileNames([]);
      return;
    }
    setSelectedAnalysisFileNames((prev) => {
      const available = new Set(actigraphyFiles.map((file) => file.name));
      const kept = (prev || []).filter((name) => available.has(name));
      return kept.length ? kept : actigraphyFiles.map((file) => file.name);
    });
  }, [actigraphyFiles]);

  const workflowSteps = useMemo(
    () =>
      getVisibleWorkflowSteps(appConfig, {
        enableCleaning: true,
        enableDiary: true,
      }).filter((step) => showManualMapping || step.key !== "csvMapping"),
    [showManualMapping]
  );

  const currentStepIndex = workflowSteps.findIndex((step) => step.id === currentStep);

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
    () => ({
      ...buildAnalysisPayload({
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
      sleepWindowSettings,
      supportFileSettings,
      analysisWindowSettings,
      lightAnalysisSettings: {
        selectedLightMetrics,
        lightMetricSettings,
      },
    }),
    [
      selectedMetrics,
      selectedFamilies,
      analysisScope,
      selectedAlgorithm,
      sharedValues,
      metricOverrides,
      algorithmParams,
      sleepWindowSettings,
      supportFileSettings,
      analysisWindowSettings,
      selectedLightMetrics,
      lightMetricSettings,
    ]
  );

  const setProgressStage = (phase, current, total) => {
    const safeTotal = Math.max(1, Number(total) || 1);
    const safeCurrent = Math.min(Math.max(0, Number(current) || 0), safeTotal);
    setAnalysisProgress({
      phase,
      current: safeCurrent,
      total: safeTotal,
      percent: Math.round((safeCurrent / safeTotal) * 100),
    });
  };

  const parseJsonResponse = async (res) => {
    const text = await res.text();
    const contentType = res.headers.get("content-type") || "";

    if (!text) {
      const error = createApiError(`Empty response from server (${res.status})`, res);
      error.diagnostics.transport.response_preview = "";
      throw error;
    }

    const looksLikeJson = contentType.includes("application/json") || /^[\s\r\n]*[\[{]/.test(text);

    if (!looksLikeJson) {
      const serverMessage = text
        .replace(/<script[\s\S]*?<\/script>/gi, " ")
        .replace(/<style[\s\S]*?<\/style>/gi, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 1000);

      const message =
        `Server returned ${res.status} ${res.statusText || "non-JSON response"} instead of JSON. ` +
        `This usually means the upload was rejected, the backend ran out of memory, or the request timed out.` +
        (serverMessage ? ` Server message: ${serverMessage}` : "");
      const error = createApiError(message, res);
      error.diagnostics.transport.response_preview = serverMessage;
      error.diagnostics.transport.response_length = text.length;
      throw error;
    }

    try {
      return JSON.parse(text);
    } catch (parseError) {
      const message =
        `Server response was not valid JSON (${res.status}). ` +
        `This can happen when a large raw file crashes the backend during conversion or analysis.`;
      const error = createApiError(message, res);
      error.diagnostics.transport.response_preview = text.slice(0, 1000);
      error.diagnostics.transport.parse_error = parseError.message;
      throw error;
    }
  };

  const goToStep = (stepId) => {
    if (Number(stepId) <= Number(maxUnlockedStep)) {
      setCurrentStep(stepId);
    }
  };

  const unlockStep = (stepId) => {
    const n = Number(stepId);
    if (n > Number(maxUnlockedStep)) {
      setMaxUnlockedStep(String(n));
    }
  };

  const unlockAndGoToStep = (stepId) => {
    unlockStep(stepId);
    setCurrentStep(String(stepId));
  };

  const goPrevious = () => {
    if (currentStepIndex > 0) {
      const prev = workflowSteps[currentStepIndex - 1];
      goToStep(prev.id);
    }
  };

  const resetPreviewAndResults = () => {
    setPreviewLoaded(false);
    setPreviewData(null);
    setActivityPreviewByFile({});
    setLightPreviewLoaded(false);
    setLightPreviewData(null);
    setPreviewError("");
    setResultsGenerated(false);
    setSummaryResults({});
    setMultiFileResults([]);
    setQcWarnings([]);
    setAnalysisError("");
    setLightAnalysisError("");
    setLightResults({});
    setSupportFileSummary(null);
    setAnalysisWindowSettings({
      mode: "full",
      intervalPreset: "manual",
      specificDays: [],
      dailyStartTime: "",
      dailyStopTime: "",
      manualIntervals: [],
    });
  };

  const handleActivityMappingChange = (nextMapping) => {
    setActivityMapping(nextMapping);
    setPreviewLoaded(false);
    setPreviewData(null);
    setActivityPreviewByFile({});
    setResultsGenerated(false);
    setSummaryResults({});
    setMultiFileResults([]);
    setAnalysisError("");
    setPreviewError("");
  };

  const handleActigraphyFilesChange = (files) => {
    setUploadedFiles((prev) => ({ ...prev, actigraphy: files }));
    setSelectedPreviewFile(files?.[0]?.name || "");
    setSelectedLightPreviewFile("");
    setSelectedAnalysisFileNames((files || []).map((file) => file.name));
    resetPreviewAndResults();

    setShowManualMapping(false);
    setCsvMapping({
      timestamp_col: "",
      time_col: "",
      activity_col: "",
      light_col: "",
      temperature_col: "",
      nonwear_col: "",
    });

    unlockStep("3");
  };

  const handleCsvNeedsMapping = () => {
    setShowManualMapping(true);
    unlockAndGoToStep("2");
  };

  const loadActivityPreviewForFile = async (fileName = selectedPreviewFile) => {
    const targetFile =
      actigraphyFiles.find((file) => file.name === fileName) ||
      actigraphyFile;
    if (!targetFile) return null;

    try {
      setPreviewLoading(true);
      setPreviewError("");

      const formData = new FormData();
      formData.append("file", targetFile);
      formData.append("activityChannel", activityChannel);
      formData.append("activityMapping", activityMapping);
      formData.append("resampleFreq", "1min");
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);
      (uploadedFiles.masking || []).forEach((file) => formData.append("maskingFiles", file));
      (uploadedFiles.sleepDiary || []).forEach((file) => formData.append("sleepDiaryFiles", file));
      (uploadedFiles.startStop || []).forEach((file) => formData.append("startStopFiles", file));

      const res = await fetch(buildApiUrl("api/preview/basic"), {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to load activity preview.");
      }

      const labeledData = { ...data, preview_file_name: targetFile.name };
      setSelectedPreviewFile(targetFile.name);
      setPreviewData(labeledData);
      setActivityPreviewByFile((prev) => ({ ...prev, [targetFile.name]: labeledData }));
      setPreviewLoaded(true);
      unlockStep("4");
      return labeledData;
    } catch (err) {
      setPreviewError(err.message || "Failed to load activity preview.");
      setPreviewLoaded(false);
      throw err;
    } finally {
      setPreviewLoading(false);
    }
  };

  const onActivityPreview = async () => {
    try {
      await loadActivityPreviewForFile(selectedPreviewFile);
    } catch (error) {
      // loadActivityPreviewForFile already updates previewError for the UI.
    }
  };

  const onLightPreview = async () => {
    if (!lightFile) return;

    try {
      setPreviewLoading(true);
      setPreviewError("");
      setLightPreviewLoaded(false);
      setLightPreviewData(null);

      const formData = new FormData();
      formData.append("file", lightFile);
      formData.append("resampleFreq", "1min");
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);

      const res = await fetch(buildApiUrl("api/light/preview"), {
        method: "POST",
        body: formData,
      });

      const data = await parseJsonResponse(res);
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to load light preview.");
      }

      setLightPreviewData(data);
      setLightPreviewLoaded(true);
      unlockStep("5");
    } catch (err) {
      setPreviewError(err.message || "Failed to load light preview.");
      setLightPreviewLoaded(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const runSelectedLightMetrics = async (targetFile = lightFile, startingStep = 1, totalSteps = 1, fileLabel = "") => {
    if (!targetFile || selectedLightMetrics.length === 0) {
      return { results: {}, diagnostics: {} };
    }

    const nextLightResults = {};
    const nextLightDiagnostics = {};
    const errors = [];

    for (let index = 0; index < selectedLightMetrics.length; index += 1) {
      const metricId = selectedLightMetrics[index];
      const metricNumber = index + 1;
      setProgressStage(
        `${fileLabel ? `${fileLabel}: ` : ""}Running light metric ${metricNumber} of ${selectedLightMetrics.length}: ${metricId}`,
        startingStep + index,
        totalSteps
      );

      try {
        const formData = new FormData();
        formData.append("file", targetFile);
        formData.append("metricId", metricId);
        formData.append("channel", lightMetricSettings.channel || "");
        formData.append("thresholdLux", lightMetricSettings.thresholdLux || "");
        formData.append("startTime", lightMetricSettings.startTime || "");
        formData.append("stopTime", lightMetricSettings.stopTime || "");
        formData.append("bins", lightMetricSettings.bins || "24h");
        formData.append("agg", lightMetricSettings.agg || "mean");
        formData.append("aggFuncs", lightMetricSettings.aggFuncs || "mean,median,sum,std,min,max");
        formData.append("outputFormat", lightMetricSettings.outputFormat || "minute");
        formData.append("lmxLength", lightMetricSettings.lmxLength || "5h");
        formData.append("lowest", String(lightMetricSettings.lowest !== false));
        formData.append("binarize", String(Boolean(lightMetricSettings.binarizeMetric)));

        const res = await fetch(buildApiUrl("api/light/analyze"), { method: "POST", body: formData });
        const data = await parseJsonResponse(res);

        if (!res.ok) {
          throw createApiError(data?.detail || `Failed to run ${metricId}.`, res, data);
        }

        const { diagnostics: lightDiagnosticPayload, ...lightResultPayload } = data || {};
        nextLightResults[metricId] = lightResultPayload;
        nextLightDiagnostics[metricId] = lightDiagnosticPayload || null;
      } catch (err) {
        errors.push(`${metricId}: ${err.message || "failed"}`);
        nextLightDiagnostics[metricId] = clientFailureDiagnostics(err, targetFile, buildApiUrl("api/light/analyze"));
      } finally {
        setProgressStage(
          `${fileLabel ? `${fileLabel}: ` : ""}Finished light metric ${metricNumber} of ${selectedLightMetrics.length}`,
          startingStep + metricNumber,
          totalSteps
        );
      }
    }

    setLightResults(nextLightResults);
    setLightAnalysisError(errors.length ? errors.join(" | ") : "");
    return { results: nextLightResults, diagnostics: nextLightDiagnostics };
  };

  const handleGenerateResults = async () => {
    const filesToAnalyze = selectedAnalysisFiles;
    if (!filesToAnalyze.length) {
      setAnalysisError("Select at least one file to analyze.");
      unlockAndGoToStep("10");
      return;
    }

    const lightMetricCount = selectedLightMetrics.length;
    const totalSteps = Math.max(1, filesToAnalyze.length * (1 + lightMetricCount));
    let completedSteps = 0;
    const batchResults = [];

    try {
      setAnalysisLoading(true);
      setAnalysisError("");
      setLightAnalysisError("");
      setLightResults({});
      setResultsGenerated(false);
      setMultiFileResults([]);
      setProgressStage(`Preparing ${filesToAnalyze.length} file(s) for analysis`, 0, totalSteps);

      for (let fileIndex = 0; fileIndex < filesToAnalyze.length; fileIndex += 1) {
        const sourceFile = filesToAnalyze[fileIndex];
        const fileLabel = `${sourceFile.name} (${fileIndex + 1}/${filesToAnalyze.length})`;

        try {
          setProgressStage(`Uploading and analyzing ${fileLabel}`, completedSteps, totalSteps);

          const formData = new FormData();
          formData.append("file", sourceFile);
          formData.append("sourceFileName", sourceFile.name);
          formData.append("activityChannel", activityChannel);
          formData.append("activityMapping", activityMapping);
          formData.append("activityTransform", activityTransform);
          formData.append("lightTransform", lightTransform);
          formData.append("analysisMode", analysisMode);
          formData.append("analysisConfig", JSON.stringify(resolvedAnalysisConfig));
          formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
          formData.append("csvSeparator", csvSeparator);
          (uploadedFiles.masking || []).forEach((file) => formData.append("maskingFiles", file));
          (uploadedFiles.sleepDiary || []).forEach((file) => formData.append("sleepDiaryFiles", file));
          (uploadedFiles.startStop || []).forEach((file) => formData.append("startStopFiles", file));

          const res = await fetch(buildApiUrl("api/analyze/basic"), {
            method: "POST",
            body: formData,
          });

          const data = await parseJsonResponse(res);
          if (!res.ok) {
            throw createApiError(data?.detail || "Failed to generate results.", res, data);
          }

          completedSteps += 1;
          setProgressStage(`Activity/sleep metrics complete for ${fileLabel}`, completedSteps, totalSteps);

          const results = data.results || {};
          const lightTargetFile = lightFiles.length > 0 ? lightFile : sourceFile;
          const generatedLightRun = await runSelectedLightMetrics(
            lightTargetFile,
            completedSteps,
            totalSteps,
            sourceFile.name
          );
          const generatedLightResults = generatedLightRun.results;
          const generatedLightDiagnostics = generatedLightRun.diagnostics;
          completedSteps += lightMetricCount;
          setProgressStage(`Finished all selected metrics for ${fileLabel}`, completedSteps, totalSteps);

          const lightHasFailures = Object.values(generatedLightDiagnostics || {}).some(
            (diagnostic) => diagnostic?.status === "failed"
          );
          const activityStatus = data.diagnostics?.status || "completed";
          const combinedStatus = lightHasFailures && activityStatus === "completed"
            ? "completed_with_warnings"
            : activityStatus;

          const row = {
            fileName: sourceFile.name,
            fileSizeMb: Number((sourceFile.size / (1024 * 1024)).toFixed(3)),
            status: combinedStatus,
            results,
            qcWarnings: data.qcWarnings || [],
            supportFileSummary: data.supportFileSummary || null,
            detectedInputType: data.detected_input_type || null,
            activityMapping: data.activity_mapping || { requested: activityMapping, resolved: activityMapping },
            diagnostics: data.diagnostics || null,
            lightResults: generatedLightResults,
            lightDiagnostics: generatedLightDiagnostics,
          };
          batchResults.push(row);
          setMultiFileResults([...batchResults]);

          void saveRunRecord({
            sourceFile,
            status: combinedStatus,
            results,
            qcWarnings: data.qcWarnings || [],
            supportFileSummary: data.supportFileSummary || null,
            detectedInputType: data.detected_input_type || null,
            lightResults: generatedLightResults,
          });
        } catch (err) {
          completedSteps += 1 + lightMetricCount;
          const message = err.message || "Failed to generate results.";
          const row = {
            fileName: sourceFile.name,
            fileSizeMb: Number((sourceFile.size / (1024 * 1024)).toFixed(3)),
            status: "failed",
            error: message,
            results: {},
            qcWarnings: [],
            supportFileSummary: null,
            detectedInputType: null,
            activityMapping: { requested: activityMapping, resolved: activityMapping },
            diagnostics: clientFailureDiagnostics(err, sourceFile, buildApiUrl("api/analyze/basic")),
            lightResults: {},
            lightDiagnostics: {},
          };
          batchResults.push(row);
          setMultiFileResults([...batchResults]);
          setProgressStage(`Failed ${fileLabel}: ${message}`, completedSteps, totalSteps);
          void saveRunRecord({ sourceFile, status: "failed", errorMessage: message });
        }
      }

      const successful = batchResults.filter((item) => ["completed", "completed_with_warnings"].includes(item.status));
      const failed = batchResults.filter((item) => item.status === "failed");

      if (!successful.length) {
        const message = failed.map((item) => `${item.fileName}: ${item.error}`).join(" | ") || "No files could be analyzed.";
        throw new Error(message);
      }

      setSummaryResults(successful[0]?.results || {});
      setQcWarnings(batchResults.flatMap((item) => (item.qcWarnings || []).map((warning) => `${item.fileName}: ${warning}`)));
      setSupportFileSummary(successful.length === 1 ? successful[0].supportFileSummary : null);
      setLightResults(successful.length === 1 ? successful[0].lightResults || {} : {});
      setSelectedResultMetric(Object.keys(successful[0]?.results || {})[0] || "");
      setProgressStage(
        failed.length ? `Analysis complete with ${failed.length} file error(s)` : "Analysis complete",
        totalSteps,
        totalSteps
      );
      setResultsGenerated(true);
      setAnalysisError(failed.length ? `Some files could not be analyzed: ${failed.map((item) => `${item.fileName}: ${item.error}`).join(" | ")}` : "");
      unlockAndGoToStep("10");
    } catch (err) {
      const message = err.message || "Failed to generate results.";
      setAnalysisError(message);
      setAnalysisProgress((prev) => ({
        ...prev,
        phase: message,
      }));
      setResultsGenerated(false);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const saveRunRecord = async ({
    sourceFile = actigraphyFile,
    status = "completed",
    results = {},
    qcWarnings: savedWarnings = [],
    supportFileSummary: savedSupportFileSummary = null,
    detectedInputType: savedDetectedInputType = null,
    lightResults: savedLightResults = {},
    errorMessage = "",
  }) => {
    if (!ENABLE_AUTH_RUNS || !supabaseConfigured || !supabase || !currentUser || !sourceFile) return;

    try {
      const row = {
        user_id: currentUser.id,
        user_email: currentUser.email || null,
        original_filename: sourceFile.name,
        file_type: getExtension(sourceFile.name),
        file_size_mb: Number((sourceFile.size / (1024 * 1024)).toFixed(3)),
        status,
        analysis_mode: analysisMode,
        selected_algorithm: selectedAlgorithm,
        activity_channel: activityChannel,
        activity_mapping: activityMapping,
        detected_input_type: savedDetectedInputType || detectedInputType,
        results: results || {},
        qc_warnings: savedWarnings || [],
        support_file_summary: savedSupportFileSummary || null,
        analysis_config: resolvedAnalysisConfig || {},
        error_message: errorMessage || null,
        app_version: import.meta.env.VITE_APP_VERSION || "frontend-dev",
      };

      const { error } = await supabase.from("analysis_runs").insert(row);
      if (error) throw error;

      setRunSaveStatus("Saved this analysis to your account.");
      setRunHistoryRefresh((value) => value + 1);
    } catch (err) {
      setRunSaveStatus(`Could not save run history: ${err.message || "Unknown error"}`);
    }
  };

  const handleLoadSavedRun = (run) => {
    const savedResults = run.results || {};
    setActivityMapping(run.activity_mapping || "original");
    setSummaryResults(savedResults);
    setQcWarnings(run.qc_warnings || []);
    setSupportFileSummary(run.support_file_summary || null);
    setMultiFileResults([]);
    setSelectedResultMetric(Object.keys(savedResults)[0] || "");
    setResultsGenerated(Object.keys(savedResults).length > 0);
    setAnalysisError(run.error_message || "");
    setLightResults({});
    setLightAnalysisError("");
    unlockAndGoToStep("10");
  };

  const getStepValidation = () => {
    switch (currentStep) {
      case "1":
        return {
          valid: actigraphyFiles.length > 0,
          message: actigraphyFiles.length > 0 ? "" : "Upload at least one actigraphy file.",
        };
      case "2":
        return {
          valid: !showManualMapping || Boolean(csvMapping.timestamp_col && csvMapping.activity_col),
          message:
            !showManualMapping || (csvMapping.timestamp_col && csvMapping.activity_col)
              ? ""
              : "Select timestamp and activity columns to continue.",
        };
      case "3":
        return {
          valid: true,
          message: previewLoaded
            ? ""
            : "Activity preview is optional. Load it if you want to inspect one file, or click Next to continue.",
        };
      case "4":
        return {
          valid: true,
          message: lightPreviewLoaded
            ? ""
            : "Light preview is optional. Load it if light channels exist, or click Next to skip.",
        };
      case "5":
      case "6":
      case "7":
      case "8":
        return {
          valid: true,
          message: "",
        };
      case "9": {
        const hasMetrics =
          analysisMode === "standard"
            ? resolvedSelectedMetrics.length > 0
            : analysisScope === "family"
            ? selectedFamilies.length > 0
            : selectedMetrics.length > 0;

        const hasAlgorithm = Boolean(selectedAlgorithm);
        const hasAnalysisFiles = selectedAnalysisFileNames.length > 0;

        const selectedIntervalPreset = analysisWindowSettings.intervalPreset || "manual";
        const hasRequiredSpecificDays =
          selectedIntervalPreset !== "specific_days" ||
          (analysisWindowSettings.specificDays || []).length > 0;

        const intervalModeValid =
          !["selected", "both"].includes(analysisWindowSettings.mode) ||
          (
            selectedIntervalPreset !== "manual" &&
            hasRequiredSpecificDays
          ) ||
          (analysisWindowSettings.manualIntervals || []).length > 0;

        return {
          valid: hasMetrics && hasAlgorithm && intervalModeValid && hasAnalysisFiles,
          message: !hasAnalysisFiles
            ? "Select at least one uploaded file to analyze."
            : !hasMetrics || !hasAlgorithm
            ? "Select an algorithm and at least one metric or family."
            : !intervalModeValid
            ? "Add at least one manual analysis interval, choose weekdays/weekends/specific days, or switch back to Analyze whole file."
            : "",
        };
      }
      case "10":
        return {
          valid: resultsGenerated,
          message: resultsGenerated ? "" : "Generate results to continue.",
        };
      default:
        return {
          valid: true,
          message: "",
        };
    }
  };

  const stepValidation = getStepValidation();

  const goNext = () => {
    if (!stepValidation.valid) return;

    if (currentStep === "1" && !showManualMapping) {
      unlockAndGoToStep("3");
      return;
    }

    if (currentStep === "2" && !showManualMapping) {
      unlockAndGoToStep("3");
      return;
    }

    if (currentStep === "4" && !lightPreviewLoaded) {
      unlockAndGoToStep("6");
      return;
    }

    if (currentStepIndex < workflowSteps.length - 1) {
      const next = workflowSteps[currentStepIndex + 1];
      unlockAndGoToStep(next.id);
    }
  };

  const detectedInputType =
    previewData?.detected_input_type ||
    getExtension(actigraphyFile?.name || "").replace(".", "") ||
    "unknown";

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
        showManualMapping={showManualMapping}
        setShowManualMapping={setShowManualMapping}
      />
    );
  } else if (currentStep === "2" && !showManualMapping) {
    content = (
      <PreviewPanel
        title={appConfig.panels.preview.title}
        mode="activity"
        previewLoaded={previewLoaded}
        previewLoading={previewLoading}
        previewError={previewError}
        previewData={previewData}
        actigraphyFiles={actigraphyFiles}
        selectedPreviewFile={selectedPreviewFile}
        setSelectedPreviewFile={setSelectedPreviewFile}
        lightFiles={lightFiles}
        selectedLightPreviewFile={selectedLightPreviewFile}
        setSelectedLightPreviewFile={setSelectedLightPreviewFile}
        activityMapping={activityMapping}
        setActivityMapping={handleActivityMappingChange}
        onPreview={onActivityPreview}
      />
    );
  } else if (currentStep === "2" && showManualMapping) {
    content = (
      <CsvMappingPanel
        title={appConfig.panels.csvMapping.title}
        csvFile={actigraphyFile}
        csvMapping={csvMapping}
        setCsvMapping={setCsvMapping}
        csvSeparator={csvSeparator}
        setCsvSeparator={setCsvSeparator}
        onContinue={onActivityPreview}
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
        actigraphyFiles={actigraphyFiles}
        selectedPreviewFile={selectedPreviewFile}
        setSelectedPreviewFile={setSelectedPreviewFile}
        lightFiles={lightFiles}
        selectedLightPreviewFile={selectedLightPreviewFile}
        setSelectedLightPreviewFile={setSelectedLightPreviewFile}
        activityMapping={activityMapping}
        setActivityMapping={handleActivityMappingChange}
        onPreview={onActivityPreview}
      />
    );
  } else if (currentStep === "4") {
    content = (
      <div style={{ display: "grid", gap: 16 }}>
        <PreviewPanel
          title={appConfig.panels.lightPreview.title}
          mode="light"
          previewLoaded={lightPreviewLoaded}
          previewLoading={previewLoading}
          previewError={previewError}
          previewData={lightPreviewData}
          actigraphyFiles={actigraphyFiles}
          selectedPreviewFile={selectedPreviewFile}
          setSelectedPreviewFile={setSelectedPreviewFile}
          lightFiles={lightFiles}
          selectedLightPreviewFile={selectedLightPreviewFile}
          setSelectedLightPreviewFile={setSelectedLightPreviewFile}
          onPreview={onLightPreview}
        />

        {lightFile && <LightRGBPanel lightFile={lightFile} />}
      </div>
    );
  } else if (currentStep === "6") {
    content = (
      <SupportFilesStep
        title={appConfig.panels.startStop.title}
        type="startStop"
        description="Start/stop files define the true recording interval and should be applied before masking or sleep scoring."
        files={uploadedFiles.startStop}
        onFilesChange={(files) => setUploadedFiles((prev) => ({ ...prev, startStop: files }))}
        settings={supportFileSettings.startStop}
        onSettingsChange={(settings) =>
          setSupportFileSettings((prev) => ({ ...prev, startStop: settings }))
        }
        options={[
          { id: "apply", label: "Apply uploaded or manually selected start/stop intervals", defaultValue: true },
        ]}
        previewData={previewData}
        previewDataByFile={activityPreviewByFile}
        actigraphyFiles={actigraphyFiles}
        onLoadPreviewForFile={loadActivityPreviewForFile}
      />
    );
  } else if (currentStep === "7") {
    content = (
      <SupportFilesStep
        title={appConfig.panels.cleaning.title}
        type="masking"
        description="Masking excludes invalid, non-wear, or spurious inactivity periods before analysis."
        files={uploadedFiles.masking}
        onFilesChange={(files) => setUploadedFiles((prev) => ({ ...prev, masking: files }))}
        settings={supportFileSettings.masking}
        onSettingsChange={(settings) =>
          setSupportFileSettings((prev) => ({ ...prev, masking: settings }))
        }
        options={[
          { id: "apply", label: "Apply uploaded or manually selected masking intervals", defaultValue: true },
          { id: "respectNonwear", label: "Respect detected non-wear when available", defaultValue: true },
        ]}
        previewData={previewData}
        previewDataByFile={activityPreviewByFile}
        actigraphyFiles={actigraphyFiles}
        onLoadPreviewForFile={loadActivityPreviewForFile}
      />
    );
  } else if (currentStep === "8") {
    content = (
      <SupportFilesStep
        title={appConfig.panels.sleepDiary.title}
        type="sleepDiary"
        description="Sleep diary files provide reported bedtimes, wake times, naps, or diary states for sleep-specific summaries."
        files={uploadedFiles.sleepDiary}
        onFilesChange={(files) => setUploadedFiles((prev) => ({ ...prev, sleepDiary: files }))}
        settings={supportFileSettings.sleepDiary}
        onSettingsChange={(settings) =>
          setSupportFileSettings((prev) => ({ ...prev, sleepDiary: settings }))
        }
        options={[
          { id: "apply", label: "Use uploaded or manually selected diary windows when available", defaultValue: true },
        ]}
        previewData={previewData}
        previewDataByFile={activityPreviewByFile}
        actigraphyFiles={actigraphyFiles}
        onLoadPreviewForFile={loadActivityPreviewForFile}
      />
    );
  } else if (currentStep === "9") {
    content = (
      <div style={{ display: "grid", gap: 16 }}>
        <ActivityMappingPanel
          value={activityMapping}
          onChange={handleActivityMappingChange}
        />
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
          sharedValues={sharedValues}
          setSharedValues={setSharedValues}
          metricOverrides={metricOverrides}
          setMetricOverrides={setMetricOverrides}
          algorithmParams={algorithmParams}
          setAlgorithmParams={setAlgorithmParams}
          sleepWindowSettings={sleepWindowSettings}
          setSleepWindowSettings={setSleepWindowSettings}
          analysisMode={analysisMode}
          inputType={detectedInputType}
          previewData={previewData}
          analysisWindowSettings={analysisWindowSettings}
          setAnalysisWindowSettings={setAnalysisWindowSettings}
        />
        <LightMetricsPanel
          lightFile={lightFile}
          selectedLightMetrics={selectedLightMetrics}
          setSelectedLightMetrics={setSelectedLightMetrics}
          lightMetricSettings={lightMetricSettings}
          setLightMetricSettings={setLightMetricSettings}
          previewData={lightPreviewData || previewData}
        />
      </div>
    );
  } else if (currentStep === "10") {
    content = (
      <ResultsPanel
        title={appConfig.panels.results.title}
        actigraphyFiles={actigraphyFiles}
        selectedAnalysisFileNames={selectedAnalysisFileNames}
        setSelectedAnalysisFileNames={setSelectedAnalysisFileNames}
        multiFileResults={multiFileResults}
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
        analysisProgress={analysisProgress}
        analysisMode={analysisMode}
        activityMapping={activityMapping}
        supportFileSummary={supportFileSummary}
        lightResults={lightResults}
        selectedLightMetrics={selectedLightMetrics}
        lightMetricSettings={lightMetricSettings}
        lightAnalysisError={lightAnalysisError}
      />
    );
  } else {
    content = (
      <ExportPanel
        title={appConfig.panels.export.title}
        exportRegistry={exportRegistry}
        resultsGenerated={resultsGenerated}
        summaryResults={summaryResults}
        qcWarnings={qcWarnings}
        metricRegistry={metricRegistry}
        algorithmRegistry={algorithmRegistry}
        analysisConfig={resolvedAnalysisConfig}
        selectedAlgorithm={selectedAlgorithm}
        analysisMode={analysisMode}
        supportFileSummary={supportFileSummary}
        lightResults={lightResults}
      />
    );
  }

  const canGoPrevious = currentStepIndex > 0;
  const canGoNext = currentStepIndex < workflowSteps.length - 1 && stepValidation.valid;

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
          Sequential actigraphy workflow with separate activity and light preview, optional mapping, support files, and family-aware analysis.
        </p>

        {ENABLE_AUTH_RUNS && (
          <>
            <AuthBar onUserChange={setCurrentUser} />
            {runSaveStatus && (
              <div
                style={{
                  background: runSaveStatus.startsWith("Saved") ? "#f0fdf4" : "#fef2f2",
                  border: runSaveStatus.startsWith("Saved") ? "1px solid #bbf7d0" : "1px solid #fecaca",
                  color: runSaveStatus.startsWith("Saved") ? "#166534" : "#b91c1c",
                  borderRadius: 12,
                  padding: 10,
                  fontSize: 14,
                  marginBottom: 16,
                }}
              >
                {runSaveStatus}
              </div>
            )}
            <RunHistoryPanel
              user={currentUser}
              refreshToken={runHistoryRefresh}
              onLoadRun={handleLoadSavedRun}
            />
          </>
        )}

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
                alignItems: "center",
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

              <div
                style={{
                  flex: 1,
                  textAlign: "center",
                  color: stepValidation.valid ? "#64748b" : "#b91c1c",
                  fontSize: 14,
                }}
              >
                {stepValidation.message}
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                {currentStep === "9" && (
                  <button
                    type="button"
                    onClick={handleGenerateResults}
                    style={{
                      padding: "10px 16px",
                      borderRadius: 12,
                      background: "#0f172a",
                      color: "white",
                      border: "none",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Generate Results
                  </button>
                )}

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

      <FeedbackButton
        buildApiUrl={buildApiUrl}
        user={currentUser}
        context={{
          currentStep,
          fileName: actigraphyFile?.name || "",
          fileType: getExtension(actigraphyFile?.name || ""),
          fileSizeMb: actigraphyFile ? Number((actigraphyFile.size / (1024 * 1024)).toFixed(3)) : null,
          previewError,
          analysisError,
          fileError,
          endpoint: analysisError ? "api/analyze/basic" : previewError ? "api/preview/basic" : "",
          appVersion: import.meta.env.VITE_APP_VERSION || "frontend-dev",
          backendUrl: API_BASE_URL,
        }}
      />
    </div>
  );
}