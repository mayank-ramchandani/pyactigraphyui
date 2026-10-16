/**
 * Availability gate for optional high-frequency raw X/Y/Z preprocessing.
 *
 * The settings are global across an analysis, so *every* uploaded actigraphy
 * recording must be eligible (including when the user joins recordings).
 * Extension checks keep the UI safe; the backend also checks the file content
 * and only accepts GENEActiv BIN rather than other manufacturers' .bin files.
 */
export function getRawSignalFileEligibility(files = []) {
  const recordings = Array.isArray(files) ? files : [];
  const unsupported = recordings.filter((file) => {
    const name = String(file?.name || "").trim().toLowerCase();
    return !name.endsWith(".gt3x") && !name.endsWith(".bin");
  });
  if (recordings.length === 0) {
    return {
      eligible: false,
      reason: "Upload a native .gt3x or GENEActiv .bin activity recording in Step 1 to enable custom raw preprocessing.",
      unsupportedNames: [],
    };
  }
  if (unsupported.length) {
    const names = unsupported.map((file) => String(file?.name || "Unnamed recording"));
    return {
      eligible: false,
      reason: unsupported.length === recordings.length
        ? "Custom raw preprocessing is unavailable for the uploaded file format. Only native .gt3x and GENEActiv .bin recordings are supported."
        : "Custom raw preprocessing requires every uploaded actigraphy recording to be a native .gt3x or GENEActiv .bin file. Remove unsupported files or analyze the raw recordings separately.",
      unsupportedNames: names,
    };
  }
  return { eligible: true, reason: "", unsupportedNames: [] };
}
