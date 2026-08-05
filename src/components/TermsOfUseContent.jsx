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
          This web tool is hosted by the Ontario Brain Institute (OBI), with development supported through the Centre for Analytics. By using the tool, you agree to the conditions below and to any applicable institutional, research-ethics, privacy, and data-governance requirements.
        </div>
      )}

      <TermSection title="Research and educational use">
        The application supports actigraphy preprocessing, quality control, analysis, visualization, and export. It is not a medical device, does not provide a diagnosis or treatment recommendation, and is not a substitute for clinical judgment. Users remain responsible for choosing methods and interpreting outputs appropriately for their study or service context.
      </TermSection>

      <TermSection title="Authority to upload and de-identification">
        Upload only data that you are authorized to process. Follow the consent, research-ethics, privacy, data-sharing, and security requirements that apply to your organization and project. Remove direct identifiers from recordings, filenames, diaries, support files, free-text feedback, and exported configurations before upload.
      </TermSection>

      <TermSection title="Temporary processing">
        Uploaded recording and support files are used temporarily to complete the requested preview or analysis and are deleted after processing. Processing status and result data are also temporary. Download any outputs that you need to retain.
      </TermSection>

      <TermSection title="Technical context and feedback">
        Feedback may include non-raw technical information such as filenames, file sizes, selected settings, processing stages, errors, request IDs, and summary results. A contact email address is required so the Centre for Analytics team can follow up. Feedback, the email address, and attached technical context are retained for 30 days from submission and then automatically deleted. Do not include participant identifiers, raw measurements, or other sensitive information in filenames or feedback text.
      </TermSection>

      <TermSection title="Recommended settings and scientific responsibility">
        Values labelled “recommended” are configurable starting points, not mandatory standards for every device, population, protocol, or research question. Users are responsible for prespecifying or justifying their choices, reviewing quality-control findings, and reporting exclusions and sensitivity analyses accurately.
      </TermSection>

      <TermSection title="Availability, outputs, and third-party software">
        The service is provided on an as-available basis. Processing may be interrupted by upload limits, maintenance, capacity, networking, unsupported files, or dependency behaviour. Review outputs and diagnostics before relying on them. The application uses open-source packages, including pyActigraphy and format-specific readers, under their respective licences and citation requirements.
      </TermSection>

      <TermSection title="Acceptable use">
        Do not upload unlawful content, attempt unauthorized access, interfere with service operation, evade platform limits, or use the application in a way that compromises other users, OBI infrastructure, or research data. Access may be limited or removed when needed to protect the service or comply with legal and institutional obligations.
      </TermSection>
    </div>
  );
}
