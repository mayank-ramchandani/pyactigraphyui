#!/usr/bin/env Rscript
# Run GGIR separately by part so timing includes its actual on-disk milestones.
# Usage: Rscript run_ggir_benchmark.R FILE OUTPUT_DIR PARTS TIMEZONE CALIBRATION
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 5L) stop("Expected: file output_dir parts timezone calibration_true_false")
if (!requireNamespace("GGIR", quietly = TRUE)) stop("Install GGIR first: install.packages('GGIR')")
input <- normalizePath(args[[1]], mustWork = TRUE)
output <- normalizePath(args[[2]], mustWork = FALSE)
dir.create(output, recursive = TRUE, showWarnings = FALSE)
parts <- as.integer(strsplit(args[[3]], ",", fixed = TRUE)[[1]])
if (anyNA(parts) || !identical(parts, seq_len(max(parts))) || any(!parts %in% 1:6)) {
  stop("Parts must be sequential starting at 1, e.g. 1,2 or 1,2,3,4,5")
}
zone <- args[[4]]
calibrate <- identical(tolower(args[[5]]), "true")
record <- list()
for (part in parts) {
  start <- proc.time()[["elapsed"]]
  error <- NULL
  tryCatch(
    GGIR::GGIR(
      mode = part,
      datadir = input,
      outputdir = output,
      studyname = "actilab_benchmark",
      overwrite = FALSE,
      do.parallel = FALSE,
      windowsizes = c(5, 900, 3600),
      do.enmo = TRUE,
      do.cal = calibrate,
      desiredtz = zone,
      do.report = if (part == 2L) 2 else c(),
      print.filename = FALSE
    ),
    error = function(e) { error <<- conditionMessage(e) }
  )
  elapsed <- proc.time()[["elapsed"]] - start
  record[[length(record) + 1L]] <- data.frame(
    tool = "GGIR", operation = paste0("part_", part), seconds = elapsed,
    success = is.null(error), message = if (is.null(error)) "" else error,
    stringsAsFactors = FALSE
  )
  write.csv(do.call(rbind, record), file.path(output, "ggir_timing.csv"), row.names = FALSE)
  if (!is.null(error)) stop(sprintf("GGIR part %d failed: %s", part, error))
}
writeLines(
  c(paste0("GGIR_version=", as.character(utils::packageVersion("GGIR"))),
    paste0("R_version=", R.version.string),
    paste0("parts=", args[[3]]), paste0("timezone=", zone),
    paste0("do.cal=", calibrate), "windowsizes=5,900,3600",
    "Part 1 and 2 report/processing is not identical to ActiLab Step 2 QC."),
  file.path(output, "ggir_configuration.txt")
)
