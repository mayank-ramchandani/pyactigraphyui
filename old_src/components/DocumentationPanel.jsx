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
  ["GENEActiv .bin", "Raw X/Y/Z acceleration, with embedded light and temperature", "Recommended source / processed acc", "ENMO, MAD, PIM, and ZCM are available. Embedded light is used only when present."],
  ["Axivity .cwa", "Raw X/Y/Z acceleration", "Processed acc", "Other activity measures are available when they are present in a converted time-series file."],
  ["ActiGraph .gt3x", "Raw X/Y/Z acceleration, with optional lux", "Recommended source / processed acc", "Activity analysis still works when the file contains no light data."],
  ["ActiGraph .agd", "Device activity counts", "Source/device activity", "Use this when the analysis should remain on the ActiGraph count scale."],
  ["Actiwatch .awd and other native pyActigraphy formats", "Device activity", "Source/device activity", "Available options depend on the information contained in the file."],
  ["Oxford timeSeries.csv(.gz)", "Epoch-level processed acceleration", "Existing acc column", "Existing ENMO, MAD, PIM, or ZCM columns can also be selected."],
  ["Philips Actiware/RPX CSV", "Epoch activity with optional white/RGB light", "Source activity", "English, French, and German exports are supported, including Windows-1252 files."],
  ["Generic CSV/TXT", "User-defined columns", "Mapped activity column", "The app detects columns automatically; manual mapping is available when needed."],
  ["NHANES PAXHR_H", "Hourly summaries for multiple participants", "PAXMTSH after preparation", "Select one participant and create a documented participant-relative time index before upload."],
];

const NARRATIVE_SEARCH_TEXT = {
  overview: "start here user guide upload de-identified data recommended settings preview analysis results export research educational privacy feedback",
  workflow: appConfig.workflow.map((step) => `${step.id} ${step.title} ${step.description}`).join(" "),
  preprocessing: "pre-processing recommended settings 16 analyzable hours calendar day recording aligned 24 hour consecutive valid windows sleep coverage 80 percent gaps non-wear masks missing data",
  files: `${FILE_ROWS.flat().join(" ")} encoding utf-8 windows-1252 localized actiware french german generic csv manual mapping nhanes paxhr`,
  activity: `${ACTIVITY_MAPPING_OPTIONS.map((option) => `${option.label} ${option.units} ${option.description}`).join(" ")} recommended default processed acceleration enmo mad pim zcm source counts`,
  cleaning: "recording start stop masking exclusion non-wear file-specific intervals crossing midnight missing epochs unavailable not zero",
  sleep: `${algorithmRegistry.algorithms.map((algorithm) => JSON.stringify(algorithm)).join(" ")} sleep diary custom windows bedtime wake time crespo roenneberg no fallback coverage unavailable`,
  sensors: "light lux rgb preview exposure temperature other sensors embedded separate file",
  metrics: `${metricRegistry.metrics.map((metric) => JSON.stringify(metric)).join(" ")} ${analysisFamilyRegistry.families.map((family) => JSON.stringify(family)).join(" ")} analysis families metrics parameters relative amplitude ra is iv m10 l5 sri fragmentation cosinor`,
  results: "generate results plots tables quality control warnings multi-file export csv json configuration three significant figures",
  troubleshooting: "warning failed skipped 413 500 503 504 timeout background job no light csv metric unavailable relative amplitude sleep window feedback request id",
  methods: "pyactigraphy methods reproducibility provenance activity mapping units parameters preprocessing masks valid windows software version citation data handling feedback 30 days",
  terms: "terms of use Ontario Brain Institute Centre for Analytics privacy de-identification research educational medical device acceptable use feedback retention",
};

const SECTIONS = [
  { id: "overview", label: "Start here" },
  { id: "workflow", label: "10-step workflow" },
  { id: "preprocessing", label: "Pre-processing" },
  { id: "files", label: "File formats" },
  { id: "activity", label: "Choosing an activity measure" },
  { id: "cleaning", label: "Cleaning & masking" },
  { id: "sleep", label: "Sleep-wake classification" },
  { id: "sensors", label: "Light & other sensors" },
  { id: "metrics", label: "Metrics & analysis" },
  { id: "results", label: "Results & export" },
  { id: "troubleshooting", label: "Troubleshooting" },
  { id: "methods", label: "Methods & reproducibility" },
  { id: "terms", label: "Terms of use" },
];

function Card({ title, children }) {
  return (
    <section className="documentation-card" style={{ background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 18 }}>
      <h3 style={{ margin: "0 0 10px", fontSize: 18, color: "#0f172a", textAlign: "center" }}>{title}</h3>
      <div style={{ color: "#475569", lineHeight: 1.7, fontSize: 14, textAlign: "left" }}>{children}</div>
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
                <td key={cellIndex} style={{ padding: 10, verticalAlign: "top", textAlign: "left", borderBottom: rowIndex === rows.length - 1 ? "none" : "1px solid #f1f5f9", color: cellIndex === 0 ? "#0f172a" : "#475569", fontWeight: cellIndex === 0 ? 700 : 400 }}>
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
    return [props.title, props.label, props.headers, props.rows, props.children].map(extractDocumentationText).join(" ");
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
  const derivedDocsUrl = repositoryUrl === DEFAULT_REPOSITORY_URL ? DEFAULT_DOCS_URL : `${repositoryUrl}/tree/main/src/docs`;
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
    algorithm.note || "Review the selected parameters and activity scale.",
  ]);

  const familyRows = analysisFamilyRegistry.families.map((family) => [
    family.label,
    family.metrics.length ? family.metrics.join(", ").toUpperCase() : (family.id === "cosinor" ? "Mesor, amplitude, acrophase, fit statistics" : "Configured family output"),
    family.description,
  ]);

  const sectionContent = {
    overview: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="What this application is for">
          The {appConfig.appName} helps researchers import actigraphy recordings, review data quality, choose preprocessing and analysis settings, calculate activity and sleep-related measures, inspect results, and export a reproducible record of the analysis.
        </Card>
        <Card title="A simple way to get started">
          <ol style={{ margin: 0, paddingLeft: 22 }}>
            <li>Upload de-identified actigraphy files.</li>
            <li>Keep the recommended preprocessing and activity settings unless your protocol requires something different.</li>
            <li>Preview each recording and review gaps, dates, and signal quality.</li>
            <li>Add cleaning intervals, sleep windows, or light data when applicable.</li>
            <li>Select metrics, generate results, review warnings, and export the outputs.</li>
          </ol>
        </Card>
        <Card title="Before uploading data">
          Remove participant names, health-card numbers, dates of birth, and other direct identifiers from filenames and support files. This tool supports research and educational use; it does not provide a diagnosis or treatment recommendation.
        </Card>
      </div>
    ),
    workflow: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="The complete workflow">
          <Table headers={["Step", "Page", "What you do"]} rows={appConfig.workflow.map((step) => [step.id, step.title, step.description])} />
        </Card>
        <Card title="Where to add supporting files">
          Upload actigraphy recordings on Step 1. Add start/stop files and masks on Step 5, sleep diaries on Step 6, and separate light or other sensor files on Step 7. Steps 2–9 can be opened from the left workflow after at least one actigraphy file is uploaded. Export unlocks after results are generated.
        </Card>
      </div>
    ),
    preprocessing: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Recommended starting settings">
          <ul style={{ margin: 0, paddingLeft: 22 }}>
            <li><strong>Valid quality window:</strong> at least 16 analyzable hours.</li>
            <li><strong>Multi-day rhythm and SRI eligibility:</strong> at least 2 consecutive valid quality windows.</li>
            <li><strong>Sleep-window coverage:</strong> at least 80% of expected epochs remain available and scorable.</li>
          </ul>
          <p style={{ marginBottom: 0 }}>Keep these settings for a standard analysis. Customize them only when your study protocol or sensitivity analysis specifies different criteria.</p>
        </Card>
        <Card title="Calendar day or recording-aligned window?">
          <p><strong>Calendar day</strong> is the recommended default. It evaluates midnight-to-midnight periods and keeps daily summaries aligned with clock dates.</p>
          <p style={{ marginBottom: 0 }}><strong>Recording-aligned 24-hour windows</strong> begin at the first retained timestamp. They can be useful for short recordings or studies organized around the device-deployment time. The selected approach is included in the results and exports.</p>
        </Card>
        <Card title="How missing and excluded data are handled">
          Recording gaps, detected non-wear, and manual masks remain unavailable. They are not changed to zero activity. Initial quality information appears on Step 2, and final quality is recalculated after start/stop limits and masks are applied.
        </Card>
        <Card title="Sleep-window coverage">
          Coverage compares the expected epochs inside a sleep window with the epochs still available after gaps, non-wear, start/stop limits, and masks. At the recommended threshold of <Code>0.8</Code>, at least 80% must remain. Lower-coverage windows are excluded from sleep summaries rather than filled in.
        </Card>
      </div>
    ),
    files: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Supported file patterns">
          <Table headers={["Format", "Typical content", "Recommended activity basis", "What to know"]} rows={FILE_ROWS} />
        </Card>
        <Card title="CSV and text files">
          The application first tries to identify timestamp, activity, light, temperature, and non-wear columns automatically. Turn on manual CSV mapping only when the detected columns are incorrect. Confirm the preview before continuing.
        </Card>
        <Card title="Localized Actiware/RPX files">
          English, French, and German Actiware exports are supported. The importer can read common UTF-8 and Windows-1252 encodings and can retain white, red, green, and blue light channels when they are present.
        </Card>
        <Card title="NHANES PAXHR_H files">
          PAXHR_H contains hourly summaries for many participants rather than one continuous recording. Prepare one participant at a time, construct a documented participant-relative time index, and map PAXMTSH as the activity column. Do not upload the full cohort file as one recording.
        </Card>
      </div>
    ),
    activity: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Recommended choice for most users">
          Choose <strong>Recommended source / processed acc</strong> unless your protocol requires a specific signal. It uses the activity series already supplied by count-based files and creates an epoch-level processed acceleration series for supported raw accelerometer files.
        </Card>
        <Card title="Available activity measures">
          <Table headers={["Option", "Units", "When it is useful"]} rows={ACTIVITY_MAPPING_OPTIONS.map((option) => [option.label, option.units || "Source-dependent", option.description])} />
        </Card>
        <Card title="Why the choice matters">
          All selected rest-activity metrics use the chosen epoch-level activity series. Counts, mg, mg·s/epoch, and crossings/epoch are different scales, so thresholds must be chosen for the selected measure. The resolved measure, units, epoch duration, and settings are included with the results.
        </Card>
      </div>
    ),
    cleaning: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Recording start and stop">
          Use start/stop intervals to define the period that should be analysed for each file. You can upload intervals or select them from the activity plot. Full timestamps are supported, including intervals that cross midnight.
        </Card>
        <Card title="Masks and non-wear">
          Masks remove invalid periods from analysis. Uploaded and manually selected intervals remain linked to the correct file, so an exclusion for one recording is not applied to another. Missing, masked, and non-wear epochs remain unavailable rather than becoming zero activity.
        </Card>
        <Card title="What to review before continuing">
          Check that each interval is assigned to the intended file, start times occur before stop times, and overnight intervals use the correct next-day date. Review the updated plot whenever manual intervals are added.
        </Card>
      </div>
    ),
    sleep: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Sleep windows">
          Upload a sleep diary or create file-specific bedtime and wake-time windows. When no diary is available, Crespo_AoT or Roenneberg_AoT can estimate a main rest window. The application does not create a lowest-activity fallback window when the selected method finds no usable onset and offset.
        </Card>
        <Card title="Classification algorithms">
          <Table headers={["Algorithm", "Context", "Purpose", "Important note"]} rows={algorithmRows} />
        </Card>
        <Card title="When a sleep result is unavailable">
          A sleep metric may be unavailable because no window was supplied or detected, the selected algorithm could not score the data, or the window did not meet the configured coverage threshold. Review the sleep-window QC message before changing settings.
        </Card>
      </div>
    ),
    sensors: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Light data">
          Step 7 can inspect light embedded in a supported actigraphy file or use a separate light file. Review the available channels, preview the signal, and select light metrics before generating results. A recording with no usable light can still be analysed for activity; only the light outputs are skipped.
        </Card>
        <Card title="RGB and multichannel light">
          When red, green, blue, white, or lux channels are available, the preview identifies them separately. Confirm the units and channel used by each selected light metric, especially when choosing thresholds.
        </Card>
        <Card title="Temperature and additional sensors">
          Temperature and other sensor files may be attached for record-keeping, but the current version does not calculate temperature or generic sensor metrics. These files are clearly labelled as not yet analysed.
        </Card>
      </div>
    ),
    metrics: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Analysis families">
          <Table headers={["Family", "Included outputs", "Purpose"]} rows={familyRows} />
        </Card>
        <Card title="Available metrics">
          <Table headers={["Code", "Metric", "Category", "What it describes"]} rows={metricRows} />
        </Card>
        <Card title="Choosing Standard or Custom mode">
          Use Standard mode for common analysis groups with their recommended starting parameters. Use Custom mode when you need individual metrics or protocol-specific settings. Step 8 configures the analysis; Step 9 runs it.
        </Card>
      </div>
    ),
    results: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Generate and review results">
          Step 9 runs the selected files and analyses. Review the file-level status, summary values, plots, daily recording quality, valid-window counts, sleep-window coverage, warnings, selected activity measure, and light results where available.
        </Card>
        <Card title="Understanding warnings">
          A warning means processing continued but something needs review, such as an excluded low-coverage day, an unavailable metric, or missing light data. A failed status means that the affected stage could not produce a usable result. Other successful outputs may still be valid.
        </Card>
        <Card title="Export outputs">
          Step 10 downloads the selected tables and supporting information, including result summaries, CSV-ready tables, analysis settings, quality-control information, and diagnostics. Keep the exported configuration with the result tables so the analysis can be reproduced later.
        </Card>
      </div>
    ),
    troubleshooting: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Status meanings">
          <Table headers={["Status", "Meaning", "What to do"]} rows={[
            ["Passed", "The stage completed normally.", "No action is required."],
            ["Warning", "Processing continued, but a value or quality issue needs review.", "Read the message and confirm whether the result is suitable for your analysis."],
            ["Failed", "The stage could not produce a usable result.", "Review the error, file format, selected settings, and affected file."],
            ["Skipped", "A required signal, window, or supported method was unavailable.", "Confirm that the necessary data and settings were supplied."],
          ]} />
        </Card>
        <Card title="Common problems">
          <Table headers={["Message", "Likely meaning", "Recommended action"]} rows={[
            ["413 / file too large", "The upload was rejected before processing began.", "Try a smaller file or contact the service team with the file size and format."],
            ["500, 503, or 504", "The service encountered an error, timeout, or temporary interruption.", "Retry once, preferably with one file. If it repeats, submit feedback with the request ID and visible error."],
            ["Background job not found", "The saved processing job is no longer available.", "Start the preview or analysis again. Avoid refreshing or closing the page during the run."],
            ["No light data", "No usable light channel was found.", "Continue with activity analysis or upload a separate light file."],
            ["Metric unavailable or null", "The metric lacked enough valid data, required windows, or a supported signal.", "Review daily QC, consecutive valid windows, sleep-window coverage, and metric requirements."],
            ["No Crespo/Roenneberg window", "The selected method did not find a usable main rest interval.", "Review gaps, wear time, activity measure, and recording duration; add a diary window when available."],
          ]} />
        </Card>
        <Card title="Before submitting feedback">
          Note the affected filename, file format, selected activity measure, workflow step, request ID, and exact message. Do not include participant identifiers or raw measurements in the feedback text. A contact email is required so the team can follow up.
        </Card>
      </div>
    ),
    methods: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="pyActigraphy foundation">
          Native file readers, non-parametric activity metrics, Crespo_AoT and Roenneberg_AoT procedures, and Cosinor modelling use pyActigraphy. The application prepares the selected scalar activity series, applies the chosen preprocessing, and then calls the corresponding methods. See the <a href="https://ghammad.github.io/pyActigraphy/" target="_blank" rel="noreferrer">pyActigraphy documentation</a>, <a href="https://github.com/ghammad/pyActigraphy" target="_blank" rel="noreferrer">source code</a>, and <a href="https://doi.org/10.1371/journal.pcbi.1009514" target="_blank" rel="noreferrer">package paper</a>.
        </Card>
        <Card title="What is recorded with the analysis">
          Results retain the source file and reader, resolved activity measure and units, epoch duration, selected preprocessing thresholds, start/stop intervals, masks, valid-window decisions, sleep-window coverage, algorithms, metric parameters, application version, and quality-control messages. Missing and excluded epochs remain unavailable rather than being treated as zero activity.
        </Card>
        <Card title="Data handling and feedback">
          Uploaded recording and support files are used temporarily to complete the requested operation and are deleted after processing. Feedback requires a contact email and may include non-raw technical context such as filenames, selected settings, request IDs, and visible errors. Feedback and its attached context are retained for 30 days, then automatically deleted. Do not include participant identifiers in filenames or feedback.
        </Card>
      </div>
    ),
    terms: (
      <div style={{ display: "grid", gap: 14 }}>
        <Card title="Hosting and support">
          This web tool is hosted by the Ontario Brain Institute (OBI), with development supported through the Centre for Analytics.
        </Card>
        <TermsOfUseContent compact />
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
            <div style={{ color: "#475569", lineHeight: 1.5 }}>Searchable guidance for completing the workflow, choosing settings, understanding results, and resolving common problems.</div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center", width: "100%" }}>
            <a href={githubDocsUrl} target="_blank" rel="noreferrer" style={{ padding: "9px 13px", borderRadius: 10, border: "1px solid #cbd5e1", color: "#0f172a", textDecoration: "none", fontWeight: 700, fontSize: 13 }}>
              Open full user guide
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
            placeholder="Search the user guide"
            aria-label="Search all documentation content"
            style={{ width: "100%", boxSizing: "border-box", padding: "10px 11px", borderRadius: 9, border: "1px solid #cbd5e1", marginBottom: 7 }}
          />
          <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.4, marginBottom: 10 }}>
            Searches workflow steps, settings, file formats, metrics, results, and troubleshooting guidance.
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
            {visibleSections.length === 0 && <div style={{ color: "#64748b", fontSize: 13, padding: 8 }}>No guide content matched this search.</div>}
          </div>
        </aside>

        <main>{visibleSections.length > 0 ? sectionContent[activeSection] : null}</main>
      </div>
    </div>
  );
}
