export function makeSafeFilename(name) {
  return String(name || "actigraphy-export")
    .replace(/[^a-z0-9_\-.]+/gi, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 120);
}

export function downloadBlob(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function downloadJson(data, filename = "actigraphy-results.json") {
  downloadBlob(JSON.stringify(data ?? {}, null, 2), makeSafeFilename(filename), "application/json;charset=utf-8");
}

function escapeCsvValue(value) {
  if (value == null) return "";
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function rowsToCsv(rows, columns) {
  const cols = columns || Array.from(rows.reduce((set, row) => {
    Object.keys(row || {}).forEach((key) => set.add(key));
    return set;
  }, new Set()));
  return [cols.join(","), ...rows.map((row) => cols.map((col) => escapeCsvValue(row?.[col])).join(","))].join("\n");
}

export function resultPayloadToRows(payload) {
  if (!payload) return [];
  if (payload.kind === "scalar") return [{ value: payload.value }];
  if (payload.kind === "series") {
    return (payload.index || []).map((index, idx) => ({ index, value: payload.values?.[idx] }));
  }
  if (payload.kind === "dataframe") {
    return (payload.rows || []).map((row) => {
      const out = { index: row.index };
      (payload.columns || []).forEach((col, idx) => {
        out[col] = row.values?.[idx];
      });
      return out;
    });
  }
  return [];
}

export function summaryResultsToRows(summaryResults = {}, labelResolver = (key) => key) {
  return Object.entries(summaryResults).map(([metric, value]) => ({
    metric,
    label: labelResolver(metric),
    value: typeof value === "object" ? JSON.stringify(value) : value,
  }));
}

export function previewToRows(previewData, mode = "activity") {
  const points = mode === "light"
    ? previewData?.light_preview || []
    : previewData?.full_recording_preview || [];
  return points.map((point) => ({ ...point }));
}
