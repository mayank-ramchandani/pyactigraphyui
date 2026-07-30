export function fileSelectionKey(file, index = 0) {
  if (!file) return "";
  const name = encodeURIComponent(file.name || "unnamed");
  const size = Number(file.size || 0);
  const modified = Number(file.lastModified || 0);
  return `upload-${index}-${name}-${size}-${modified}`;
}

export function buildFileEntries(files = []) {
  const nameTotals = files.reduce((counts, file) => {
    const name = file?.name || "Unnamed file";
    counts[name] = (counts[name] || 0) + 1;
    return counts;
  }, {});
  const seen = {};

  return files.map((file, index) => {
    const name = file?.name || "Unnamed file";
    seen[name] = (seen[name] || 0) + 1;
    return {
      file,
      index,
      key: fileSelectionKey(file, index),
      duplicateIndex: seen[name],
      duplicateCount: nameTotals[name] || 1,
    };
  });
}

export function resolveFileSelection(files = [], selection = "") {
  const entries = buildFileEntries(files);
  if (!entries.length) return null;
  return (
    entries.find((entry) => entry.key === selection) ||
    entries.find((entry) => entry.file?.name === selection) ||
    entries[0]
  );
}

export function formatFileSize(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const order = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const scaled = value / (1024 ** order);
  return `${scaled >= 10 || order === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[order]}`;
}

export function fileEntryLabel(entry) {
  if (!entry) return "";
  if (entry.duplicateCount <= 1) return entry.file?.name || "Unnamed file";
  return `${entry.file?.name || "Unnamed file"} — duplicate ${entry.duplicateIndex} of ${entry.duplicateCount}`;
}

export function searchFileEntries(entries = [], query = "") {
  const normalized = String(query || "").trim().toLowerCase();
  if (!normalized) return entries;
  const tokens = normalized.split(/\s+/).filter(Boolean);

  return entries
    .map((entry) => {
      const file = entry.file || {};
      const name = String(file.name || "").toLowerCase();
      const extension = name.includes(".") ? name.split(".").pop() : "";
      const metadata = `${name} ${extension} ${formatFileSize(file.size).toLowerCase()} ${entry.duplicateIndex} ${entry.duplicateCount}`;
      if (!tokens.every((token) => metadata.includes(token))) return null;
      let score = 0;
      if (name === normalized) score += 100;
      if (name.startsWith(normalized)) score += 50;
      if (name.includes(normalized)) score += 25;
      return { entry, score };
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score || a.entry.index - b.entry.index)
    .map(({ entry }) => entry);
}
