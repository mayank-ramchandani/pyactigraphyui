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
import PreprocessingPanel from "../components/PreprocessingPanel";
import OtherSensorsPanel from "../components/OtherSensorsPanel";
import AuthBar from "../components/AuthBar";
import RunHistoryPanel from "../components/RunHistoryPanel";
import FeedbackButton from "../components/FeedbackButton";
import DocumentationPanel from "../components/DocumentationPanel";

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

function createRequestId() {
  try {
    return crypto.randomUUID();
  } catch (_error) {
    return `analysis-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

function postFormDataWithUploadProgress(url, formData, onUploadProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    // Required for Azure Container Apps cookie-based session affinity when
    // the frontend and backend are hosted on different origins.
    xhr.withCredentials = true;

    xhr.upload.onprogress = (event) => {
      if (typeof onUploadProgress === "function" && event.lengthComputable) {
        onUploadProgress(event.loaded, event.total);
      }
    };

    xhr.onerror = () => reject(new Error("Network error while uploading the recording."));
    xhr.ontimeout = () => reject(new Error("The upload or analysis request timed out."));
    xhr.onabort = () => reject(new Error("The upload or analysis request was cancelled."));
    xhr.onload = () => {
      const responseText = xhr.responseText || "";
      const contentType = xhr.getResponseHeader("content-type") || "";
      resolve({
        ok: xhr.status >= 200 && xhr.status < 300,
        status: xhr.status,
        statusText: xhr.statusText,
        url,
        headers: {
          get: (name) => String(name || "").toLowerCase() === "content-type" ? contentType : null,
        },
        text: async () => responseText,
      });
    };

    xhr.send(formData);
  });
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
  const [documentationOpen, setDocumentationOpen] = useState(false);
  const [maxUnlockedStep, setMaxUnlockedStep] = useState("1");
  const [visitedSteps, setVisitedSteps] = useState(["1"]);

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
    filePercent: 0,
    detail: "",
    requestId: null,
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
    masking: {
      apply: true,
      manualIntervals: [],
      respectNonwear: true,
      customizeDataQualityThresholds: false,
      minimumValidHoursPerDay: 16,
      minimumValidDaysForRhythm: 2,
      minimumSleepWindowCoverage: 0.8,
    },
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
  const [previewActivityMapping, setPreviewActivityMapping] = useState("auto");
  const [activityMapping, setActivityMapping] = useState("auto");
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
  const [dataQuality, setDataQuality] = useState(null);
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

  const requestedLightFile =
    lightFiles.find((file) => file.name === selectedLightPreviewFile) ||
    lightFiles[0] ||
    actigraphyFile ||
    null;
  const lightFile = requestedLightFile;
  const lightInspectionMatchesSelection =
    Boolean(lightFile) &&
    lightPreviewData?.light_preview_file_name === lightFile.name &&
    Boolean(lightPreviewData?.light_detection?.inspected);
  const selectedFileHasNoLight =
    lightInspectionMatchesSelection &&
    lightPreviewData?.light_detection?.available === false;
  const lightSourceMessage = selectedFileHasNoLight
    ? lightPreviewData?.message ||
      "This file contains no embedded light measurements. Light preview and metrics will be skipped."
    : "";
  const lightMetricFile = selectedFileHasNoLight ? null : lightFile;

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

  useEffect(() => {
    if (!actigraphyFiles.length) {
      setMaxUnlockedStep("1");
      setVisitedSteps(["1"]);
      if (currentStep !== "1") setCurrentStep("1");
      return;
    }

    setMaxUnlockedStep(resultsGenerated ? "10" : "9");
    if (!resultsGenerated && currentStep === "10") setCurrentStep("9");
  }, [actigraphyFiles.length, currentStep, resultsGenerated]);

  const workflowSteps = useMemo(
    () =>
      getVisibleWorkflowSteps(appConfig, {
        enableCleaning: true,
        enableDiary: true,
      }),
    []
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
      futureSensorAttachments: {
        temperatureAndOther: (uploadedFiles.temperature || []).map((file) => ({
          name: file.name,
          sizeBytes: file.size,
          contentType: file.type || null,
          lastModified: file.lastModified || null,
        })),
        analysisStatus: "not_implemented",
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
      uploadedFiles.temperature,
    ]
  );

  const setProgressStage = (phase, current, total) => {
    const safeTotal = Math.max(1, Number(total) || 1);
    const safeCurrent = Math.min(Math.max(0, Number(current) || 0), safeTotal);
    setAnalysisProgress((previous) => ({
      ...previous,
      phase,
      current: safeCurrent,
      total: safeTotal,
      percent: Math.round((safeCurrent / safeTotal) * 100),
      filePercent: Math.round((safeCurrent / safeTotal) * 100),
      detail: "",
    }));
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

  const waitForBackgroundJob = async (jobId, onUpdate = null, acceptedRuntime = null) => {
    const startedAt = Date.now();
    const maxWaitMs = 6 * 60 * 60 * 1000;
    const discoveryGraceMs = 60 * 1000;
    let consecutivePollFailures = 0;
    let lastMissingJobPayload = null;

    while (Date.now() - startedAt < maxWaitMs) {
      try {
        const statusResponse = await fetch(buildApiUrl(`api/jobs/${encodeURIComponent(jobId)}`), {
          cache: "no-store",
          credentials: "include",
        });
        const statusData = await parseJsonResponse(statusResponse);
        if (!statusResponse.ok) {
          if (
            statusResponse.status === 404 &&
            statusData?.code === "background_job_not_found" &&
            Date.now() - startedAt < discoveryGraceMs
          ) {
            // A different replica/revision may answer one poll. Keep trying
            // long enough for affinity/routing to settle instead of discarding
            // a job which is still processing successfully elsewhere.
            lastMissingJobPayload = statusData;
            consecutivePollFailures = 0;
            await new Promise((resolve) => window.setTimeout(resolve, 1000));
            continue;
          }
          if (statusResponse.status === 404 && statusData?.code === "background_job_not_found") {
            const accepted = acceptedRuntime || {};
            const polled = statusData?.runtime || lastMissingJobPayload?.runtime || {};
            const acceptedLocation = [accepted.revision, accepted.replica].filter(Boolean).join(" / ");
            const polledLocation = [polled.revision, polled.replica].filter(Boolean).join(" / ");
            const locationDetail =
              acceptedLocation || polledLocation
                ? ` Upload accepted by ${acceptedLocation || "an unknown instance"}; polling reached ${polledLocation || "an unknown instance"}.`
                : "";
            const error = createApiError(
              `Background job state was lost or is stored on another backend replica.${locationDetail} ` +
                "Use one active revision and one replica, or mount shared persistent storage at APP_DATA_DIR.",
              statusResponse,
              statusData
            );
            error.backgroundJobTerminal = true;
            throw error;
          }
          throw createApiError(statusData?.detail || "Could not read background job status.", statusResponse, statusData);
        }
        consecutivePollFailures = 0;
        if (typeof onUpdate === "function") onUpdate(statusData);

        if (statusData.status === "completed") {
          const resultStatus = Number(statusData.result_http_status || 200);
          const result = statusData.result || {};
          if (resultStatus < 200 || resultStatus >= 400) {
            const error = new Error(result?.detail || "Background processing returned an error.");
            error.httpStatus = resultStatus;
            error.diagnostics = result?.diagnostics || null;
            error.backgroundJobTerminal = true;
            throw error;
          }
          return result;
        }

        if (statusData.status === "failed") {
          const result = statusData.result || {};
          const error = new Error(result?.detail || statusData.message || "Background processing failed.");
          error.httpStatus = Number(statusData.result_http_status || 500);
          error.diagnostics = result?.diagnostics || null;
          error.backgroundJobTerminal = true;
          throw error;
        }
      } catch (error) {
        // A transient polling failure should not discard a job that is still
        // running successfully in the container.
        const pollStatus = Number(error?.httpStatus || 0);
        if (error?.backgroundJobTerminal || (pollStatus >= 400 && pollStatus < 500)) throw error;
        consecutivePollFailures += 1;
        if (consecutivePollFailures >= 8) throw error;
      }

      await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }

    throw new Error("Background processing exceeded the six-hour job wait limit.");
  };

  const runBackgroundFormJob = async ({
    path,
    formData,
    jobId,
    onUploadProgress = null,
    onUpdate = null,
  }) => {
    if (!formData.has("jobId")) formData.append("jobId", jobId);
    let startResponse;

    try {
      startResponse = await postFormDataWithUploadProgress(
        buildApiUrl(path),
        formData,
        onUploadProgress
      );
      const startData = await parseJsonResponse(startResponse);
      if (!startResponse.ok) {
        throw createApiError(startData?.detail || "Could not start background processing.", startResponse, startData);
      }
      return waitForBackgroundJob(startData.job_id || jobId, onUpdate, startData.runtime || null);
    } catch (error) {
      // If ingress closed exactly as the upload completed, the server may still
      // have accepted the known client-generated job ID. Recover by polling it.
      if ([503, 504].includes(Number(error?.httpStatus))) {
        try {
          const recoveryResponse = await fetch(buildApiUrl(`api/jobs/${encodeURIComponent(jobId)}`), {
            cache: "no-store",
            credentials: "include",
          });
          if (recoveryResponse.ok) return waitForBackgroundJob(jobId, onUpdate);
        } catch (_recoveryError) {
          // Preserve the original transport error when no job was created.
        }
      }
      throw error;
    }
  };

  const goToStep = (stepId) => {
    if (Number(stepId) <= Number(maxUnlockedStep)) {
      const resolvedStepId = String(stepId);
      setCurrentStep(resolvedStepId);
      setVisitedSteps((previous) => Array.from(new Set([...(previous || []), resolvedStepId])));
    }
  };

  const unlockStep = (stepId) => {
    const n = Number(stepId);
    if (n > Number(maxUnlockedStep)) {
      setMaxUnlockedStep(String(n));
    }
  };

  const unlockAndGoToStep = (stepId) => {
    const resolvedStepId = String(stepId);
    unlockStep(resolvedStepId);
    setCurrentStep(resolvedStepId);
    setVisitedSteps((previous) => Array.from(new Set([...(previous || []), resolvedStepId])));
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

  const handlePreviewActivityMappingChange = (nextMapping) => {
    setPreviewActivityMapping(nextMapping);
    setPreviewLoaded(false);
    setPreviewData(null);
    setActivityPreviewByFile({});
    setPreviewError("");
  };

  const handleActivityMappingChange = (nextMapping) => {
    setActivityMapping(nextMapping);
    setPreviewActivityMapping(nextMapping);
    setPreviewLoaded(false);
    setPreviewData(null);
    setActivityPreviewByFile({});
    setResultsGenerated(false);
    setSummaryResults({});
    setMultiFileResults([]);
    setAnalysisError("");
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

    setMaxUnlockedStep(files?.length ? "9" : "1");
    setVisitedSteps(["1"]);
  };

  const handleCsvNeedsMapping = () => {
    setShowManualMapping(true);
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
      formData.append("activityMapping", previewActivityMapping);
      formData.append("resampleFreq", "1min");
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);
      (uploadedFiles.masking || []).forEach((file) => formData.append("maskingFiles", file));
      (uploadedFiles.sleepDiary || []).forEach((file) => formData.append("sleepDiaryFiles", file));
      (uploadedFiles.startStop || []).forEach((file) => formData.append("startStopFiles", file));
      const previewJobId = createRequestId();
      const data = await runBackgroundFormJob({
        path: "api/jobs/preview/basic",
        formData,
        jobId: previewJobId,
      });

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
    if (!lightFile) {
      setPreviewError(lightSourceMessage || "Select a supported light file before loading the light preview.");
      setLightPreviewLoaded(false);
      setLightPreviewData(null);
      return;
    }

    try {
      setPreviewLoading(true);
      setPreviewError("");
      setLightPreviewLoaded(false);
      setLightPreviewData(null);

      const formData = new FormData();
      formData.append("file", lightFile);
      formData.append("resampleFreq", "1min");
      formData.append("rgbResampleFreq", "5min");
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);
      const lightPreviewJobId = createRequestId();
      const data = await runBackgroundFormJob({
        path: "api/jobs/light/preview",
        formData,
        jobId: lightPreviewJobId,
      });

      const labeledData = {
        ...data,
        light_preview_file_name: lightFile.name,
      };
      setLightPreviewData(labeledData);
      setLightPreviewLoaded(true);
      unlockStep(data?.light_preview_available ? "5" : "6");
    } catch (err) {
      setPreviewError(err.message || "Failed to load light preview.");
      setLightPreviewLoaded(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const runSelectedLightMetrics = async (targetFile = lightFile, startingStep = 1, totalSteps = 1, fileLabel = "") => {
    if (selectedLightMetrics.length === 0) {
      return { results: {}, diagnostics: {} };
    }
    const targetAlreadyInspectedWithoutLight =
      Boolean(targetFile) &&
      lightPreviewData?.light_preview_file_name === targetFile.name &&
      lightPreviewData?.light_detection?.inspected === true &&
      lightPreviewData?.light_detection?.available === false;
    if (targetAlreadyInspectedWithoutLight) {
      const message =
        lightPreviewData?.message ||
        "This file contains no embedded light measurements, so light metrics were skipped.";
      const diagnostics = Object.fromEntries(
        selectedLightMetrics.map((metricId) => [
          metricId,
          { status: "skipped", metric_id: metricId, message },
        ])
      );
      setLightResults({});
      setLightAnalysisError(message);
      setProgressStage(
        `${fileLabel ? `${fileLabel}: ` : ""}No light data found; light metrics skipped`,
        startingStep + selectedLightMetrics.length,
        totalSteps
      );
      return {
        results: {},
        diagnostics,
        detection: lightPreviewData.light_detection,
        skipped: true,
      };
    }
    if (!targetFile) {
      const message =
        lightSourceMessage ||
        "No supported light source is available, so the selected light metrics were skipped.";
      setLightAnalysisError(message);
      return {
        results: {},
        diagnostics: {
          light_source: {
            status: "skipped",
            message,
          },
        },
      };
    }

    setProgressStage(
      `${fileLabel ? `${fileLabel}: ` : ""}Inspecting light data and running ${selectedLightMetrics.length} selected light metric(s)`,
      startingStep,
      totalSteps
    );

    try {
      const formData = new FormData();
      formData.append("file", targetFile);
      formData.append("metricIds", JSON.stringify(selectedLightMetrics));
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
      formData.append("csvMapping", JSON.stringify(showManualMapping ? csvMapping : {}));
      formData.append("csvSeparator", csvSeparator);

      const lightAnalysisJobId = createRequestId();
      formData.append("requestId", lightAnalysisJobId);
      const data = await runBackgroundFormJob({
        path: "api/jobs/light/analyze",
        formData,
        jobId: lightAnalysisJobId,
        onUpdate: (jobData) => {
          const progressData = jobData?.progress;
          if (!progressData) return;
          setAnalysisProgress((previous) => ({
            ...previous,
            phase: `${fileLabel ? `${fileLabel}: ` : ""}${progressData.message || "Inspecting and analyzing light data"}`,
            detail: progressData.stage_label || "",
          }));
        },
      });

      const nextLightResults = data?.results || {};
      const nextLightDiagnostics = data?.metric_diagnostics || {};
      if (data?.diagnostics && selectedLightMetrics.length > 0) {
        const firstMetric = selectedLightMetrics[0];
        nextLightDiagnostics[firstMetric] = {
          ...(nextLightDiagnostics[firstMetric] || {}),
          pipeline_diagnostics: data.diagnostics,
        };
      }

      const errors = Array.isArray(data?.metric_errors) ? data.metric_errors : [];
      const message = data?.skipped ? data?.message || "No embedded light data were found." : "";
      setLightResults(nextLightResults);
      setLightAnalysisError(errors.length ? errors.join(" | ") : message);
      setProgressStage(
        `${fileLabel ? `${fileLabel}: ` : ""}${
          data?.skipped ? "No light data found; light metrics skipped" : "Light metrics complete"
        }`,
        startingStep + selectedLightMetrics.length,
        totalSteps
      );
      return {
        results: nextLightResults,
        diagnostics: nextLightDiagnostics,
        detection: data?.light_detection || null,
        skipped: Boolean(data?.skipped),
      };
    } catch (err) {
      const endpoint = buildApiUrl("api/jobs/light/analyze");
      const diagnostics = Object.fromEntries(
        selectedLightMetrics.map((metricId) => [
          metricId,
          clientFailureDiagnostics(err, targetFile, endpoint),
        ])
      );
      setLightAnalysisError(err.message || "Light analysis failed.");
      return { results: {}, diagnostics };
    }
  };

  const handleGenerateResults = async () => {
    const filesToAnalyze = selectedAnalysisFiles;
    if (!filesToAnalyze.length) {
      setAnalysisError("Select at least one file to analyze.");
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

          const requestId = createRequestId();
          formData.append("requestId", requestId);

          let progressTimer = null;
          let lastBackendProgress = 0;
          const updateOverallFileProgress = (fileFraction, progressPayload = {}) => {
            const boundedFileFraction = Math.min(1, Math.max(0, Number(fileFraction) || 0));
            const overallPercent = Math.round(((completedSteps + boundedFileFraction) / totalSteps) * 100);
            setAnalysisProgress((previous) => ({
              ...previous,
              phase: progressPayload.phase || previous.phase,
              current: progressPayload.current ?? previous.current,
              total: progressPayload.total ?? previous.total,
              percent: overallPercent,
              filePercent: Math.round(boundedFileFraction * 100),
              detail: progressPayload.detail || "",
              requestId,
            }));
          };

          const pollBackendProgress = async () => {
            try {
              const progressResponse = await fetch(buildApiUrl(`api/progress/${encodeURIComponent(requestId)}`), {
                cache: "no-store",
                credentials: "include",
              });
              if (!progressResponse.ok) return;
              const progressData = await progressResponse.json();
              const backendPercent = Math.max(lastBackendProgress, Number(progressData.percent) || 0);
              lastBackendProgress = backendPercent;
              const fileFraction = 0.05 + (backendPercent / 100) * 0.95;
              const detailParts = [];
              if (progressData.details?.pages_decoded != null) {
                detailParts.push(`${Number(progressData.details.pages_decoded).toLocaleString()} pages decoded`);
              }
              if (progressData.details?.samples_decoded != null) {
                detailParts.push(`${Number(progressData.details.samples_decoded).toLocaleString()} samples decoded`);
              }
              updateOverallFileProgress(fileFraction, {
                phase: `${fileLabel}: ${progressData.message || progressData.stage_label || "Running analysis"}`,
                current: progressData.stage_current || 0,
                total: progressData.stage_total || 0,
                detail: detailParts.join(" · "),
              });
            } catch (_error) {
              // Progress polling is advisory; the analysis request remains authoritative.
            }
          };

          progressTimer = window.setInterval(pollBackendProgress, 750);
          const data = await runBackgroundFormJob({
            path: "api/jobs/analyze/basic",
            formData,
            jobId: requestId,
            onUploadProgress: (loaded, total) => {
              const uploadFraction = total > 0 ? loaded / total : 0;
              updateOverallFileProgress(uploadFraction * 0.05, {
                phase: `${fileLabel}: Uploading recording (${Math.round(uploadFraction * 100)}%)`,
                current: 0,
                total: 0,
                detail: `${(loaded / (1024 * 1024)).toFixed(1)} of ${(total / (1024 * 1024)).toFixed(1)} MB uploaded`,
              });
            },
            onUpdate: (jobData) => {
              const progressData = jobData?.progress;
              if (!progressData) return;
              const backendPercent = Math.max(lastBackendProgress, Number(progressData.percent) || 0);
              lastBackendProgress = backendPercent;
              updateOverallFileProgress(0.05 + (backendPercent / 100) * 0.95, {
                phase: `${fileLabel}: ${progressData.message || progressData.stage_label || jobData.message || "Running analysis"}`,
                current: progressData.stage_current || 0,
                total: progressData.stage_total || 0,
              });
            },
          }).finally(() => {
            if (progressTimer) window.clearInterval(progressTimer);
          });
          await pollBackendProgress();

          completedSteps += 1;
          setProgressStage(`Activity/sleep metrics complete for ${fileLabel}`, completedSteps, totalSteps);

          const results = data.results || {};
          const lightTargetFile =
            lightFiles.length > 0
              ? lightFile
              : sourceFile;
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
            dataQuality: data.dataQuality || null,
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
            dataQuality: null,
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
      setDataQuality(successful.length === 1 ? successful[0].dataQuality : null);
      setLightResults(successful.length === 1 ? successful[0].lightResults || {} : {});
      setSelectedResultMetric(Object.keys(successful[0]?.results || {})[0] || "");
      setProgressStage(
        failed.length ? `Analysis complete with ${failed.length} file error(s)` : "Analysis complete",
        totalSteps,
        totalSteps
      );
      setResultsGenerated(true);
      setAnalysisError(failed.length ? `Some files could not be analyzed: ${failed.map((item) => `${item.fileName}: ${item.error}`).join(" | ")}` : "");
      unlockStep("10");
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
    setActivityMapping(run.activity_mapping || "auto");
    setSummaryResults(savedResults);
    setQcWarnings(run.qc_warnings || []);
    setSupportFileSummary(run.support_file_summary || null);
    setMultiFileResults([]);
    setSelectedResultMetric(Object.keys(savedResults)[0] || "");
    setResultsGenerated(Object.keys(savedResults).length > 0);
    setAnalysisError(run.error_message || "");
    setLightResults({});
    setLightAnalysisError("");
    unlockAndGoToStep("9");
  };

  const getStepValidation = () => {
    const dataQuality = supportFileSettings.masking || {};
    const customThresholdsValid =
      !dataQuality.customizeDataQualityThresholds ||
      (
        Number(dataQuality.minimumValidHoursPerDay) >= 1 &&
        Number(dataQuality.minimumValidHoursPerDay) <= 24 &&
        Number(dataQuality.minimumValidDaysForRhythm) >= 1 &&
        Number(dataQuality.minimumSleepWindowCoverage) >= 0 &&
        Number(dataQuality.minimumSleepWindowCoverage) <= 1
      );

    const hasMetrics =
      analysisMode === "standard"
        ? resolvedSelectedMetrics.length > 0
        : analysisScope === "family"
        ? selectedFamilies.length > 0
        : selectedMetrics.length > 0;

    switch (currentStep) {
      case "1": {
        const mappingValid = !showManualMapping || Boolean(csvMapping.timestamp_col && csvMapping.activity_col);
        return {
          valid: actigraphyFiles.length > 0 && mappingValid,
          message: !actigraphyFiles.length
            ? "Upload at least one actigraphy file."
            : !mappingValid
            ? "Select timestamp and activity columns for the manually mapped CSV."
            : "",
        };
      }
      case "2":
        return {
          valid: customThresholdsValid,
          message: customThresholdsValid
            ? ""
            : "Use 1–24 valid hours, at least 1 consecutive day, and sleep-window coverage between 0 and 1.",
        };
      case "3":
        return {
          valid: Boolean(activityMapping),
          message: activityMapping ? "" : "Choose an activity metric / acceleration-magnitude option.",
        };
      case "4":
        return {
          valid: true,
          message: previewLoaded
            ? ""
            : "Activity preview is optional, but it is needed for plot-based interval selection on later pages.",
        };
      case "5":
        return { valid: true, message: "" };
      case "6":
        return {
          valid: Boolean(selectedAlgorithm),
          message: selectedAlgorithm ? "" : "Choose a sleep/rest classification algorithm.",
        };
      case "7":
        return {
          valid: true,
          message: lightPreviewLoaded ? "" : "Light and other sensor processing is optional.",
        };
      case "8":
        return {
          valid: selectedAnalysisFileNames.length > 0 && hasMetrics,
          message: !selectedAnalysisFileNames.length
            ? "Select at least one uploaded file to analyze."
            : !hasMetrics
            ? "Choose at least one analysis family or metric."
            : "",
        };
      case "9":
        return {
          valid: resultsGenerated,
          message: resultsGenerated ? "" : "Generate results on this page to unlock Export Outputs.",
        };
      default:
        return { valid: true, message: "" };
    }
  };

  const stepValidation = getStepValidation();

  const goNext = () => {
    if (!stepValidation.valid) return;
    if (currentStepIndex < workflowSteps.length - 1) {
      const next = workflowSteps[currentStepIndex + 1];
      unlockAndGoToStep(next.id);
    }
  };

  const detectedInputType =
    previewData?.detected_input_type ||
    getExtension(actigraphyFile?.name || "").replace(".", "") ||
    "unknown";

  const metricsPanelProps = {
    metricRegistry,
    algorithmRegistry,
    analysisFamilyRegistry,
    sharedParamRegistry,
    selectedMetrics,
    setSelectedMetrics,
    selectedFamilies,
    setSelectedFamilies,
    analysisScope,
    setAnalysisScope,
    selectedAlgorithm,
    setSelectedAlgorithm,
    sharedValues,
    setSharedValues,
    metricOverrides,
    setMetricOverrides,
    algorithmParams,
    setAlgorithmParams,
    sleepWindowSettings,
    setSleepWindowSettings,
    analysisMode,
    inputType: detectedInputType,
    previewData,
    analysisWindowSettings,
    setAnalysisWindowSettings,
  };

  let content = null;

  if (currentStep === "1") {
    content = (
      <div style={{ display: "grid", gap: 16 }}>
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
        {showManualMapping && (
          <CsvMappingPanel
            title="Manual CSV Column Mapping"
            csvFile={actigraphyFile}
            csvMapping={csvMapping}
            setCsvMapping={setCsvMapping}
            csvSeparator={csvSeparator}
            setCsvSeparator={setCsvSeparator}
            onContinue={goNext}
          />
        )}
      </div>
    );
  } else if (currentStep === "2") {
    content = (
      <PreprocessingPanel
        title={appConfig.panels.preprocessing.title}
        settings={supportFileSettings.masking}
        onSettingsChange={(settings) =>
          setSupportFileSettings((previous) => ({ ...previous, masking: settings }))
        }
      />
    );
  } else if (currentStep === "3") {
    content = (
      <ActivityMappingPanel
        title={appConfig.panels.activityMapping.title}
        value={activityMapping}
        onChange={handleActivityMappingChange}
      />
    );
  } else if (currentStep === "4") {
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
        activityMapping={previewActivityMapping}
        setActivityMapping={handlePreviewActivityMappingChange}
        onPreview={onActivityPreview}
      />
    );
  } else if (currentStep === "5") {
    content = (
      <div style={{ display: "grid", gap: 16 }}>
        <SupportFilesStep
          title={appConfig.panels.startStop.title}
          type="startStop"
          description="Define the true effective recording interval for each file before masks and sleep windows are applied."
          files={uploadedFiles.startStop}
          onFilesChange={(files) => setUploadedFiles((previous) => ({ ...previous, startStop: files }))}
          settings={supportFileSettings.startStop}
          onSettingsChange={(settings) =>
            setSupportFileSettings((previous) => ({ ...previous, startStop: settings }))
          }
          options={[
            { id: "apply", label: "Apply uploaded or manually selected start/stop intervals", defaultValue: true },
          ]}
          previewData={previewData}
          previewDataByFile={activityPreviewByFile}
          actigraphyFiles={actigraphyFiles}
          onLoadPreviewForFile={loadActivityPreviewForFile}
        />
        <SupportFilesStep
          title={appConfig.panels.masking.title}
          type="masking"
          description="Upload exclusion intervals, respect detected non-wear, or select per-file masks directly on the activity plot."
          files={uploadedFiles.masking}
          onFilesChange={(files) => setUploadedFiles((previous) => ({ ...previous, masking: files }))}
          settings={supportFileSettings.masking}
          onSettingsChange={(settings) =>
            setSupportFileSettings((previous) => ({ ...previous, masking: settings }))
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
      </div>
    );
  } else if (currentStep === "6") {
    content = (
      <div style={{ display: "grid", gap: 16 }}>
        <SupportFilesStep
          title={appConfig.panels.sleepDiary.title}
          type="sleepDiary"
          description="Upload sleep diaries or create per-file bedtime/wake-time windows using timestamps or the activity plot."
          files={uploadedFiles.sleepDiary}
          onFilesChange={(files) => setUploadedFiles((previous) => ({ ...previous, sleepDiary: files }))}
          settings={supportFileSettings.sleepDiary}
          onSettingsChange={(settings) =>
            setSupportFileSettings((previous) => ({ ...previous, sleepDiary: settings }))
          }
          options={[
            { id: "apply", label: "Use uploaded or manually selected diary windows when available", defaultValue: true },
          ]}
          previewData={previewData}
          previewDataByFile={activityPreviewByFile}
          actigraphyFiles={actigraphyFiles}
          onLoadPreviewForFile={loadActivityPreviewForFile}
        />
        <MetricsPanel
          {...metricsPanelProps}
          title={appConfig.panels.sleepWake.title}
          mode="sleep"
        />
      </div>
    );
  } else if (currentStep === "7") {
    content = (
      <OtherSensorsPanel
        title={appConfig.panels.otherSensors.title}
        lightFiles={lightFiles}
        onLightFilesChange={(files) => {
          setUploadedFiles((previous) => ({ ...previous, light: files }));
          setSelectedLightPreviewFile(files?.[0]?.name || "");
          setLightPreviewLoaded(false);
          setLightPreviewData(null);
        }}
        temperatureFiles={uploadedFiles.temperature || []}
        onTemperatureFilesChange={(files) =>
          setUploadedFiles((previous) => ({ ...previous, temperature: files }))
        }
        previewProps={{
          title: appConfig.panels.lightPreview.title,
          mode: "light",
          previewLoaded: lightPreviewLoaded,
          previewLoading,
          previewError,
          previewData: lightPreviewData,
          actigraphyFiles,
          selectedPreviewFile,
          setSelectedPreviewFile,
          lightFiles,
          selectedLightPreviewFile,
          setSelectedLightPreviewFile,
          lightSourceAvailable: Boolean(lightFile),
          lightSourceMessage,
          onPreview: onLightPreview,
        }}
        lightFile={lightMetricFile}
        lightPreviewLoaded={lightPreviewLoaded}
        lightPreviewData={lightPreviewData}
        selectedLightMetrics={selectedLightMetrics}
        setSelectedLightMetrics={setSelectedLightMetrics}
        lightMetricSettings={lightMetricSettings}
        setLightMetricSettings={setLightMetricSettings}
        lightSourceMessage={lightSourceMessage}
        onLightInspection={(data) => {
          if (!lightFile || data?.light_detection?.available !== false) return;
          setLightPreviewData({ ...data, light_preview_file_name: lightFile.name });
          setLightPreviewLoaded(true);
        }}
      />
    );
  } else if (currentStep === "8") {
    content = (
      <MetricsPanel
        {...metricsPanelProps}
        title={appConfig.panels.metrics.title}
        mode="metrics"
      />
    );
  } else if (currentStep === "9") {
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
        dataQuality={dataQuality}
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
        dataQuality={dataQuality}
        lightResults={lightResults}
      />
    );
  }

  const canGoPrevious = currentStepIndex > 0;
  const canGoNext = currentStepIndex < workflowSteps.length - 1 && stepValidation.valid;

  return (
    <div
      className="app-center-aligned"
      style={{
        padding: 24,
        fontFamily: "Arial, sans-serif",
        background: "#f8fafc",
        minHeight: "100vh",
      }}
    >
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <div className="app-header-centered" style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
          <div style={{ width: "100%" }}>
            <h1 style={{ fontSize: 32, margin: "0 0 8px" }}>{appConfig.appName}</h1>
            <p style={{ color: "#475569", margin: 0, lineHeight: 1.5 }}>
              Guided 10-step actigraphy workflow covering preprocessing, activity estimation, cleaning, sleep-wake classification, other sensors, analysis, results, and export.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDocumentationOpen((value) => !value)}
            style={{ padding: "10px 14px", borderRadius: 12, background: documentationOpen ? "#0f172a" : "white", color: documentationOpen ? "white" : "#0f172a", border: "1px solid #cbd5e1", cursor: "pointer", fontWeight: 700 }}
          >
            {documentationOpen ? "Close Documentation" : "Documentation"}
          </button>
        </div>

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

        {documentationOpen ? (
          <DocumentationPanel onClose={() => setDocumentationOpen(false)} />
        ) : (
        <div
          className="workflow-centered"
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
                visitedSteps={visitedSteps}
                onStepClick={goToStep}
              />
            </div>
          )}

          <div className="workflow-page-centered" style={{ display: "grid", gap: 16 }}>
            {content}

            <div
              style={{
                display: "flex",
                justifyContent: "center",
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

              <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
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
                  {currentStep === "8" ? "Go to Generate Results" : currentStep === "9" ? "Go to Export Outputs" : "Next"}
                </button>
              </div>
            </div>
          </div>
        </div>
        )}
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
