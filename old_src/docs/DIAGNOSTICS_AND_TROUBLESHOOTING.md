# Diagnostics and troubleshooting

## Structured diagnostic report

Each backend-generated analysis response includes a per-file `diagnostics` object. The Results page can display and download the report.

Captured information includes:

- request ID and endpoint;
- filename, extension, content type, size, and optional SHA-256;
- reader and raw-object class;
- recording dates, epochs, gaps, duplicates, missingness, zero fraction, and channels;
- requested and resolved activity mapping;
- stage runtime, memory, and temporary-disk information;
- suppressed exceptions and tracebacks;
- converter command, return code, and stdout/stderr tails;
- QC warnings and cleanup results.

## Status meanings

| Status | Meaning |
|---|---|
| `passed` | Stage completed normally. |
| `warning` | Processing continued but returned no usable value/window or recovered from an issue. |
| `failed` | Stage raised an exception or produced an invalid result. |
| `skipped` | A prerequisite or supported method was unavailable. |
| `completed_with_warnings` | Results were returned, but at least one stage requires review. |

Quality control is non-fatal. A QC implementation error should be captured without discarding successful metric calculations.

## Live progress

The frontend supplies a request ID and polls:

```text
GET /api/progress/{request_id}
```

Progress can include:

- browser upload bytes;
- current backend stage and human-readable detail;
- current stage number and total;
- overall and current-file percentage;
- GENEActiv pages and samples decoded.

The percentage represents pipeline completion, not estimated time remaining. A long raw-decoding stage can dominate elapsed time.

Progress records are stored under:

```text
${APP_DATA_DIR:-/tmp/actigraphy-ui-data}/progress/
```

In a multi-replica deployment, use shared storage, one replica, or sticky routing so the polling request can locate the same progress record.

## Common failures

### HTTP 413

The upload was rejected before FastAPI processed it. Check every proxy/ingress layer, not only application code:

- Nginx `client_max_body_size`;
- Azure ingress limits;
- upstream gateway limits;
- frontend host/proxy limits.

### Plain-text HTTP 500

Ordinary Python exceptions should be converted to JSON. A plain `Internal Server Error` after that safeguard may indicate:

- worker/container termination;
- memory pressure;
- process restart;
- reverse-proxy failure;
- an exception before the application handler is reached.

Inspect Azure/container logs using the request time and filename.

### Exit code 137 or abrupt restart

Commonly associated with an operating-system or container memory kill. Python cannot return a structured traceback after the process is terminated.

### HTML returned instead of JSON

Usually an Nginx, ingress, hosting, timeout, or platform error page. Capture HTTP status, content type, and the first portion of the response body.

### Metric returns `null`

Review the metric stage and suppressed exceptions. The metric can be unsupported for the raw-object type, require more days, require sleep windows, or have returned a non-scalar value that failed validation.

### RA equals 1

Review `ra_components`. A zero L5 with positive M10 produces RA = 1. Compare continuous and binarized results and verify the threshold scale.

### Crespo/Roenneberg detects no windows

Review gaps, wear, duration, activity basis, units, resampling, thresholds, and detected onset/offset arrays. A no-window result is not proof that no sleep occurred.

## Persistent logs

Completed reports are appended to:

```text
${APP_DATA_DIR:-/tmp/actigraphy-ui-data}/diagnostics.jsonl
```

Relevant environment variables include:

```text
DIAGNOSTIC_LOG_MAX_MB=50
DIAGNOSTIC_SHA256_MAX_MB=512
DIAGNOSTIC_TRACEBACK_CHARS=12000
DIAGNOSTIC_SUPPRESSED_ERROR_LIMIT=30
GENEACTIV_DIAGNOSTIC_PAGE_INTERVAL=5000
ANALYSIS_PROGRESS_TTL_SECONDS=21600
```
