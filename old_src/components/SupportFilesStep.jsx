import React, { useState } from "react";

const supportFileExtensions = ".csv,.ods,.xls,.xlsx,.txt";

export default function SupportFilesStep({
  title,
  description,
  files,
  onFilesChange,
  options = [],
}) {
  const [localOptions, setLocalOptions] = useState(
    Object.fromEntries(options.map((opt) => [opt.id, opt.defaultValue ?? false]))
  );

  return (
    <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 20, padding: 20 }}>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      <p style={{ color: "#64748b", lineHeight: 1.6 }}>{description}</p>

      <label
        style={{
          display: "block",
          border: "2px dashed #cbd5e1",
          borderRadius: 16,
          padding: 20,
          background: "#f8fafc",
          cursor: "pointer",
          marginTop: 12,
        }}
      >
        <div style={{ fontWeight: 700 }}>Upload supporting files</div>
        <div style={{ fontSize: 13, color: "#64748b", marginTop: 6 }}>
          {files?.length ? `${files.length} file(s) selected` : "No files selected"}
        </div>

        <input
          type="file"
          multiple
          accept={supportFileExtensions}
          style={{ display: "none" }}
          onChange={(e) => onFilesChange(Array.from(e.target.files || []))}
        />

        <div
          style={{
            marginTop: 12,
            display: "inline-block",
            padding: "8px 12px",
            borderRadius: 10,
            border: "1px solid #cbd5e1",
            background: "white",
          }}
        >
          Choose Files
        </div>
      </label>

      {options.length > 0 && (
        <div
          style={{
            marginTop: 16,
            border: "1px solid #e2e8f0",
            borderRadius: 16,
            padding: 16,
            background: "#f8fafc",
            display: "grid",
            gap: 10,
          }}
        >
          <div style={{ fontWeight: 700 }}>Options</div>
          {options.map((opt) => (
            <label key={opt.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <input
                type="checkbox"
                checked={Boolean(localOptions[opt.id])}
                onChange={(e) =>
                  setLocalOptions((prev) => ({
                    ...prev,
                    [opt.id]: e.target.checked,
                  }))
                }
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}