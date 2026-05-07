def quick_qc(metrics: dict):
    warnings = []

    sri = metrics.get("sri")
    if sri is not None and not (0 <= sri <= 100):
        warnings.append("SRI is outside the expected 0-100 range.")

    ra = metrics.get("ra")
    if ra is not None and not (0 <= ra <= 1):
        warnings.append("RA is outside the expected 0-1 range.")

    sleep_efficiency = metrics.get("sleep_efficiency")
    if sleep_efficiency is not None and not (0 <= sleep_efficiency <= 100):
        warnings.append("Sleep Efficiency is outside the expected 0-100 range.")

    if metrics.get("kra") is None and "kra" in metrics:
        warnings.append("kRA could not be computed with the current file or settings.")

    if metrics.get("kar") is None and "kar" in metrics:
        warnings.append("kAR could not be computed with the current file or settings.")

    for metric_id in ["isp", "ivp", "rap"]:
        if metric_id in metrics and metrics.get(metric_id) == []:
            warnings.append(f"{metric_id.upper()} returned an empty list; the recording may be too short for the selected period.")

    return warnings