"""Shared activity-basis helpers for actigraphy and raw accelerometer inputs.

The recommended ``auto`` mode keeps a device/source activity series when the
file already contains one, and uses an epoch-level accelerometer ``acc`` series
for raw tri-axial inputs.  ``mad`` and the legacy/custom ``enmo`` calculation
remain available as explicit alternatives.
"""

from __future__ import annotations

from typing import Any, Dict


ACTIVITY_MAPPING_OPTIONS: Dict[str, Dict[str, Any]] = {
    "auto": {
        "label": "Recommended source / processed `acc`",
        "units": None,
        "description": (
            "Use the file's source/device activity when it exists; otherwise use the "
            "epoch-level accelerometer-processed `acc` signal for raw X/Y/Z recordings."
        ),
    },
    "accelerometer": {
        "label": "Processed acceleration (`acc` basis)",
        "units": "mg",
        "description": (
            "Use the Oxford accelerometer `acc` column when available, or the memory-safe "
            "compatible processed-acceleration path for supported raw recordings."
        ),
    },
    "original": {
        "label": "Source / device activity",
        "units": None,
        "description": "Use an activity/count series already supplied by the file or native reader.",
    },
    "mad": {
        "label": "MAD",
        "units": "mg",
        "description": "Mean amplitude deviation of vector magnitude within each epoch.",
    },
    "enmo": {
        "label": "Custom ENMO (legacy)",
        "units": "mg",
        "description": "Direct Euclidean Norm Minus One calculation retained for comparison and backwards compatibility.",
    },
}


_ALIASES = {
    "": "auto",
    "default": "auto",
    "recommended": "auto",
    "automatic": "auto",
    "source_or_acc": "auto",
    "native": "original",
    "device": "original",
    "device_activity": "original",
    "original_activity": "original",
    "acc": "accelerometer",
    "processed_acc": "accelerometer",
    "accelerometer_acc": "accelerometer",
    "accelerometer_processed": "accelerometer",
    "enmo_mg": "enmo",
    "euclidean_norm_minus_one": "enmo",
    "mean_amplitude_deviation": "mad",
    "mad_mg": "mad",
}


def normalize_activity_mapping(value: Any) -> str:
    text = str(value or "auto").strip().lower()
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
    """Attach activity-basis details to pyActigraphy and lightweight raw objects."""
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
        return mapping_metadata("auto", "original")
