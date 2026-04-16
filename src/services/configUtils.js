export function getDefaultSelectedMetrics(metricRegistry) {
  return (metricRegistry.metrics || [])
    .filter((metric) => metric.defaultSelected)
    .map((metric) => metric.id);
}

export function getDefaultAlgorithm(algorithmRegistry) {
  const found = (algorithmRegistry.algorithms || []).find((algo) => algo.default);
  return found ? found.id : null;
}

export function getMetricDefinition(metricRegistry, metricId) {
  return (metricRegistry.metrics || []).find((m) => m.id === metricId) || null;
}

export function getMetricLabel(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.label : metricId;
}

export function getMetricShortLabel(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.shortLabel || found.label : metricId;
}

export function getMetricSummary(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.summary || "" : "";
}

export function getMetricDescription(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.description || "" : "";
}

export function getMetricParameters(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.parameterSchema || [] : [];
}

export function getMetricResultSchema(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.resultSchema || null : null;
}

export function getMetricReferences(metricRegistry, metricId) {
  const found = getMetricDefinition(metricRegistry, metricId);
  return found ? found.references || [] : [];
}

export function requiresSleepScoring(selectedMetrics, metricRegistry) {
  return selectedMetrics.some((metricId) => {
    const metric = getMetricDefinition(metricRegistry, metricId);
    return metric?.requiresSleepScoring;
  });
}

export function requiresDiary(selectedMetrics, metricRegistry) {
  return selectedMetrics.some((metricId) => {
    const metric = getMetricDefinition(metricRegistry, metricId);
    return metric?.requiresDiary;
  });
}

export function getMetricsByCategory(metricRegistry, category) {
  return (metricRegistry.metrics || []).filter((metric) => metric.category === category);
}

export function getMetricCategories(metricRegistry) {
  return metricRegistry.categories || [];
}

export function getVisibleMetrics(metricRegistry, { includeAdvanced = true, includePlanned = true } = {}) {
  return (metricRegistry.metrics || []).filter((metric) => {
    const ui = metric.uiExposure || {};
    if (ui.showInMetricPicker === false) return false;
    if (!includeAdvanced && ui.advanced) return false;
    if (!includePlanned && ui.planned) return false;
    return true;
  });
}

export function getSupportedMetricsForInput(metricRegistry, inputType, options = {}) {
  return getVisibleMetrics(metricRegistry, options).filter((metric) =>
    (metric.supportedInputTypes || []).includes(inputType)
  );
}

export function getAlgorithmDefinition(algorithmRegistry, algorithmId) {
  return (algorithmRegistry.algorithms || []).find((algo) => algo.id === algorithmId) || null;
}

export function getAlgorithmLabel(algorithmRegistry, algorithmId) {
  const found = getAlgorithmDefinition(algorithmRegistry, algorithmId);
  return found ? found.label : algorithmId;
}

export function getAlgorithmSummary(algorithmRegistry, algorithmId) {
  const found = getAlgorithmDefinition(algorithmRegistry, algorithmId);
  return found ? found.summary || "" : "";
}

export function getAlgorithmDescription(algorithmRegistry, algorithmId) {
  const found = getAlgorithmDefinition(algorithmRegistry, algorithmId);
  return found ? found.description || "" : "";
}

export function getAlgorithmParameters(algorithmRegistry, algorithmId) {
  const found = getAlgorithmDefinition(algorithmRegistry, algorithmId);
  return found ? found.parameterSchema || [] : [];
}

export function getAlgorithmReferences(algorithmRegistry, algorithmId) {
  const found = getAlgorithmDefinition(algorithmRegistry, algorithmId);
  return found ? [found.citationText].filter(Boolean) : [];
}

export function getAvailableAlgorithms(selectedMetrics, algorithmRegistry) {
  if (!selectedMetrics || selectedMetrics.length === 0) {
    return [];
  }

  return (algorithmRegistry.algorithms || []).filter((algo) =>
    selectedMetrics.some((metricId) => (algo.supportedMetrics || []).includes(metricId))
  );
}

export function getSupportedAlgorithmsForInput(algorithmRegistry, inputType, { includeAdvanced = true, includePlanned = true } = {}) {
  return (algorithmRegistry.algorithms || []).filter((algo) => {
    const ui = algo.uiExposure || {};
    if (ui.showInSelector === false) return false;
    if (!includeAdvanced && ui.advanced) return false;
    if (!includePlanned && ui.planned) return false;
    return (algo.supportedInputTypes || []).includes(inputType);
  });
}

export function getAlgorithmsForMetric(metricId, algorithmRegistry) {
  return (algorithmRegistry.algorithms || []).filter((algo) =>
    (algo.supportedMetrics || []).includes(metricId)
  );
}

export function getMetricsRequiringAlgorithms(selectedMetrics, metricRegistry) {
  return (selectedMetrics || []).filter((metricId) => {
    const metric = getMetricDefinition(metricRegistry, metricId);
    return metric?.requiresSleepScoring;
  });
}

export function getVisibleWorkflowSteps(appConfig, { enableCleaning = true, enableDiary = true } = {}) {
  return (appConfig.workflow || []).filter((step) => {
    if (!enableCleaning && step.key === "cleaning") return false;
    if (!enableDiary && step.key === "diaryAndLogs") return false;
    return true;
  });
}