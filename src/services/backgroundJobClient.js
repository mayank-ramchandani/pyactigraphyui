function makeJobId(prefix = "job") {
  try {
    return crypto.randomUUID();
  } catch (_error) {
    return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

async function readJsonResponse(response) {
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (_error) {
    const error = new Error(
      `The server returned a non-JSON response (${response.status}). ` +
        "The upload may have timed out or the backend may have restarted."
    );
    error.httpStatus = response.status;
    throw error;
  }
  return payload;
}

function resultError(payload, fallback, status = null) {
  const error = new Error(payload?.detail || fallback);
  error.httpStatus = status;
  return error;
}

async function waitForJob(statusUrl, acceptedRuntime, onUpdate) {
  const startedAt = Date.now();
  const maxWaitMs = 6 * 60 * 60 * 1000;
  const missingGraceMs = 60 * 1000;
  let consecutiveTransportErrors = 0;

  while (Date.now() - startedAt < maxWaitMs) {
    try {
      const response = await fetch(statusUrl, {
        cache: "no-store",
        credentials: "include",
      });
      const payload = await readJsonResponse(response);

      if (!response.ok) {
        if (
          response.status === 404 &&
          payload?.code === "background_job_not_found" &&
          Date.now() - startedAt < missingGraceMs
        ) {
          await new Promise((resolve) => window.setTimeout(resolve, 1000));
          continue;
        }
        if (response.status === 404 && payload?.code === "background_job_not_found") {
          const accepted = acceptedRuntime || {};
          const polled = payload?.runtime || {};
          const acceptedAt = [accepted.revision, accepted.replica].filter(Boolean).join(" / ");
          const polledAt = [polled.revision, polled.replica].filter(Boolean).join(" / ");
          const routing =
            acceptedAt || polledAt
              ? ` Upload accepted by ${acceptedAt || "an unknown instance"}; polling reached ${polledAt || "an unknown instance"}.`
              : "";
          const error = resultError(
            payload,
            `Background job state was lost or is stored on another backend replica.${routing}`,
            response.status
          );
          error.backgroundJobTerminal = true;
          throw error;
        }
        throw resultError(payload, "Could not read background job status.", response.status);
      }

      consecutiveTransportErrors = 0;
      if (typeof onUpdate === "function") onUpdate(payload);

      if (payload.status === "completed") {
        const resultStatus = Number(payload.result_http_status || 200);
        const result = payload.result || {};
        if (resultStatus < 200 || resultStatus >= 400) {
          const error = resultError(result, "Background light processing returned an error.", resultStatus);
          error.backgroundJobTerminal = true;
          throw error;
        }
        return result;
      }

      if (payload.status === "failed") {
        const error = resultError(
          payload.result || {},
          payload.message || "Background light processing failed.",
          Number(payload.result_http_status || 500)
        );
        error.backgroundJobTerminal = true;
        throw error;
      }
    } catch (error) {
      const status = Number(error?.httpStatus || 0);
      if (error?.backgroundJobTerminal || (status >= 400 && status < 500)) throw error;
      consecutiveTransportErrors += 1;
      if (consecutiveTransportErrors >= 8) throw error;
    }

    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }

  throw new Error("Background light processing exceeded the six-hour wait limit.");
}

export async function runBackgroundFileJob({
  startUrl,
  statusBaseUrl,
  file,
  fields = {},
  jobPrefix = "light",
  onUpdate = null,
}) {
  const jobId = makeJobId(jobPrefix);
  const formData = new FormData();
  formData.append("file", file);
  formData.append("jobId", jobId);
  Object.entries(fields || {}).forEach(([key, value]) => {
    if (value != null) formData.append(key, String(value));
  });

  let startResponse;
  try {
    startResponse = await fetch(startUrl, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    const startPayload = await readJsonResponse(startResponse);
    if (!startResponse.ok) {
      throw resultError(startPayload, "Could not start background light processing.", startResponse.status);
    }
    const resolvedJobId = startPayload.job_id || jobId;
    return await waitForJob(
      `${statusBaseUrl}/${encodeURIComponent(resolvedJobId)}`,
      startPayload.runtime || null,
      onUpdate
    );
  } catch (error) {
    if ([503, 504].includes(Number(error?.httpStatus))) {
      return waitForJob(
        `${statusBaseUrl}/${encodeURIComponent(jobId)}`,
        null,
        onUpdate
      );
    }
    throw error;
  }
}
