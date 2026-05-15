import React, { useMemo, useState } from "react";
import {
  getAlgorithmDescription,
  getAlgorithmParameters,
  getAlgorithmReferences,
  getMetricCategories,
  getMetricSummary,
} from "../services/configUtils";
import { getSharedParamsForSelectedMetrics } from "../services/analysisConfigUtils";

const INPUT_TYPE_LABELS = {
  agd: "ActiGraph AGD",
  atr: "ActTrust ATR",
  awd: "Actiwatch AWD",
  bba: "BBA / accelerometer",
  csv: "CSV / mapped to Pandas",
  dqt: "Daqtometer",
  gt3x: "ActiGraph GT3X",
  mesa: "MESA",
  mtn: "MotionWatch MTN",
  rpx: "Respironics RPX",
  tal: "Tempatilumi TAL",
};

function normalizeMultiselectValue(value) {
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function cardStyle(selected, planned) {
  return {
    padding: 12,
    borderRadius: 14,
    border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
    background: selected ? "#0f172a" : "white",
    color: selected ? "white" : "#0f172a",
    cursor: planned ? "not-allowed" : "pointer",
    textAlign: "left",
    width: "100%",
    minHeight: 130,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    opacity: planned ? 0.7 : 1,
  };
}

export default function MetricsPanel({
  title,
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
  sharedValues = {},
  setSharedValues = () => {},
  metricOverrides = {},
  setMetricOverrides = () => {},
  analysisMode,
  inputType,
  algorithmParams = {},
  setAlgorithmParams = () => {},
  sleepWindowSettings = {},
  setSleepWindowSettings = () => {},
}) {
  const [expandedAlgorithm, setExpandedAlgorithm] = useState(null);
  const [expandedMetric, setExpandedMetric] = useState(null);
  const [expandedMetricGroup, setExpandedMetricGroup] = useState("rest_activity_group");

  const resolvedInputType = inputType || "csv";
  const detectedInputLabel = INPUT_TYPE_LABELS[resolvedInputType] || resolvedInputType;

  const allMetrics = useMemo(() => metricRegistry.metrics || [], [metricRegistry]);
  const allAlgorithms = useMemo(() => algorithmRegistry.algorithms || [], [algorithmRegistry]);
  const allFamilies = useMemo(() => analysisFamilyRegistry.families || [], [analysisFamilyRegistry]);

  const visibleCategories = useMemo(() => {
    const categories = getMetricCategories(metricRegistry);
    return categories.filter((category) =>
      allMetrics.some((metric) => metric.category === category.id)
    );
  }, [metricRegistry, allMetrics]);

  const metricGroups = useMemo(() => {
    const categoryById = Object.fromEntries(visibleCategories.map((category) => [category.id, category]));
    const restActivityCategories = new Set(["rest_activity", "fragmentation"]);
    const groups = [];

    const restActivityMetrics = allMetrics.filter((metric) => restActivityCategories.has(metric.category));
    if (restActivityMetrics.length > 0) {
      groups.push({
        id: "rest_activity_group",
        label: "Rest-Activity Metrics",
        description: "Rest-activity rhythm, non-parametric, and fragmentation metrics grouped together so users can select the whole group or expand it to choose individual metrics.",
        metrics: restActivityMetrics,
      });
    }

    visibleCategories
      .filter((category) => !restActivityCategories.has(category.id))
      .forEach((category) => {
        groups.push({
          id: category.id,
          label: category.label,
          description: category.description,
          metrics: allMetrics.filter((metric) => metric.category === category.id),
        });
      });

    return groups.filter((group) => group.metrics.length > 0);
  }, [visibleCategories, allMetrics]);

  const sharedParamsForSelection = useMemo(
    () =>
      getSharedParamsForSelectedMetrics(
        metricRegistry,
        sharedParamRegistry,
        selectedMetrics
      ),
    [metricRegistry, sharedParamRegistry, selectedMetrics]
  );

  const toggleMetric = (metricId) => {
    setSelectedMetrics((prev) =>
      prev.includes(metricId)
        ? prev.filter((item) => item !== metricId)
        : [...prev, metricId]
    );
  };


  const toggleMetricGroup = (metrics) => {
    const selectableIds = metrics
      .filter((metric) => !metric?.uiExposure?.planned)
      .map((metric) => metric.id);
    const allSelected = selectableIds.every((id) => selectedMetrics.includes(id));

    setSelectedMetrics((prev) => {
      if (allSelected) {
        return prev.filter((id) => !selectableIds.includes(id));
      }
      return Array.from(new Set([...prev, ...selectableIds]));
    });
  };

  const toggleFamily = (familyId, planned) => {
    if (planned) return;
    setSelectedFamilies((prev) =>
      prev.includes(familyId)
        ? prev.filter((item) => item !== familyId)
        : [...prev, familyId]
    );
  };

  const updateSharedValue = (sharedParamId, value) => {
    setSharedValues((prev) => ({
      ...prev,
      [sharedParamId]: value,
    }));
  };

  const updateMetricOverride = (metricId, paramName, value) => {
    setMetricOverrides((prev) => ({
      ...prev,
      [metricId]: {
        ...(prev[metricId] || {}),
        [paramName]: value,
      },
    }));
  };

  const updateAlgorithmParam = (algorithmId, name, value) => {
    setAlgorithmParams((prev) => ({
      ...prev,
      [algorithmId]: {
        ...(prev[algorithmId] || {}),
        [name]: value,
      },
    }));
  };

  const renderParamInput = (param, value, onChange) => {
    const current = value ?? param.default;

    if (param.type === "select") {
      return (
        <select
          value={current ?? ""}
          onChange={(e) => onChange(e.target.value)}
          style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
        >
          {(param.options || []).map((option) => {
            const optionValue = typeof option === "string" ? option : option.value;
            const optionLabel = typeof option === "string" ? option : option.label;
            return (
              <option key={optionValue} value={optionValue}>
                {optionLabel}
              </option>
            );
          })}
        </select>
      );
    }

    if (param.type === "multiselect") {
      const selectedValues = normalizeMultiselectValue(current);
      return (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(param.options || []).map((option) => {
            const optionValue = typeof option === "string" ? option : option.value;
            const optionLabel = typeof option === "string" ? option : option.label;
            const isSelected = selectedValues.includes(optionValue);

            return (
              <button
                key={optionValue}
                type="button"
                onClick={() => {
                  const next = isSelected
                    ? selectedValues.filter((item) => item !== optionValue)
                    : [...selectedValues, optionValue];
                  onChange(next);
                }}
                style={{
                  padding: "8px 12px",
                  borderRadius: 10,
                  border: isSelected ? "1px solid #0f172a" : "1px solid #cbd5e1",
                  background: isSelected ? "#0f172a" : "white",
                  color: isSelected ? "white" : "#0f172a",
                  cursor: "pointer",
                }}
              >
                {optionLabel}
              </button>
            );
          })}
        </div>
      );
    }

    if (param.type === "number_list") {
      const displayValue = Array.isArray(current) ? current.join(", ") : String(current ?? "");
      return (
        <input
          value={displayValue}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Comma-separated values"
          style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
        />
      );
    }

    if (param.type === "boolean") {
      return (
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
            background: "white",
          }}
        >
          <input
            type="checkbox"
            checked={Boolean(current)}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span>{param.label}</span>
        </label>
      );
    }

    if (param.type === "number" || param.type === "integer") {
      return (
        <input
          type="number"
          value={current ?? ""}
          min={param.min}
          max={param.max}
          step={param.step || 1}
          onChange={(e) =>
            onChange(e.target.value === "" ? "" : Number(e.target.value))
          }
          style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
        />
      );
    }

    return (
      <input
        type="text"
        value={current ?? ""}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", width: "100%" }}
      />
    );
  };

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
        Choose the sleep/rest algorithm first, then select either family-level analysis or metric-level analysis.
      </p>

      <div
        style={{
          border: "1px solid #dbeafe",
          borderRadius: 14,
          background: "#eff6ff",
          color: "#1e3a8a",
          padding: 14,
          marginBottom: 20,
          fontSize: 15,
          lineHeight: 1.5,
        }}
      >
        Detected input type: <strong>{detectedInputLabel}</strong>.
      </div>

      <div style={{ marginTop: 8, marginBottom: 24 }}>
        <div style={{ fontWeight: 700, marginBottom: 6 }}>Sleep / rest-detection algorithms</div>
        <div
          style={{
            border: "1px solid #e2e8f0",
            borderRadius: 14,
            overflow: "hidden",
            background: "#f8fafc",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.4fr 1fr 90px",
              background: "#e2e8f0",
              padding: "10px 12px",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            <div>Algorithm</div>
            <div>Context</div>
            <div>Select</div>
          </div>

          {allAlgorithms.map((algo, index) => {
            const isPlanned = Boolean(algo.uiExposure?.planned);

            return (
              <div
                key={algo.id}
                style={{
                  borderTop: index === 0 ? "none" : "1px solid #e2e8f0",
                  background: "white",
                  opacity: isPlanned ? 0.86 : 1,
                }}
              >
                <label
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1.4fr 1fr 90px",
                    padding: "12px",
                    alignItems: "center",
                    fontSize: 14,
                    cursor: "pointer",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{algo.label}</div>
                    <div style={{ fontSize: 14, color: "#64748b", marginTop: 2 }}>
                      {getAlgorithmDescription(algorithmRegistry, algo.id)}
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        setExpandedAlgorithm(expandedAlgorithm === algo.id ? null : algo.id);
                      }}
                      style={{
                        marginTop: 6,
                        padding: 0,
                        border: "none",
                        background: "transparent",
                        color: "#2563eb",
                        fontSize: 14,
                        cursor: "pointer",
                      }}
                    >
                      {expandedAlgorithm === algo.id ? "Hide details" : "Show details"}
                    </button>
                  </div>

                  <div style={{ color: "#475569", lineHeight: 1.5 }}>{algo.context}</div>

                  <div>
                    <input
                      type="radio"
                      name="sleepAlgorithm"
                      checked={selectedAlgorithm === algo.id}
                      onChange={() => setSelectedAlgorithm(algo.id)}
                    />
                  </div>
                </label>

                {expandedAlgorithm === algo.id && (
                  <div
                    style={{
                      padding: "0 12px 12px 12px",
                      color: "#475569",
                      fontSize: 14,
                      lineHeight: 1.6,
                    }}
                  >
                    <div style={{ marginBottom: 8 }}>{algo.note}</div>

                    {(algo.warnings || []).length > 0 && (
                      <div style={{ marginBottom: 8, color: "#9a3412" }}>
                        <strong>Warnings:</strong> {algo.warnings.join(" ")}
                      </div>
                    )}

                    {getAlgorithmReferences(algorithmRegistry, algo.id).length > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <strong>Citation:</strong>{" "}
                        {getAlgorithmReferences(algorithmRegistry, algo.id).join("; ")}
                      </div>
                    )}

                    {(getAlgorithmParameters(algorithmRegistry, algo.id) || []).length > 0 && (
                      <div style={{ display: "grid", gap: 10 }}>
                        {(getAlgorithmParameters(algorithmRegistry, algo.id) || []).map((param) => (
                          <div key={`${algo.id}-${param.name}`}>
                            <div style={{ fontWeight: 600, marginBottom: 6 }}>{param.label}</div>
                            {renderParamInput(
                              param,
                              algorithmParams?.[algo.id]?.[param.name],
                              (value) => updateAlgorithmParam(algo.id, param.name, value)
                            )}
                            {param.description && (
                              <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
                                {param.description}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div
        style={{
          border: "1px solid #dcfce7",
          borderRadius: 14,
          background: "#f0fdf4",
          color: "#14532d",
          padding: 14,
          marginBottom: 24,
          fontSize: 14,
          lineHeight: 1.55,
        }}
      >
        <div style={{ fontWeight: 800, marginBottom: 8 }}>Sleep window source for TST, WASO, and sleep efficiency</div>
        <div style={{ marginBottom: 10 }}>
          <strong>Crespo_AoT</strong> estimates activity offset/onset periods from the activity-rest pattern and is a good default for detecting the main rest window.
          <strong> Roenneberg_AoT</strong> is an alternative automatic sleep/rest detector based on consolidated rest periods and threshold/trend-style detection.
          Start with <strong>3–14 hours</strong> to avoid missing unusual sleep windows; for typical adult overnight sleep, <strong>4–12 hours</strong> is usually a tighter practical range.
        </div>
        <label style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={sleepWindowSettings?.estimateWithoutDiary !== false}
            onChange={(e) =>
              setSleepWindowSettings((prev) => ({ ...prev, estimateWithoutDiary: e.target.checked }))
            }
            style={{ marginTop: 3 }}
          />
          <span>
            If no sleep diary is uploaded, estimate the sleep/rest window using pyActigraphy activity onset/offset detection.
            Results will be labelled as estimated.
          </span>
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Detection method</div>
            <select
              value={sleepWindowSettings?.method || "crespo_aot"}
              onChange={(e) => setSleepWindowSettings((prev) => ({ ...prev, method: e.target.value }))}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #86efac" }}
            >
              <option value="crespo_aot">pyActigraphy Crespo_AoT</option>
              <option value="roenneberg_aot">pyActigraphy Roenneberg_AoT</option>
            </select>
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Min rest window (h)</div>
            <input
              type="number"
              min="1"
              step="0.5"
              value={sleepWindowSettings?.minRestWindowHours ?? 3}
              onChange={(e) => setSleepWindowSettings((prev) => ({ ...prev, minRestWindowHours: Number(e.target.value) }))}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #86efac" }}
            />
          </label>
          <label>
            <div style={{ fontWeight: 600, marginBottom: 5 }}>Max rest window (h)</div>
            <input
              type="number"
              min="2"
              step="0.5"
              value={sleepWindowSettings?.maxRestWindowHours ?? 14}
              onChange={(e) => setSleepWindowSettings((prev) => ({ ...prev, maxRestWindowHours: Number(e.target.value) }))}
              style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1px solid #86efac" }}
            />
          </label>
        </div>
      </div>

      {analysisMode !== "standard" && (
        <div
          style={{
            border: "1px solid #e2e8f0",
            borderRadius: 16,
            padding: 16,
            background: "#f8fafc",
            marginBottom: 24,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Analysis scope</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {[
              { id: "family", label: "Family-level analysis" },
              { id: "metric", label: "Metric-level analysis" },
            ].map((option) => {
              const selected = analysisScope === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setAnalysisScope(option.id)}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 12,
                    border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
                    background: selected ? "#0f172a" : "white",
                    color: selected ? "white" : "#0f172a",
                    cursor: "pointer",
                  }}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {analysisScope === "family" && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Analysis families</div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: 12,
            }}
          >
            {allFamilies.map((family) => {
              const selected = selectedFamilies.includes(family.id);
              return (
                <button
                  key={family.id}
                  type="button"
                  onClick={() => toggleFamily(family.id, family.planned)}
                  style={cardStyle(selected, family.planned)}
                >
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 17 }}>{family.label}</div>
                    <div
                      style={{
                        marginTop: 8,
                        color: selected ? "rgba(255,255,255,0.9)" : "#475569",
                        fontSize: 14,
                        lineHeight: 1.45,
                      }}
                    >
                      {family.description}
                    </div>
                  </div>
                  {family.planned && (
                    <div style={{ fontSize: 13, fontWeight: 700 }}>Planned</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {analysisScope === "metric" &&
        metricGroups.map((group) => {
          const selectableMetrics = group.metrics.filter((metric) => !metric?.uiExposure?.planned);
          const selectedCount = selectableMetrics.filter((metric) => selectedMetrics.includes(metric.id)).length;
          const allSelected = selectableMetrics.length > 0 && selectedCount === selectableMetrics.length;
          const isExpanded = expandedMetricGroup === group.id;

          return (
            <div
              key={group.id}
              style={{
                marginBottom: 16,
                border: "1px solid #e2e8f0",
                borderRadius: 16,
                overflow: "hidden",
                background: "#f8fafc",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto auto",
                  gap: 10,
                  alignItems: "center",
                  padding: 14,
                  background: "white",
                  borderBottom: isExpanded ? "1px solid #e2e8f0" : "none",
                }}
              >
                <button
                  type="button"
                  onClick={() => setExpandedMetricGroup(isExpanded ? null : group.id)}
                  style={{
                    padding: 0,
                    border: "none",
                    background: "transparent",
                    textAlign: "left",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 800, fontSize: 17 }}>
                    {isExpanded ? "▾" : "▸"} {group.label}
                  </div>
                  <div style={{ color: "#64748b", fontSize: 14, marginTop: 4, lineHeight: 1.45 }}>
                    {group.description}
                  </div>
                </button>

                <div style={{ color: "#475569", fontSize: 14 }}>
                  {selectedCount}/{selectableMetrics.length} selected
                </div>

                <button
                  type="button"
                  onClick={() => toggleMetricGroup(group.metrics)}
                  disabled={selectableMetrics.length === 0}
                  style={{
                    padding: "9px 12px",
                    borderRadius: 10,
                    border: allSelected ? "1px solid #0f172a" : "1px solid #cbd5e1",
                    background: allSelected ? "#0f172a" : "white",
                    color: allSelected ? "white" : "#0f172a",
                    cursor: selectableMetrics.length === 0 ? "not-allowed" : "pointer",
                    fontWeight: 700,
                  }}
                >
                  {allSelected ? "Clear group" : "Select group"}
                </button>
              </div>

              {isExpanded && (
                <div style={{ padding: 14 }}>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                      gap: 12,
                    }}
                  >
                    {group.metrics.map((metric) => {
                      const isSelected = selectedMetrics.includes(metric.id);
                      const isPlanned = Boolean(metric?.uiExposure?.planned);

                      return (
                        <div key={metric.id}>
                          <button
                            type="button"
                            onClick={() => !isPlanned && toggleMetric(metric.id)}
                            style={cardStyle(isSelected, isPlanned)}
                          >
                            <div>
                              <div style={{ fontWeight: 1000, fontSize: 17 }}>{metric.label}</div>
                              <div
                                style={{
                                  marginTop: 8,
                                  fontSize: 15,
                                  lineHeight: 1.45,
                                  color: isSelected ? "rgba(255,255,255,0.92)" : "#475569",
                                  minHeight: 38,
                                }}
                              >
                                {getMetricSummary(metricRegistry, metric.id)}
                              </div>
                            </div>

                            <div style={{ marginTop: 10 }}>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedMetric(expandedMetric === metric.id ? null : metric.id);
                                }}
                                style={{
                                  padding: 0,
                                  border: "none",
                                  background: "transparent",
                                  color: isSelected ? "white" : "#2563eb",
                                  cursor: "pointer",
                                  fontSize: 15,
                                }}
                              >
                                {expandedMetric === metric.id ? "Hide details" : "Show details"}
                              </button>

                              {expandedMetric === metric.id && (
                                <div style={{ marginTop: 10, fontSize: 15, lineHeight: 1.55 }}>
                                  <div style={{ marginBottom: 6 }}>{metric.description}</div>
                                  {(metric.references || []).length > 0 && (
                                    <div>
                                      <strong>References:</strong> {metric.references.join("; ")}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}

      {analysisScope === "metric" && analysisMode !== "standard" && sharedParamsForSelection.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Common metric settings</div>
          <div style={{ display: "grid", gap: 12 }}>
            {sharedParamsForSelection.map((param) => (
              <div key={param.id}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{param.label}</div>
                {renderParamInput(
                  param,
                  sharedValues?.[param.id],
                  (value) => updateSharedValue(param.id, value)
                )}
                {param.description && (
                  <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
                    {param.description}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {analysisScope === "metric" && analysisMode !== "standard" && selectedMetrics.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Metric-specific overrides</div>
          <div style={{ display: "grid", gap: 14 }}>
            {selectedMetrics.map((metricId) => {
              const metric = allMetrics.find((m) => m.id === metricId);
              if (!metric) return null;

              const params = metric.parameterSchema || [];
              if (params.length === 0) return null;

              return (
                <div
                  key={`override-${metricId}`}
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: 14,
                    padding: 14,
                    background: "#f8fafc",
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: 10 }}>{metric.label}</div>

                  <div style={{ display: "grid", gap: 10 }}>
                    {params.map((param) => (
                      <div key={`${metricId}-${param.name}`}>
                        <div style={{ fontWeight: 600, marginBottom: 6 }}>{param.label}</div>
                        {renderParamInput(
                          param,
                          metricOverrides?.[metricId]?.[param.name],
                          (value) => updateMetricOverride(metricId, param.name, value)
                        )}
                        {param.sharedParamId && (
                          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                            Leave blank to inherit the common setting.
                          </div>
                        )}
                        {param.description && (
                          <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
                            {param.description}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}