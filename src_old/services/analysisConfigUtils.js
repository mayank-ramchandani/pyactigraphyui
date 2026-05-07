import {
    getMetricDefinition,
    getAlgorithmDefinition,
  } from "./configUtils";
  
  export function getSharedParamDefinition(sharedRegistry, sharedParamId) {
    return (sharedRegistry?.sharedParams || []).find((p) => p.id === sharedParamId) || null;
  }
  
  export function getMetricParameters(metricRegistry, metricId) {
    return getMetricDefinition(metricRegistry, metricId)?.parameterSchema || [];
  }
  
  export function getAlgorithmParametersFromRegistry(algorithmRegistry, algorithmId) {
    return getAlgorithmDefinition(algorithmRegistry, algorithmId)?.parameterSchema || [];
  }
  
  export function getSharedParamUsage(metricRegistry, selectedMetrics) {
    const usage = {};
  
    for (const metricId of selectedMetrics || []) {
      const params = getMetricParameters(metricRegistry, metricId);
      for (const param of params) {
        if (!param.sharedParamId) continue;
        if (!usage[param.sharedParamId]) {
          usage[param.sharedParamId] = [];
        }
        usage[param.sharedParamId].push({
          metricId,
          paramName: param.name,
          backendArgName: param.backendArgName || param.name,
        });
      }
    }
  
    return usage;
  }
  
  export function getSharedParamsForSelectedMetrics(metricRegistry, sharedRegistry, selectedMetrics) {
    const usage = getSharedParamUsage(metricRegistry, selectedMetrics);
  
    return Object.keys(usage)
      .filter((sharedParamId) => usage[sharedParamId].length >= 2)
      .map((sharedParamId) => ({
        ...getSharedParamDefinition(sharedRegistry, sharedParamId),
        usage: usage[sharedParamId],
      }))
      .filter(Boolean);
  }
  
  export function getMetricLocalParams(metricRegistry, metricId) {
    const params = getMetricParameters(metricRegistry, metricId);
    return params.filter((param) => !param.sharedParamId);
  }
  
  export function getMetricOverrideValue(metricOverrides, metricId, paramName) {
    return metricOverrides?.[metricId]?.[paramName];
  }
  
  export function resolveMetricParams(metricRegistry, sharedRegistry, metricId, sharedValues, metricOverrides) {
    const metric = getMetricDefinition(metricRegistry, metricId);
    if (!metric) return {};
  
    const params = metric.parameterSchema || [];
    const overrides = metricOverrides?.[metricId] || {};
    const resolved = {};
  
    for (const param of params) {
      const backendArgName = param.backendArgName || param.name;
  
      if (overrides[param.name] !== undefined) {
        resolved[backendArgName] = overrides[param.name];
        continue;
      }
  
      if (param.sharedParamId) {
        if (sharedValues?.[param.sharedParamId] !== undefined) {
          resolved[backendArgName] = sharedValues[param.sharedParamId];
          continue;
        }
  
        const sharedDef = getSharedParamDefinition(sharedRegistry, param.sharedParamId);
        if (sharedDef && sharedDef.default !== undefined) {
          resolved[backendArgName] = sharedDef.default;
          continue;
        }
      }
  
      if (param.default !== undefined) {
        resolved[backendArgName] = param.default;
      }
    }
  
    return resolved;
  }
  
  export function resolveAlgorithmParams(algorithmRegistry, algorithmId, algorithmParams) {
    const algorithm = getAlgorithmDefinition(algorithmRegistry, algorithmId);
    if (!algorithm) return {};
  
    const paramDefs = algorithm.parameterSchema || [];
    const storedParams = algorithmParams?.[algorithmId] || {};
    const resolved = {};
  
    for (const param of paramDefs) {
      const backendArgName = param.backendArgName || param.name;
      if (storedParams[param.name] !== undefined) {
        resolved[backendArgName] = storedParams[param.name];
      } else if (param.default !== undefined) {
        resolved[backendArgName] = param.default;
      }
    }
  
    return resolved;
  }
  
  export function buildAnalysisPayload({
    metricRegistry,
    sharedRegistry,
    algorithmRegistry,
    selectedMetrics,
    selectedAlgorithm,
    sharedValues,
    metricOverrides,
    algorithmParams,
  }) {
    return {
      metrics: (selectedMetrics || []).map((metricId) => ({
        id: metricId,
        params: resolveMetricParams(
          metricRegistry,
          sharedRegistry,
          metricId,
          sharedValues,
          metricOverrides
        ),
      })),
      algorithm: selectedAlgorithm
        ? {
            id: selectedAlgorithm,
            params: resolveAlgorithmParams(algorithmRegistry, selectedAlgorithm, algorithmParams),
          }
        : null,
    };
  }