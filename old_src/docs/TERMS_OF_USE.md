# Terms of use

## Hosting and funding

This web tool is hosted by the **Ontario Brain Institute (OBI)**, with development supported through the **Centre for Analytics**. Use of the service is subject to applicable OBI, institutional, research-ethics, privacy, data-governance, and legal requirements.

## Research and educational purpose

The application supports actigraphy preprocessing, quality control, analysis, visualization, and export. It is not a medical device, does not provide a diagnosis or treatment recommendation, and is not a substitute for clinical judgment. Users are responsible for choosing methods and interpreting outputs appropriately for their protocol and population.

## Authority to upload and de-identification

Upload only data that you are authorized to process. Remove direct identifiers from recordings, filenames, diaries, support files, feedback, and exported configurations. Do not upload identifiable clinical records unless an approved governance process explicitly permits their use in this service.

## Transient raw-file processing

Raw uploaded recordings and support files are copied into a temporary processing/job area only to perform the requested operation. Those input files are deleted before the request or background job is reported as completed or failed.

Job status and result JSON are also transient and become eligible for cleanup after the configured job-retention period. The current code default is six hours (`ANALYSIS_JOB_TTL_SECONDS=21600`), although the deployed service may configure a different period. Browser state is temporary unless the user downloads an export or an optional authenticated run-history feature is enabled.

## Diagnostics and feedback metadata

Operational diagnostics may retain non-raw technical metadata such as filenames, sizes, selected settings, reader type, processing stages, errors, request IDs, and summary results when persistent application storage is configured. Feedback is stored separately and may include the technical context attached to a report. A contact email address is required so the Centre for Analytics team can follow up about the submission. Feedback, the contact email address, and attached technical context are retained for **30 days from submission** and then automatically deleted. Do not place participant identifiers, raw measurements, or other sensitive content in filenames or feedback text.

## Recommended settings and scientific responsibility

Values labelled **recommended** are configurable starting points, not mandatory standards for every device, population, protocol, or research question. The application records the resolved settings and processing provenance. Users remain responsible for prespecifying or justifying their choices, reviewing QC findings, and accurately reporting exclusions and sensitivity analyses.

## Availability and outputs

The service is provided on an as-available basis. Processing may be interrupted by upload limits, platform maintenance, capacity, networking, unsupported files, or dependency behaviour. Users should review outputs and diagnostics before relying on them.

## Third-party software

The application uses open-source packages, including pyActigraphy and format-specific readers, under their respective licences and citation requirements.

## Acceptable use

Do not upload unlawful content, attempt unauthorized access, interfere with service operation, evade platform limits, or use the application in a way that compromises other users, OBI infrastructure, or research data. Access may be limited or removed when needed to protect the service or comply with legal and institutional obligations.
