"""Shared activity-mapping helpers for raw accelerometer inputs.

The UI exposes three choices:

- ``original``: preserve the file/device's existing activity representation.
- ``enmo``: Euclidean Norm Minus One, averaged per epoch and reported in mg.
- ``mad``: mean amplitude deviation of vector magnitude per epoch, reported in mg.

ENMO and MAD require calibrated tri-axial acceleration, except when an uploaded
preprocessed time-series already contains the requested mapping as a column.
"""

from __future__ import annotations

from typing import Any, Dict


ACTIVITY_MAPPING_OPTIONS: Dict[str, Dict[str, Any]] = {
    "original": {
        "label": "Original / device activity",
        "units": None,
        "description": "Use the activity signal already provided by the file or its native reader.",
    },
    "enmo": {
        "label": "ENMO",
        "units": "mg",
        "description": "Euclidean Norm Minus One: max(sqrt(x²+y²+z²) - 1 g, 0), averaged within each epoch.",
    },
    "mad": {
        "label": "MAD",
        "units": "mg",
        "description": "Mean amplitude deviation of vector magnitude within each epoch.",
    },
}


_ALIASES = {
    "": "original",
    "default": "original",
    "native": "original",
    "device": "original",
    "device_activity": "original",
    "original_activity": "original",
    "enmo_mg": "enmo",
    "euclidean_norm_minus_one": "enmo",
    "mean_amplitude_deviation": "mad",
    "mad_mg": "mad",
}


def normalize_activity_mapping(value: Any) -> str:
    text = str(value or "original").strip().lower()
    text = _ALIASES.get(text, text)
    if text not in ACTIVITY_MAPPING_OPTIONS:
        supported = ", ".join(ACTIVITY_MAPPING_OPTIONS)
        raise ValueError(f"Unsupported activity mapping '{value}'. Supported values: {supported}.")
    return text


def mapping_metadata(requested: Any, resolved: str | None = None, **extra: Any) -> Dict[str, Any]:
    requested_norm = normalize_activity_mapping(requested)
    resolved_norm = normalize_activity_mapping(resolved or requested_norm)
    option = ACTIVITY_MAPPING_OPTIONS[resolved_norm]
    payload: Dict[str, Any] = {
        "requested": requested_norm,
        "resolved": resolved_norm,
        "label": option["label"],
        "units": option.get("units"),
        "description": option.get("description"),
    }
    payload.update(extra)
    return payload


def attach_mapping_metadata(raw: Any, metadata: Dict[str, Any]) -> Any:
    """Attach mapping details to pyActigraphy and lightweight raw objects."""
    try:
        raw._ui_activity_mapping = metadata.get("resolved")
        raw._ui_activity_mapping_requested = metadata.get("requested")
        raw._ui_activity_units = metadata.get("units")
        raw._ui_activity_mapping_metadata = metadata
    except Exception:
        pass

    existing = getattr(raw, "metadata", None)
    if isinstance(existing, dict):
        existing["activity_mapping"] = metadata
    return raw


def raw_mapping_metadata(raw: Any) -> Dict[str, Any]:
    details = getattr(raw, "_ui_activity_mapping_metadata", None)
    if isinstance(details, dict):
        return details

    metadata = getattr(raw, "metadata", None)
    if isinstance(metadata, dict) and isinstance(metadata.get("activity_mapping"), dict):
        return metadata["activity_mapping"]

    resolved = getattr(raw, "_ui_activity_mapping", None) or "original"
    requested = getattr(raw, "_ui_activity_mapping_requested", None) or resolved
    try:
        return mapping_metadata(requested, resolved)
    except Exception:
        return mapping_metadata("original", "original")
