import React from "react";

function TermSection({ title, children }) {
  return (
    <section style={{ border: "1px solid #e2e8f0", borderRadius: 14, padding: 15, background: "white" }}>
      <h3 style={{ margin: "0 0 8px", color: "#0f172a", fontSize: 17 }}>{title}</h3>
      <div style={{ color: "#475569", lineHeight: 1.65, fontSize: 14 }}>{children}</div>
    </section>
  );
}

export default function TermsOfUseContent({ compact = false }) {
  return (
    <div style={{ display: "grid", gap: 12, textAlign: "left" }}>
      {!compact && (
        <div style={{ border: "1px solid #bfdbfe", borderRadius: 14, padding: 15, background: "#eff6ff", color: "#1e3a8a", lineHeight: 1.6 }}>
          This web tool is hosted by the Ontario Brain Institute (OBI), with development supported through the CFA grant. By using the tool, you agree to the conditions below and to any applicable institutional, research-ethics, privacy, and data-governance requirements.
        </div>
      )}

      <TermSection title="Research and educational use">
        The application supports actigraphy preprocessing, quality control, analysis, visualization, and export. It is not a medical device, does not provide a diagnosis or treatment recommendation, and is not a substitute for clinical judgment. Users remain responsible for selecting methods and interpreting outputs appropriately for their study or service context.
      </TermSection>

      <TermSection title="Authority to upload and de-identification">
        Upload only data that you are authorized to process. Follow the consent, research-ethics, privacy, data-sharing, and security requirements that apply to your organization and project. Remove direct identifiers from recordings, filenames, diaries, support files, free-text feedback, and exported configurations before upload. Do not use the service for identifiable clinical records unless your approved governance explicitly permits it.
      </TermSection>

      <TermSection title="Transient processing and retention">
        Raw uploaded recording and support files are copied into a temporary processing/job area only to perform the requested operation and are deleted before the request or background job is reported as completed or failed. Job status and result JSON are transient and become eligible for cleanup after the configured job-retention period; the current code default is six hours, although the OBI deployment may configure a different period. Browser state is also temporary unless a user explicitly downloads an export or an optional authenticated run-history feature is enabled.
      </TermSection>

      <TermSection title="Technical metadata, diagnostics, and feedback">
        Operational diagnostics may retain non-raw technical information such as filenames, file sizes, selected settings, reader type, processing stages, errors, request IDs, and summary results when the deployment uses persistent application storage. Feedback is stored separately and may include the context attached to the report. Do not place participant identifiers, raw measurements, or other sensitive content in filenames or feedback text. Administrators should apply an appropriate retention and access policy to these records.
      </TermSection>

      <TermSection title="Recommended settings and scientific responsibility">
        Values labelled “recommended” are configurable starting points, not mandatory standards for every device, population, protocol, or research question. The tool records the resolved settings and processing provenance, but users are responsible for prespecifying or justifying their choices, reviewing QC findings, and reporting exclusions and sensitivity analyses accurately.
      </TermSection>

      <TermSection title="Availability, outputs, and third-party software">
        The service is provided on an as-available basis. Processing may be interrupted by upload limits, platform maintenance, capacity, networking, unsupported files, or dependency behaviour. Review outputs and diagnostics before relying on them. The application uses open-source packages, including pyActigraphy and format-specific readers, under their respective licences and citation requirements.
      </TermSection>

      <TermSection title="Acceptable use">
        Do not upload unlawful content, attempt unauthorized access, interfere with service operation, evade platform limits, or use the application in a way that compromises other users, OBI infrastructure, or research data. Access may be limited or removed when needed to protect the service or comply with legal and institutional obligations.
      </TermSection>
    </div>
  );
}
