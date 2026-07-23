import React, { useMemo, useState } from "react";

import appConfig from "../config/appConfig.json";
import metricRegistry from "../config/metricRegistry.json";
import algorithmRegistry from "../config/algorithmRegistry.json";
import analysisFamilyRegistry from "../config/analysisFamilyRegistry.json";
import { ACTIVITY_MAPPING_OPTIONS } from "./ActivityMappingPanel";

const SECTIONS = [
  { id: "overview", label: "Overview", keywords: "overview purpose capabilities quick start" },
  { id: "workflow", label: "Workflow", keywords: "steps upload preview cleaning diary analysis export" },
  { id: "files", label: "File formats", keywords: "bin cwa gt3x agd awd csv xlsx input support light lux background" },
  { id: "activity", label: "Activity processing", keywords: "acc enmo mad mapping raw xyz counts calibration filter epoch" },
  { id: "metrics", label: "Metrics", keywords: "ra is iv m10 l5 fragmentation sleep metrics" },
  { id: "sleep", label: "Sleep algorithms", keywords: "cole kripke sadeh oakley scripps crespo roenneberg windows" },
  { id: "diagnostics", label: "Diagnostics", keywords: "stages errors progress memory 413 500 timeout logs" },
  { id: "limitations", label: "Validation & limitations", keywords: "limitations exploratory thresholds accuracy validation" },
  { id: "developers", label: "Developer reference", keywords: "backend frontend api environment deployment architecture github" },
];

const FILE_ROWS = [
  ["GENEActiv .bin", "Raw tri-axial acceleration and embedded light", "Processed acc, MAD, custom ENMO; LIGHT and LIGHT_LUX", "Large activity and light previews use streamed/background processing."],
  ["Axivity .cwa", "Raw tri-axial acceleration", "Processed acc when conversion is available", "Server conversion depends on the accelerometer/Java environment."],
  ["ActiGraph .gt3x", "Raw tri-axial acceleration; optional type-0x05 lux records", "Processed acc, MAD, custom ENMO; LIGHT and LIGHT_LUX when present", "Activity and light use separate bounded readers; files without lux skip only the light workflow."],
  ["ActiGraph .agd", "Device activity/counts", "Source/device activity", "Preferred when analysis should remain on ActiGraph count scale."],
  ["Actiwatch .awd and native formats", "Device activity", "Source/device activity", "Availability depends on the matching pyActigraphy reader."],
  ["Oxford timeSeries.csv(.gz)", "Epoch-level acc output", "Existing acc column", "Best choice when exact accProcess output is required."],
  ["Generic CSV/Excel", "User-defined columns", "Source activity; derived mappings only when valid XYZ exists", "Timestamp and activity mapping may need to be supplied manually."],
];

function Card({ title, children }) {
  return (
    <section style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 18 }}>
      <h3 style={{ margin: "0 0 10px", fontSize: 18, color: "#0f172a" }}>{title}</h3>
      <div style={{ color: "#475569", lineHeight: 1.6, fontSize: 14 }}>{children}</div>
    </section>
  );
}

function Table({ headers, rows }) {
  return (
    <div style={{ overflowX: "auto", border: "1px solid #e2e8f0", borderRadius: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 680, fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f8fafc" }}>
            {headers.map((header) => (
              <th key={header} style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e2e8f0", color: "#334155" }}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row[0]}`}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} style={{ padding: 10, verticalAlign: "top", borderBottom: rowIndex === rows.length - 1 ? "none" : "1px solid #f1f5f9", color: cellIndex === 0 ? "#0f172a" : "#475569", fontWeight: cellIndex === 0 ? 700 : 400 }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Code({ children }) {
  return <code style={{ background: "#f1f5f9", borderRadius: 6, padding: "2px 5px", color: "#0f172a" }}>{children}</code>;
}

export default function DocumentationPanel({ onClose }) {
  const [activeSection, setActiveSection] = useState("overview");
  const [query, setQuery] = useState("");

  const repositoryUrl = String(import.meta.env.VITE_GITHUB_REPOSITORY_URL || "").replace(/\/$/, "");
  const visibleSections = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return SECTIONS;
    return SECTIONS.filter((section) => `${section.label} ${section.keywords}`.toLowerCase().includes(normalized));
  }, [query]);

  const metricRows = metricRegistry.metrics.map((metric) => [
    metric.shortLabel || metric.label,
    metric.label,
    metricRegistry.categories.find((category) => category.id === metric.category)?.label || metric.category,
    metric.summary || metric.description || "",
  ]);

  const algorithmRows = algorithmRegistry.algorithms.map((algorithm) => [
    algorithm.label,
    algorithm.context || "General actigraphy",
    algorithm.summary || algorithm.description || "",
    algorithm.note || "Review parameters and the activity scale used.",
  ]);

  const familyRows = analysisFamilyRegistry.families.map((family) => [
    family.label,
    family.metrics.join(", ").toUpperCase(),
    family.description,
  ]);

  const sectionContent = {
    overview: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="What this application does">
          <p style={{ marginTop: 0 }}>The {appConfig.appName} provides a guided workflow for loading actigraphy recordings, reviewing activity and light data, applying recording intervals and masks, detecting rest windows, calculating pyActigraphy metrics, and exporting results with diagnostics.</p>
          <p style={{ marginBottom: 0 }}>It is designed to preserve file-level provenance: every output should identify the source file, selected activity basis, algorithm, parameters, preprocessing choices, and warnings.</p>
        </Card>
        <Card title="Recommended first analysis">
          <ol style={{ margin: 0, paddingLeft: 22 }}>
            <li>Upload one known-good recording.</li>
            <li>Inspect the activity preview and recording dates.</li>
            <li>Use the recommended source/processed <Code>acc</Code> activity basis.</li>
            <li>Run continuous RA, IS, and IV before applying count-based thresholds.</li>
            <li>Review M10/L5 components, QC warnings, and the diagnostic stage report.</li>
            <li>Compare results with an independently processed reference file before batch use.</li>
          </ol>
        </Card>
        <Card title="Documentation sources">
          <p style={{ marginTop: 0 }}>This in-app guide is the concise user reference. The repository <Code>docs/</Code> directory contains expanded methods, deployment, architecture, troubleshooting, validation, and change-history documentation.</p>
          <p style={{ marginBottom: 0 }}>Documentation version: <strong>2026-07-23</strong>.</p>
        </Card>
      </div>
    ),
    workflow: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Analysis workflow">
          <Table
            headers={["Step", "Purpose", "Important check"]}
            rows={appConfig.workflow.map((step) => [step.id, step.title, step.description])}
          />
        </Card>
        <Card title="Per-file intervals">
          Start/stop, masking, sleep-diary, and analysis intervals are associated with a file ID. When multiple files are loaded, confirm the selected file before drawing or editing any interval. Intervals that cross midnight are represented by full timestamps and remain valid when the stop time falls on the next calendar day.
          <p style={{ marginBottom: 0 }}>
            Missing timestamps and masked/non-wear epochs remain unavailable and are never converted to zero activity. Defaults are 16 analyzable hours per valid day, two consecutive valid days for multi-day rhythm/SRI outputs, and 80% recorded/scored coverage per sleep window. The masking page keeps these standards unless the user explicitly enables custom thresholds.
          </p>
        </Card>
      </div>
    ),
    files: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Supported input patterns">
          <Table headers={["Format", "Primary signal", "Available analysis basis", "Notes"]} rows={FILE_ROWS} />
        </Card>
        <Card title="Raw versus processed data">
          Raw X/Y/Z samples are retained as three axes and cannot be passed unchanged to metrics that expect one epoch-level activity series. Raw recordings therefore require a scalar activity mapping such as processed <Code>acc</Code>, MAD, or custom ENMO. Count-based files should normally retain their supplied device activity.
        </Card>
        <Card title="Light-source routing">
          Large light files use background jobs. One successful light-preview load returns the standard plot, available channels, and initial multichannel/RGB sample. Selected light metrics run together after one file inspection/load.
          <p style={{ marginBottom: 0 }}>
            Light capability is inspected from file contents. Current-format GT3X files are scanned for official <Code>log.bin</Code> type-<Code>0x05</Code> lux records without decoding X/Y/Z. When present, values are exposed as <Code>LIGHT</Code> (log10(lux + 1)) and <Code>LIGHT_LUX</Code> (lux); when absent, light outputs are skipped and activity remains available.
          </p>
        </Card>
      </div>
    ),
    activity: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Available activity bases">
          <Table
            headers={["Option", "Units", "Use"]}
            rows={ACTIVITY_MAPPING_OPTIONS.map((option) => [option.label, option.units || "Source-dependent", option.description])}
          />
        </Card>
        <Card title="Processed acc pathway">
          For direct raw processing, the application calculates calibrated vector magnitude, applies a fourth-order 20 Hz low-pass filter where supported, removes 1 g, truncates negative values to zero, and averages into the selected epoch. Uploaded Oxford <Code>timeSeries.csv.gz</Code> files use their existing <Code>acc</Code> column directly.
        </Card>
        <Card title="Preview versus analysis">
          The preview signal is independent from the analysis activity basis. Changing a plotted preview does not change the signal used for RA, IS, IV, fragmentation, or sleep-window detection.
        </Card>
        <Card title="Threshold warning">
          Device-count thresholds are not interchangeable with milligravity thresholds. For processed <Code>acc</Code>, ENMO, or MAD, continuous analysis without binarization is the recommended starting point. Every export should retain mapping, units, epoch duration, binarization, and threshold settings.
        </Card>
      </div>
    ),
    metrics: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Metric catalogue">
          <Table headers={["Short name", "Metric", "Category", "Meaning"]} rows={metricRows} />
        </Card>
        <Card title="Analysis families">
          <Table headers={["Family", "Metrics", "Purpose"]} rows={familyRows} />
        </Card>
        <Card title="Relative amplitude">
          RA is calculated from the most active 10 hours and least active 5 hours of the cyclic average daily profile. An RA of exactly 1 is possible when L5 is zero and M10 is positive. Review the M10/L5 values, activity basis, binarization, and threshold before interpreting a boundary value.
        </Card>
      </div>
    ),
    sleep: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Sleep and rest algorithms">
          <Table headers={["Algorithm", "Context", "Purpose", "Caution"]} rows={algorithmRows} />
        </Card>
        <Card title="Crespo and Roenneberg windows">
          Crespo and Roenneberg detect rest/activity structure; they do not guarantee a usable sleep window for every recording. No fallback window is inserted. A no-window result may reflect gaps, non-wear, insufficient contrast, short recording duration, unsuitable scale/thresholds, or algorithm parameters. Roenneberg should generally be tested with 10-minute resampling.
        </Card>
        <Card title="Interpretation">
          Running an algorithm on processed <Code>acc</Code>, MAD, or ENMO is computationally possible, but validation may depend on device, signal scale, population, epoch duration, and parameter settings. Report the exact activity basis and treat unvalidated combinations as exploratory.
        </Card>
      </div>
    ),
    diagnostics: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Diagnostic status meanings">
          <Table
            headers={["Status", "Meaning"]}
            rows={[
              ["Passed", "The stage completed without a captured problem."],
              ["Warning", "The request continued, but a value/window was missing or a recoverable issue was captured."],
              ["Failed", "The stage raised an exception or returned an unusable result."],
              ["Skipped", "A prerequisite was unavailable or the metric was not supported for the selected file/signal."],
            ]}
          />
        </Card>
        <Card title="Live progress">
          The progress percentage represents completion of the analysis pipeline, not estimated time remaining. The interface reports the current stage, stage number, file-level percentage, upload bytes, and raw-page/sample decoding where available.
        </Card>
        <Card title="Common transport errors">
          <ul style={{ margin: 0, paddingLeft: 22 }}>
            <li><strong>413:</strong> upload was rejected by a proxy or ingress before analysis.</li>
            <li><strong>Plain 500:</strong> inspect backend/container logs; structured JSON should be returned for ordinary Python exceptions.</li>
            <li><strong>Exit 137/restart:</strong> commonly indicates memory pressure or container termination.</li>
            <li><strong>504 stream timeout:</strong> Azure ended a synchronous request at 240 seconds; confirm the background-job feature and <Code>/api/jobs/...</Code> endpoints are deployed.</li>
            <li><strong>No GT3X light measurements:</strong> the file was inspected but contained no usable type-<Code>0x05</Code> lux records. Light outputs are skipped; activity remains available.</li>
            <li><strong>Background job not found:</strong> upload and polling reached different replica state; use one active revision/replica or shared persistent <Code>APP_DATA_DIR</Code> storage.</li>
            <li><strong>HTML instead of JSON:</strong> usually a gateway, timeout, or platform error page.</li>
          </ul>
        </Card>
        <Card title="Downloadable reports">
          Each file produces a JSON diagnostic report containing the request ID, reader, recording summary, activity mapping, stage timings, memory, suppressed exceptions, QC warnings, and cleanup status. Use checksums or exact filenames to compare repeated runs.
          <p style={{ marginBottom: 0 }}>
            The Daily Recording Quality table separates gaps, detected/mapped non-wear, manual masks, and analyzable time. Invalid and completely unrecorded days stay missing. Sleep-window QC similarly reports coverage and excludes windows below the configured threshold.
          </p>
        </Card>
      </div>
    ),
    limitations: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Validation requirements">
          Before research use, validate each device/file type and activity basis against a known-good independent workflow. Maintain a golden-file set covering small, medium, large, gapped, light-enabled, and previously failing recordings. Compare metric values within predefined tolerances after every deployment.
        </Card>
        <Card title="Key limitations">
          <ul style={{ margin: 0, paddingLeft: 22 }}>
            <li>Direct memory-safe processed <Code>acc</Code> may not be byte-identical to every Oxford <Code>accProcess</Code> release.</li>
            <li>Derived mg signals and proprietary device counts are not interchangeable.</li>
            <li>Sleep algorithms can execute on generic activity series without being validated for that exact mapping.</li>
            <li>Large-file success depends on upload limits, container memory, temporary storage, background-worker configuration, and keeping at least one replica active.</li>
            <li>A successful calculation is not proof of scientific validity; inspect QC and reference comparisons.</li>
          </ul>
        </Card>
      </div>
    ),
    developers: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Application architecture">
          The frontend is React/Vite. The backend is FastAPI/Uvicorn. Native readers and raw accelerometer adapters produce a Raw-like timestamped activity series for pyActigraphy. Registry JSON files define metrics, algorithms, workflow text, and export options.
        </Card>
        <Card title="Important endpoints">
          <Table
            headers={["Endpoint", "Purpose"]}
            rows={[
              ["GET /api/version", "Deployment version and enabled feature flags."],
              ["GET /api/progress/{request_id}", "Live progress for an active analysis request."],
              ["GET /api/jobs/{job_id}", "Poll background status and retrieve a completed result."],
              ["POST /api/jobs/preview/basic", "Upload and start an activity-preview job."],
              ["POST /api/jobs/light/preview", "Start light preview and return channels plus the initial multichannel sample."],
              ["POST /api/jobs/light/rgb-preview", "Start a resampled multichannel/RGB light-preview job."],
              ["POST /api/jobs/light/channels", "Discover embedded light channels through the background queue."],
              ["POST /api/jobs/analyze/basic", "Upload and start preprocessing, metrics, sleep analysis, QC, and diagnostics."],
              ["POST /api/feedback", "Store user feedback in APP_DATA_DIR."],
            ]}
          />
        </Card>
        <Card title="Documentation maintenance">
          Update both this component and the matching repository Markdown whenever behaviour changes. Metrics and algorithm tables are generated from the registries automatically. Record user-visible changes in <Code>docs/CHANGELOG.md</Code>, method changes in <Code>docs/ACTIVITY_PROCESSING.md</Code> or <Code>docs/METRICS_AND_ALGORITHMS.md</Code>, and deployment changes in <Code>docs/DEPLOYMENT.md</Code>.
        </Card>
      </div>
    ),
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 18, padding: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b", fontWeight: 800 }}>Help & methods</div>
            <h2 style={{ margin: "6px 0 6px", fontSize: 26, color: "#0f172a" }}>Documentation</h2>
            <div style={{ color: "#475569", lineHeight: 1.5 }}>User guidance, methods, file support, diagnostics, limitations, and developer notes.</div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {repositoryUrl && (
              <a href={`${repositoryUrl}/tree/main/docs`} target="_blank" rel="noreferrer" style={{ padding: "9px 13px", borderRadius: 10, border: "1px solid #cbd5e1", color: "#0f172a", textDecoration: "none", fontWeight: 700, fontSize: 13 }}>
                Open GitHub docs
              </a>
            )}
            <button type="button" onClick={onClose} style={{ padding: "9px 13px", borderRadius: 10, border: "none", background: "#0f172a", color: "white", fontWeight: 700, cursor: "pointer" }}>
              Return to workflow
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(210px, 260px) minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
        <aside style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 14, position: "sticky", top: 24 }}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search topics"
            aria-label="Search documentation topics"
            style={{ width: "100%", boxSizing: "border-box", padding: "9px 10px", borderRadius: 9, border: "1px solid #cbd5e1", marginBottom: 10 }}
          />
          <div style={{ display: "grid", gap: 6 }}>
            {visibleSections.map((section) => (
              <button
                key={section.id}
                type="button"
                onClick={() => setActiveSection(section.id)}
                style={{ border: activeSection === section.id ? "1px solid #0f172a" : "1px solid transparent", background: activeSection === section.id ? "#f1f5f9" : "transparent", borderRadius: 9, padding: "9px 10px", textAlign: "left", cursor: "pointer", color: "#0f172a", fontWeight: activeSection === section.id ? 800 : 600 }}
              >
                {section.label}
              </button>
            ))}
            {visibleSections.length === 0 && <div style={{ color: "#64748b", fontSize: 13, padding: 8 }}>No section titles matched.</div>}
          </div>
        </aside>

        <main>{sectionContent[activeSection]}</main>
      </div>
    </div>
  );
}
