import React, { useEffect, useMemo, useState } from "react";

import appConfig from "../config/appConfig.json";
import metricRegistry from "../config/metricRegistry.json";
import algorithmRegistry from "../config/algorithmRegistry.json";
import analysisFamilyRegistry from "../config/analysisFamilyRegistry.json";
import { ACTIVITY_MAPPING_OPTIONS } from "./ActivityMappingPanel";
import TermsOfUseContent from "./TermsOfUseContent";

const DEFAULT_REPOSITORY_URL = "https://github.com/mayank-ramchandani/pyactigraphyui";
const DEFAULT_DOCS_URL = "https://github.com/mayank-ramchandani/pyactigraphyui/tree/main/src/docs";

const FILE_ROWS = [
  ["GENEActiv .bin", "Raw tri-axial acceleration and embedded light", "Recommended processed acc, processed acceleration, ENMO, MAD, PIM, or ZCM", "Large previews and analyses use background/streamed paths where available."],
  ["Axivity .cwa", "Raw tri-axial acceleration", "Recommended processed acc; other mappings only when emitted by the converted time-series", "The server Oxford conversion currently emits epoch-level acc. PIM/ZCM require supplied converted columns."],
  ["ActiGraph .gt3x", "Raw tri-axial acceleration; optional lux records", "Recommended processed acc, processed acceleration, ENMO, MAD, PIM, or ZCM", "Light is inspected separately; absence of lux does not block activity analysis."],
  ["ActiGraph .agd", "Device activity/counts", "Recommended source/device activity", "Preferred when the intended analysis scale is ActiGraph counts."],
  ["Actiwatch .awd and native pyActigraphy formats", "Device activity", "Recommended source/device activity", "Availability depends on the matching pyActigraphy reader."],
  ["Oxford timeSeries.csv(.gz)", "Epoch-level processed acceleration", "Existing acc, ENMO, MAD, PIM, or ZCM column", "The selected existing column and units are retained in result provenance."],
  ["Philips Actiware/RPX CSV", "Localized epoch activity with optional white/RGB light", "Source activity", "English, French, and German exports are parsed directly in UTF-8 or Windows-1252."],
  ["Generic CSV/TXT", "User-defined columns", "Mapped source activity", "Automatic detection or manual timestamp/activity/light mapping is available on Importing Actigraphy Files."],
  ["NHANES PAXHR_H", "Multi-participant hourly summary", "PAXMTSH after participant/time-index preparation", "Filter one SEQN, merge PAXFDAY/PAXFTIME, and build a documented participant-relative time index from PAXSSNHP."],
];

const NARRATIVE_SEARCH_TEXT = {
  overview: "guided ten step actigraphy application provenance preprocessing activity magnitude preview cleaning masking sleep wake classification light temperature sensors metrics results export csv json plots diagnostics github documentation",
  workflow: appConfig.workflow.map((step) => `${step.id} ${step.title} ${step.description}`).join(" "),
  preprocessing: "pre-processing preprocessing recommended settings threshold minimum valid hours valid day quality window calendar day recording aligned 24 hour initial qc 16 hours consecutive windows two days sri rhythm metrics longest run missing data gaps non-wear masks minimum sleep-window coverage 80 percent expected epochs recorded scorable tst waso sleep efficiency customize",
  files: `${FILE_ROWS.flat().join(" ")} encoding utf-8 windows-1252 cp1252 localized actiware french german data_offset generic csv manual mapping nhanes paxhr paxhd seqn paxmtsh`,
  activity: ACTIVITY_MAPPING_OPTIONS.map((option) => `${option.label} ${option.units} ${option.description}`).join(" "),
  cleaning: "start stop recording interval support files masks masking exclusion non-wear file id per-file plot selection crossing midnight missing epochs unavailable not zero",
  sleep: `${algorithmRegistry.algorithms.map((algorithm) => JSON.stringify(algorithm)).join(" ")} sleep diary custom windows plot bedtime wake time classification algorithm cole kripke sadeh oakley scripps crespo roenneberg no fallback`,
  sensors: "other sensors light lux rgb channels preview exposure analysis threshold lmx temperature future version attachment embedded gt3x bin separate light file",
  metrics: `${metricRegistry.metrics.map((metric) => JSON.stringify(metric)).join(" ")} ${analysisFamilyRegistry.families.map((family) => JSON.stringify(family)).join(" ")} analysis setup families individual metrics parameters ra is iv m10 l5 sri fragmentation`,
  results: "generate results page nine view results plots tables csv json diagnostics quality control multi-file three significant figures export outputs page ten configuration",
  diagnostics: "request id stages progress upload background job 413 500 503 504 timeout memory json diagnostic daily recording quality gaps warnings failed skipped passed",
  provenance: "pyactigraphy preprocessing provenance calibration filtering epochs timestamps gaps nonwear masks activity mapping units parameters software version citations reproducibility feedback storage",
  developers: "react vite fastapi uvicorn endpoint api jobs progress registries documentation maintenance github environment variable deployment architecture",
  terms: "terms of use OBI Ontario Brain Institute Centre for Analytics hosted transient temporary data retention privacy de-identification research educational medical device acceptable use diagnostics feedback",
};

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "workflow", label: "10-step workflow" },
  { id: "preprocessing", label: "Pre-processing" },
  { id: "files", label: "File formats" },
  { id: "activity", label: "Activity metric" },
  { id: "cleaning", label: "Cleaning & masking" },
  { id: "sleep", label: "Sleep-wake classification" },
  { id: "sensors", label: "Other sensors" },
  { id: "metrics", label: "Metrics & analysis" },
  { id: "results", label: "Results & export" },
  { id: "diagnostics", label: "Diagnostics" },
  { id: "provenance", label: "Preprocessing & provenance" },
  { id: "terms", label: "Terms of use" },
  { id: "developers", label: "Developer reference" },
];

function Card({ title, children }) {
  return (
    <section className="documentation-card" style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 18, textAlign: "center" }}>
      <h3 style={{ margin: "0 0 10px", fontSize: 18, color: "#0f172a" }}>{title}</h3>
      <div style={{ color: "#475569", lineHeight: 1.65, fontSize: 14 }}>{children}</div>
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
              <th key={header} style={{ textAlign: "center", padding: 10, borderBottom: "1px solid #e2e8f0", color: "#334155" }}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row[0]}`}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} style={{ padding: 10, verticalAlign: "top", textAlign: "center", borderBottom: rowIndex === rows.length - 1 ? "none" : "1px solid #f1f5f9", color: cellIndex === 0 ? "#0f172a" : "#475569", fontWeight: cellIndex === 0 ? 700 : 400 }}>
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

function extractDocumentationText(value) {
  if (value == null || typeof value === "boolean" || typeof value === "function") return "";
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(extractDocumentationText).join(" ");
  if (React.isValidElement(value)) {
    const props = value.props || {};
    return [
      props.title,
      props.label,
      props.headers,
      props.rows,
      props.children,
    ].map(extractDocumentationText).join(" ");
  }
  if (typeof value === "object") {
    return Object.entries(value)
      .filter(([key]) => key !== "style")
      .map(([, nested]) => extractDocumentationText(nested))
      .join(" ");
  }
  return "";
}

export default function DocumentationPanel({ onClose }) {
  const [activeSection, setActiveSection] = useState("overview");
  const [query, setQuery] = useState("");

  const repositoryUrl = String(import.meta.env.VITE_GITHUB_REPOSITORY_URL || DEFAULT_REPOSITORY_URL).replace(/\/$/, "");
  const derivedDocsUrl = repositoryUrl === DEFAULT_REPOSITORY_URL
    ? DEFAULT_DOCS_URL
    : `${repositoryUrl}/tree/main/src/docs`;
  const githubDocsUrl = String(import.meta.env.VITE_GITHUB_DOCS_URL || derivedDocsUrl).replace(/\/$/, "");

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
    algorithm.note || "Review parameters and activity scale.",
  ]);

  const familyRows = analysisFamilyRegistry.families.map((family) => [
    family.label,
    family.metrics.length ? family.metrics.join(", ").toUpperCase() : (family.id === "cosinor" ? "Mesor, amplitude, acrophase, fit statistics" : "Configured family output"),
    family.description,
  ]);

  const sectionContent = {
    overview: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="What the application does">
          The {appConfig.appName} guides users from file import through preprocessing, activity estimation, activity preview, cleaning, sleep-wake classification, optional sensor analysis, metric selection, result generation, and export. The backend retains source filenames, resolved activity mapping, preprocessing thresholds, algorithms, parameters, quality-control warnings, and diagnostics.
        </Card>
        <Card title="Navigation">
          After at least one actigraphy file is imported, pages 2 through 9 in the left workflow are directly clickable. Users may review pages in order or jump to a later setup page without repeatedly pressing Next. Page 10, Export Outputs, remains locked until results have been generated successfully.
        </Card>
        <Card title="Documentation sources">
          This page is the searchable in-application guide. The repository documentation contains expanded user, methods, deployment, architecture, troubleshooting, preprocessing, provenance, and change-history material. Documentation version: <strong>2026-07-24</strong>.
        </Card>
      </div>
    ),
    workflow: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Current overall process">
          <Table headers={["Step", "Page", "Purpose"]} rows={appConfig.workflow.map((step) => [step.id, step.title, step.description])} />
        </Card>
        <Card title="Where optional files are added">
          The Importing Actigraphy Files page accepts actigraphy recordings only. Start/stop and mask files are added on Cleaning and Masking. Sleep diaries are added on Sleep-wake Classification. Separate light, temperature, and other sensor files are added on Other Sensors. This keeps every optional input beside the processing choice it affects.
        </Card>
      </div>
    ),
    preprocessing: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Recommended data-quality settings">
          <ul style={{ margin: 0, paddingLeft: 22 }}>
            <li><strong>Recommended valid-window minimum:</strong> at least 16 analyzable hours.</li>
            <li><strong>Recommended multi-window rhythm/SRI eligibility:</strong> at least 2 consecutive valid quality windows.</li>
            <li><strong>Recommended sleep-window coverage:</strong> at least 80% of expected epochs remain recorded and scorable.</li>
          </ul>
          <p style={{ marginBottom: 0 }}>These are configurable starting points. Enable “Customize the recommended data-quality thresholds” when a protocol or sensitivity analysis requires different criteria.</p>
        </Card>
        <Card title="Initial QC before preprocessing decisions">
          Step 2 loads each uploaded recording and reports recorded time, gaps, detected/mapped non-wear, and effective coverage for every candidate quality window. This first inspection occurs before uploaded/manual masks and start/stop limits. Final QC is recalculated during analysis after all selected preprocessing has been applied.
        </Card>
        <Card title="Calendar days or recording-aligned windows">
          <strong>Calendar day</strong> is the recommended default: midnight-to-midnight windows preserve clock-day interpretation for daily summaries and circadian timing. <strong>Recording-aligned 24-hour windows</strong> begin at the first retained timestamp and are available as a sensitivity option for short or deployment-anchored recordings. For a complete 4 PM-to-4 PM recording, calendar mode yields an 8-hour first date and a 16-hour second date, while recording-aligned mode yields one complete 24-hour quality window. Results and exports record the selected basis.
        </Card>
        <Card title="What recommended minimum sleep-window coverage means">
          Coverage is calculated for each diary-defined or automatically estimated sleep window. The expected number of epochs is compared with epochs still available after recording gaps, start/stop truncation, detected non-wear, and manual masks. A recommended threshold of <Code>0.8</Code> means at least 80% must remain. Windows below the configured threshold are excluded from TST, WASO, sleep efficiency, and other window-dependent summaries instead of being filled or treated as zero activity.
        </Card>
        <Card title="Consecutive-window requirement">
          The backend uses the longest uninterrupted run under the selected quality-window basis. Two valid windows separated by an invalid or missing window do not meet a two-consecutive-window requirement. SRI additionally requires valid scored epoch pairs exactly 24 hours apart, so eligibility does not guarantee an SRI value when paired data are insufficient.
        </Card>
      </div>
    ),
    files: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Supported input patterns">
          <Table headers={["Format", "Primary signal", "Available activity basis", "Notes"]} rows={FILE_ROWS} />
        </Card>
        <Card title="Localized Actiware/RPX CSV files">
          Philips Actiware/RPX epoch exports are recognized in English, French, and German. UTF-8, UTF-8 with BOM, Windows-1252, and Latin-1-compatible text are decoded safely. The backend locates the actual epoch table instead of relying on pyActigraphy’s English-only data-offset assumptions, and retains white/RGB light channels when present.
        </Card>
        <Card title="Generic CSV and TXT files">
          Automatic detection is attempted first. When it is incorrect, enable manual CSV mapping on the Importing Actigraphy Files page and provide timestamp plus activity columns. Light, temperature, non-wear, and separate time columns can also be mapped where present.
        </Card>
        <Card title="NHANES PAXHR_H">
          PAXHR_H is a cohort-level hourly summary rather than one timestamped actigraphy recording. The application now identifies it and gives preparation guidance instead of a generic unsupported-file error. Filter to one participant (SEQN), merge PAXFDAY and PAXFTIME from PAXHD_H, and use PAXSSNHP to build a participant-relative hourly time index. Because the public files do not disclose the actual calendar date, use and document a synthetic anchor date consistent with the reported day of week, then map PAXMTSH as activity.
        </Card>
      </div>
    ),
    activity: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Six activity-basis options">
          <Table headers={["Option", "Units", "Behaviour"]} rows={ACTIVITY_MAPPING_OPTIONS.map((option) => [option.label, option.units || "Source-dependent", option.description])} />
        </Card>
        <Card title="Interpretation">
          Raw X/Y/Z acceleration is reduced to one epoch-level scalar series before pyActigraphy metrics are calculated. The available bases are processed acceleration, ENMO, MAD, PIM, ZCM, and source/device activity. Results retain the selected mapping, units, epoch duration, filtering, reducer parameters, and source column or processing engine.
        </Card>
      </div>
    ),
    cleaning: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Start/stop intervals">
          Start/stop intervals define the effective recording period for each file. They can be uploaded or created with full timestamps and the activity plot. Overnight intervals are valid when the stop timestamp is on the following calendar date.
        </Card>
        <Card title="Masks and non-wear">
          Masks exclude invalid or non-wear intervals. Uploaded and manually selected intervals retain a file ID, so one file’s exclusions are not applied to another recording. Missing, masked, and non-wear epochs remain unavailable; they are not converted to zero activity.
        </Card>
      </div>
    ),
    sleep: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Sleep windows">
          Upload diary windows or create per-file bedtime/wake-time windows using timestamp fields and the activity plot. When no diary window is available, Crespo_AoT or Roenneberg_AoT may estimate a main rest window. The application does not insert a lowest-activity fallback window when the selected method returns no usable onset/offset pair.
        </Card>
        <Card title="Classification algorithms">
          <Table headers={["Algorithm", "Context", "Purpose", "Caution"]} rows={algorithmRows} />
        </Card>
        <Card title="Coverage and unavailable sleep metrics">
          Each candidate sleep window is checked against the preprocessing coverage threshold. A missing window, an algorithm failure, or insufficient scorable coverage produces an unavailable/skipped result with diagnostics rather than an invented sleep estimate.
        </Card>
      </div>
    ),
    sensors: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Light data">
          The Other Sensors page can inspect embedded light in supported actigraphy files or use a separately uploaded light file. It provides light channel discovery, activity-aligned preview, RGB/multichannel preview when available, and configuration for selected light metrics. Light metrics run with the main analysis when Generate Results is selected.
        </Card>
        <Card title="Temperature and additional sensors">
          Temperature or other sensor files can be attached on the Other Sensors page for future workflow development. Their filenames and basic file metadata are retained in the analysis configuration/export, but the current version does not calculate temperature or generic sensor metrics and labels these attachments as future analysis so they are not mistaken for completed processing.
        </Card>
      </div>
    ),
    metrics: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Analysis families">
          <Table headers={["Family", "Metrics", "Purpose"]} rows={familyRows} />
        </Card>
        <Card title="Available metrics">
          <Table headers={["Code", "Metric", "Category", "Summary"]} rows={metricRows} />
        </Card>
        <Card title="Analysis Set-up page">
          Page 8 is for selecting families or individual metrics and configuring shared or metric-specific parameters. It does not run the analysis. Continue to page 9 to choose files, generate results, and review outputs.
        </Card>
      </div>
    ),
    results: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Generate and view results">
          Page 9 contains the only Generate Results action. It runs each selected actigraphy file, selected light metrics where supported, data-quality checks, sleep-window checks, metric calculation, plots, QC summaries, and structured diagnostics. Results remain on page 9 for review; successful completion unlocks page 10.
        </Card>
        <Card title="Export outputs">
          Page 10 downloads selected tables and report-ready outputs, including result summaries, CSV-compatible tables, JSON configuration/diagnostics, QC warnings, and other export registry items. Exported values preserve file identifiers and the resolved analysis configuration.
        </Card>
      </div>
    ),
    diagnostics: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Diagnostic status meanings">
          <Table headers={["Status", "Meaning"]} rows={[
            ["Passed", "The stage completed without a captured problem."],
            ["Warning", "Processing continued, but a recoverable issue or unavailable value was recorded."],
            ["Failed", "The stage raised an exception or returned an unusable result."],
            ["Skipped", "A prerequisite was unavailable or the metric was unsupported for the selected signal."],
          ]} />
        </Card>
        <Card title="Common transport errors">
          <ul style={{ margin: 0, paddingLeft: 22 }}>
            <li><strong>413:</strong> proxy/ingress upload limit rejected the file before analysis.</li>
            <li><strong>500:</strong> inspect structured diagnostics and backend/container logs.</li>
            <li><strong>503/504:</strong> upstream disconnect, platform timeout, or missing background-job deployment.</li>
            <li><strong>Background job not found:</strong> upload and polling may have reached different replicas without shared job storage.</li>
            <li><strong>No light data:</strong> activity remains usable and light outputs are skipped.</li>
          </ul>
        </Card>
        <Card title="Quality tables">
          Recording Quality by 24-hour Window separates expected time, gaps, detected/mapped non-wear, manual masks, and analyzable time. It reports the selected calendar-day or recording-aligned basis, total valid windows, longest consecutive valid-window run, and resolved recommended/customized thresholds. Sleep-window QC reports expected, available, and coverage proportions for each candidate window.
        </Card>
      </div>
    ),
    provenance: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="pyActigraphy foundation">
          Native readers, non-parametric activity metrics, Crespo_AoT/Roenneberg_AoT procedures, and Cosinor modelling use pyActigraphy. The web backend prepares the selected scalar activity series, applies file-specific preprocessing, and then calls the corresponding pyActigraphy methods. See <a href="https://ghammad.github.io/pyActigraphy/" target="_blank" rel="noreferrer">pyActigraphy documentation</a>, <a href="https://github.com/ghammad/pyActigraphy" target="_blank" rel="noreferrer">source code</a>, and the <a href="https://doi.org/10.1371/journal.pcbi.1009514" target="_blank" rel="noreferrer">package paper</a>.
        </Card>
        <Card title="Recorded preprocessing">
          Results retain reader/file format, requested and resolved activity mapping, source column or raw-processing engine, units, sample rate, epoch duration, calibration/filter details, start/stop limits, non-wear and masks, valid-day decisions, sleep-window coverage, algorithm parameters, application version, Git commit, and diagnostic stages. Missing and excluded epochs remain unavailable rather than becoming zero activity.
        </Card>
        <Card title="Feedback location">
          Feedback is appended to <Code>{"${APP_DATA_DIR}/feedback.jsonl"}</Code>. A contact email is required, and each submission plus its attached technical context is retained for 30 days before automatic deletion. Configure persistent storage and <Code>FEEDBACK_ADMIN_TOKEN</Code>, then open <Code>/?feedback-admin=1</Code> in the frontend to search, inspect, and export current reports. The protected <Code>GET /api/admin/feedback</Code> and <Code>GET /api/admin/feedback/export</Code> endpoints remain available for direct access. Reports include selected settings, filenames, progress, request ID, and visible errors, but not raw files.
        </Card>
      </div>
    ),
    terms: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Hosting and funding">
          This web tool is hosted by the Ontario Brain Institute (OBI), with development supported through the Centre for Analytics.
        </Card>
        <TermsOfUseContent compact />
      </div>
    ),
    developers: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Application architecture">
          The frontend is React/Vite and the backend is FastAPI/Uvicorn. Native readers and raw accelerometer adapters produce a timestamped scalar activity series for analysis. Registry JSON files define metrics, algorithms, families, workflow labels, and export options.
        </Card>
        <Card title="Important endpoints">
          <Table headers={["Endpoint", "Purpose"]} rows={[
            ["GET /api/version", "Deployment version and enabled feature flags."],
            ["GET /api/progress/{request_id}", "Live analysis progress."],
            ["GET /api/jobs/{job_id}", "Poll background status and retrieve a completed result."],
            ["POST /api/jobs/qc/initial", "Start initial per-window data-coverage QC for Step 2."],
            ["POST /api/jobs/preview/basic", "Start activity preview."],
            ["POST /api/jobs/light/preview", "Start embedded/separate light preview."],
            ["POST /api/jobs/light/analyze", "Run selected light metrics."],
            ["POST /api/jobs/analyze/basic", "Run preprocessing, sleep, metrics, QC, and diagnostics."],
            ["POST /api/feedback", "Store user feedback in APP_DATA_DIR."],
            ["GET /api/admin/feedback", "Token-protected feedback list, filters, counts, and storage details."],
            ["GET /api/admin/feedback/export", "Token-protected CSV or JSONL feedback export."],
          ]} />
        </Card>
        <Card title="Documentation and search maintenance">
          The in-app search indexes section labels plus full narrative content, workflow descriptions, file-format text, activity options, algorithm registry content, metric registry content, and analysis-family content. When behaviour changes, update this component and the matching repository Markdown, then record the user-visible change in <Code>docs/CHANGELOG.md</Code>.
        </Card>
      </div>
    ),
  };

  const visibleSections = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return SECTIONS;

    return SECTIONS.filter((section) => {
      const renderedText = extractDocumentationText(sectionContent[section.id]);
      const corpus = `${section.label} ${NARRATIVE_SEARCH_TEXT[section.id] || ""} ${renderedText}`.toLowerCase();
      return terms.every((term) => corpus.includes(term));
    });
  }, [query]);

  useEffect(() => {
    if (visibleSections.length > 0 && !visibleSections.some((section) => section.id === activeSection)) {
      setActiveSection(visibleSections[0].id);
    }
  }, [activeSection, visibleSections]);

  return (
    <div className="documentation-centered" style={{ display: "grid", gap: 16, textAlign: "center" }}>
      <div style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 18, padding: 20 }}>
        <div style={{ display: "flex", justifyContent: "center", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ width: "100%" }}>
            <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b", fontWeight: 800 }}>Help & methods</div>
            <h2 style={{ margin: "6px 0 6px", fontSize: 26, color: "#0f172a" }}>Documentation</h2>
            <div style={{ color: "#475569", lineHeight: 1.5 }}>Searchable user guidance, methods, file support, diagnostics, preprocessing provenance, and developer notes.</div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center", width: "100%" }}>
            <a href={githubDocsUrl} target="_blank" rel="noreferrer" style={{ padding: "9px 13px", borderRadius: 10, border: "1px solid #cbd5e1", color: "#0f172a", textDecoration: "none", fontWeight: 700, fontSize: 13 }}>
              Open GitHub docs
            </a>
            <button type="button" onClick={onClose} style={{ padding: "9px 13px", borderRadius: 10, border: "none", background: "#0f172a", color: "white", fontWeight: 700, cursor: "pointer" }}>
              Return to workflow
            </button>
          </div>
        </div>
      </div>

      <div className="documentation-content-grid" style={{ display: "grid", gridTemplateColumns: "minmax(220px, 280px) minmax(0, 1fr)", gap: 16, alignItems: "start" }}>
        <aside style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 14, position: "sticky", top: 24 }}>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search all documentation"
            aria-label="Search all documentation content"
            style={{ width: "100%", boxSizing: "border-box", padding: "10px 11px", borderRadius: 9, border: "1px solid #cbd5e1", marginBottom: 7 }}
          />
          <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.4, marginBottom: 10 }}>
            Searches headings, explanations, workflow text, metrics, algorithms, formats, errors, and developer content.
          </div>
          <div style={{ display: "grid", gap: 6 }}>
            {visibleSections.map((section) => (
              <button
                key={section.id}
                type="button"
                onClick={() => setActiveSection(section.id)}
                style={{ border: activeSection === section.id ? "1px solid #0f172a" : "1px solid transparent", background: activeSection === section.id ? "#f1f5f9" : "transparent", borderRadius: 9, padding: "9px 10px", textAlign: "center", cursor: "pointer", color: "#0f172a", fontWeight: activeSection === section.id ? 800 : 600 }}
              >
                {section.label}
              </button>
            ))}
            {visibleSections.length === 0 && <div style={{ color: "#64748b", fontSize: 13, padding: 8 }}>No documentation content matched this search.</div>}
          </div>
        </aside>

        <main>{visibleSections.length > 0 ? sectionContent[activeSection] : null}</main>
      </div>
    </div>
  );
}
