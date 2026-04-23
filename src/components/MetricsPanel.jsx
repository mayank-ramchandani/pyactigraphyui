import React, { useMemo, useState } from "react";
import {
  getAlgorithmDescription,
  getAlgorithmParameters,
  getAlgorithmReferences,
  getMetricCategories,
  getMetricSummary,
} from "../services/configUtils";
import {
  getSharedParamsForSelectedMetrics,
} from "../services/analysisConfigUtils";

const INPUT_TYPE_LABELS = {
  agd: "ActiGraph AGD",
  atr: "ActTrust ATR",
  awd: "Actiwatch AWD",
  bba: "BBA / accelerometer",
  csv: "CSV",
  dqt: "Daqtometer",
  mesa: "MESA",
  mtn: "MotionWatch MTN",
  rpx: "Respironics RPX",
  tal: "Tempatilumi TAL",
};

function normalizeMultiselectValue(value) {
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
}

function metricCardStyle(selected, planned) {
  return {
    padding: 12,
    borderRadius: 14,
    border: selected ? "1px solid #0f172a" : "1px solid #cbd5e1",
    background: selected ? "#0f172a" : "white",
    color: selected ? "white" : "#0f172a",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
    minHeight: 148,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    opacity: planned ? 0.86 : 1,
  };
}

export default function MetricsPanel({
  title,
  metricRegistry,
  algorithmRegistry,
  sharedParamRegistry,
  selectedMetrics,
  setSelectedMetrics,
  selectedAlgorithm,
  setSelectedAlgorithm,
  setCurrentStep,
  activityChannel,
  setActivityChannel,
  activityTransform,
  setActivityTransform,
  lightTransform,
  setLightTransform,
  sharedValues = {},
  setSharedValues = () => {},
  metricOverrides = {},
  setMetricOverrides = () => {},
  analysisMode,
  inputType,
  algorithmParams = {},
  setAlgorithmParams = () => {},
}) {
  const [expandedAlgorithm, setExpandedAlgorithm] = useState(null);
  const [expandedMetric, setExpandedMetric] = useState(null);

  const resolvedInputType = inputType || "csv";
  const detectedInputLabel = INPUT_TYPE_LABELS[resolvedInputType] || resolvedInputType;

  const allMetrics = useMemo(() => metricRegistry.metrics || [], [metricRegistry]);
  const allAlgorithms = useMemo(() => algorithmRegistry.algorithms || [], [algorithmRegistry]);

  const visibleCategories = useMemo(() => {
    const categories = getMetricCategories(metricRegistry);
    return categories.filter((category) =>
      allMetrics.some((metric) => metric.category === category.id)
    );
  }, [metricRegistry, allMetrics]);

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
    setCurrentStep("5");
    setSelectedMetrics((prev) =>
      prev.includes(metricId)
        ? prev.filter((item) => item !== metricId)
        : [...prev, metricId]
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
            const optionValue =
              typeof option === "string" ? option : option.value;
            const optionLabel =
              typeof option === "string" ? option : option.label;

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
            const optionValue =
              typeof option === "string" ? option : option.value;
            const optionLabel =
              typeof option === "string" ? option : option.label;
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
        placeholder={param.placeholder || ""}
        style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", width: "100%" }}
      />
    );
  };

  const renderAlgorithmParameter = (algorithm, param) => {
    const current = algorithmParams?.[algorithm.id]?.[param.name] ?? param.default;
    return renderParamInput(param, current, (value) =>
      updateAlgorithmParam(algorithm.id, param.name, value)
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
        Select pyActigraphy-backed metrics and algorithms.
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

      {visibleCategories.map((category) => {
        const categoryMetrics = allMetrics.filter((metric) => metric.category === category.id);
        if (categoryMetrics.length === 0) return null;

        return (
          <div key={category.id} style={{ marginBottom: 24 }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>{category.label}</div>
            <div style={{ color: "#64748b", fontSize: 16, marginBottom: 12 }}>
              {category.description}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 12,
              }}
            >
              {categoryMetrics.map((metric) => {
                const isSelected = selectedMetrics.includes(metric.id);
                const isPlanned = Boolean(metric?.uiExposure?.planned);

                return (
                  <div key={metric.id}>
                    <button
                      type="button"
                      onClick={() => toggleMetric(metric.id)}
                      style={metricCardStyle(isSelected, isPlanned)}
                    >
                      <div>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            gap: 8,
                            alignItems: "flex-start",
                            marginBottom: 8,
                          }}
                        >
                          <div
                            style={{
                              fontWeight: 1000,
                              fontSize: 17,
                              lineHeight: 1.3,
                              minHeight: 40,
                              display: "flex",
                              alignItems: "flex-start",
                            }}
                          >
                            {metric.label}
                          </div>

                          {isPlanned && (
                            <span
                              style={{
                                fontSize: 15,
                                padding: "2px 8px",
                                borderRadius: 999,
                                background: isSelected ? "rgba(255,255,255,0.2)" : "#e2e8f0",
                                color: isSelected ? "white" : "#334155",
                                whiteSpace: "nowrap",
                              }}
                            >
                              Planned
                            </span>
                          )}
                        </div>

                        <div
                          style={{
                            fontSize: 15,
                            lineHeight: 1.45,
                            color: isSelected ? "rgba(255,255,255,0.92)" : "#475569",
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
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
                          <div
                            style={{
                              marginTop: 10,
                              fontSize: 15,
                              lineHeight: 1.55,
                              opacity: 0.95,
                            }}
                          >
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
        );
      })}

      {analysisMode !== "standard" && (
        <>
          <div style={{ marginTop: 24 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Shared preprocessing</div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 12,
              }}
            >
              <select
                value={activityChannel}
                onChange={(e) => setActivityChannel(e.target.value)}
                style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
              >
                <option value="VM">Vector Magnitude (VM)</option>
                <option value="activity_counts">Activity Counts</option>
                <option value="ENMO">ENMO</option>
                <option value="MAD">MAD</option>
                <option value="PIM">PIM</option>
                <option value="TAT">TAT</option>
                <option value="ZCM">ZCM</option>
              </select>

              <select
                value={activityTransform}
                onChange={(e) => setActivityTransform(e.target.value)}
                style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
              >
                <option value="none">No activity transform</option>
                <option value="zscore">Z-score activity</option>
              </select>

              <select
                value={lightTransform}
                onChange={(e) => setLightTransform(e.target.value)}
                style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1" }}
              >
                <option value="none">No light transform</option>
                <option value="log">Log-transform light</option>
              </select>
            </div>
          </div>

          {sharedParamsForSelection.length > 0 && (
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

          {selectedMetrics.length > 0 && (
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
        </>
      )}

      <div style={{ marginTop: 24 }}>
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
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: 16,
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                        justifyContent: "center",
                        flexWrap: "wrap",
                        textAlign: "center",
                        width: "100%",
                      }}
                    >
                      <span>{algo.label}</span>

                      {isPlanned && (
                        <span
                          style={{
                            fontSize: 14,
                            fontWeight: 700,
                            padding: "4px 8px",
                            borderRadius: 999,
                            background: "#e2e8f0",
                            color: "#334155",
                          }}
                        >
                          Planned
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: 14, color: "#64748b", marginTop: 1 }}>
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
                      onChange={() => {
                        setSelectedAlgorithm(algo.id);
                        setCurrentStep("5");
                      }}
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
                            {renderAlgorithmParameter(algo, param)}
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
    </div>
  );
}