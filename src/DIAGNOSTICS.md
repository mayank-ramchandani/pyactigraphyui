# Structured analysis diagnostics

The activity/sleep and light-analysis endpoints now return a `diagnostics` object with every success or backend-generated failure response.

## What is captured

- A unique request ID and endpoint
- Original filename, upload size, content type, and SHA-256 checksum (up to `DIAGNOSTIC_SHA256_MAX_MB`)
- Reader selected for the file and raw-object class
- Recording start/stop, row count, epoch spacing, timestamp duplicates/gaps, missing activity, zero fraction, and available light channels
- Stage runtime, current/peak memory, memory change, and temporary-disk availability
- Separate stages for upload, reader detection, loading/conversion, data validation, support-file preprocessing, sleep scoring/window detection, each metric, QC, and cleanup
- Exceptions previously suppressed by `_safe_call`, including tracebacks
- `accProcess` return code and stdout/stderr tails
- Progress events from the streaming GENEActiv `.bin` reader

The Results page displays these stages and can download either an individual diagnostic JSON file or a combined batch report.

## Important interpretation

- **passed**: the stage completed without a captured issue.
- **warning**: the request continued, but the stage returned no usable value, had no usable sleep window, or recovered from an internal exception.
- **failed**: the stage raised an exception or a metric failed after suppressed exceptions were captured.
- **completed_with_warnings**: the file returned partial/complete results, but one or more stages or light metrics need review.

An HTTP `413`, proxy timeout, or abrupt container termination can occur before FastAPI returns JSON. In that case, the browser creates a client transport diagnostic. It will not have a backend request ID. Use the HTTP status, response preview, filename/size, and Azure/Nginx logs to identify the gateway failure.

## Server logs and persistence

Each stage start/finish and GENEActiv/`accProcess` progress event is emitted as structured JSON through the `actigraphy.diagnostics` logger. This is especially useful when the container is killed during a large-file stage and no API response can be returned.

Completed diagnostic reports are also appended to:

```text
${APP_DATA_DIR:-/tmp/actigraphy-ui-data}/diagnostics.jsonl
```

The file rotates to `diagnostics.jsonl.1` after 50 MB by default.

## Optional environment variables

```text
DIAGNOSTIC_LOG_MAX_MB=50
DIAGNOSTIC_SHA256_MAX_MB=512
DIAGNOSTIC_TRACEBACK_CHARS=12000
DIAGNOSTIC_SUPPRESSED_ERROR_LIMIT=30
GENEACTIV_DIAGNOSTIC_PAGE_INTERVAL=5000
```

For Azure, set `APP_DATA_DIR` to a mounted persistent path if diagnostic history should survive container revisions. Otherwise, rely on the downloadable report and Azure log stream.
## Plain `Internal Server Error` after metrics finish

Periodic pyActigraphy metrics such as `ISp`, `IVp`, and `RAp` may return NumPy arrays or Pandas objects. Those objects must be converted before they are passed to Starlette `JSONResponse`; otherwise response construction can raise after the endpoint analysis handler has finished and the browser receives only plain-text HTTP 500.

This build converts nested NumPy/Pandas metric values to JSON-safe Python lists, dictionaries, scalars, and `null` values. It also installs a final unhandled-exception JSON handler. Container termination, reverse-proxy timeouts, and operating-system OOM kills still occur outside Python and therefore must be confirmed from Azure/container logs.

