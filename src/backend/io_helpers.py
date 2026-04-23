from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import pandas as pd
import pyActigraphy

try:
    from pyActigraphy.io import BaseRaw
except Exception:
    BaseRaw = None

READERS = {
    "agd": "read_raw_agd",
    "atr": "read_raw_atr",
    "awd": "read_raw_awd",
    "bba": "read_raw_bba",
    "dqt": "read_raw_dqt",
    "gt3x": "read_gt3x",
    "mesa": "read_raw_mesa",
    "mtn": "read_raw_mtn",
    "rpx": "read_raw_rpx",
    "tal": "read_raw_tal",
}

COMMON_TIMESTAMP_COLUMNS = [
    "Timestamp", "timestamp", "DateTime", "datetime", "time", "Time", "date_time", "DATE/TIME", "Data", "Hora"
]

COMMON_ACTIVITY_COLUMNS = [
    "VM", "vm", "activity", "Activity", "Axis1", "AxisXCounts", "activity_counts", "counts",
    "Atividade", "PIM", "TAT", "ZCM"
]

COMMON_LIGHT_COLUMNS = [
    "light", "Light", "Lux", "lux", "Illuminance", "illuminance",
    "LIGHT", "AMB LIGHT", "Luminosidade", "RED LIGHT", "GREEN LIGHT", "BLUE LIGHT",
    "IR LIGHT", "UVA LIGHT", "UVB LIGHT", "MELANOPIC_LUX", "CLEAR"
]

COMMON_TEMPERATURE_COLUMNS = [
    "temperature", "Temperature", "temp", "Temp", "TEMPERATURE", "EXT TEMPERATURE"
]

COMMON_NONWEAR_COLUMNS = [
    "nonwear", "NonWear", "mask", "Mask", "wear", "Wear"
]

PREFERRED_ACTIVITY_ORDER = ["VM", "activity", "Atividade", "PIM", "TAT", "ZCM"]
PREFERRED_LIGHT_ORDER = ["LIGHT", "AMB LIGHT", "Luminosidade", "Lux", "light", "MELANOPIC_LUX", "CLEAR"]


def infer_reader_type(file_path: str):
    suffix = Path(file_path).suffix.lower().replace(".", "")
    if suffix in READERS:
        return suffix
    if suffix in ("csv", "txt", "gz", "json", "xls", "xlsx", "ods"):
        return suffix
    raise ValueError("Unsupported file type: {}".format(suffix))


def load_native_file(file_path: str, reader_type: str):
    method_name = READERS.get(reader_type)
    if method_name is None:
        raise ValueError("Unsupported native reader type: {}".format(reader_type))

    reader = getattr(pyActigraphy.io, method_name, None)
    if reader is None:
        raise ValueError("This pyActigraphy installation does not expose '{}'.".format(method_name))

    return reader(file_path)


def _find_first_existing(columns, candidates):
    lookup = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        found = lookup.get(candidate.lower())
        if found is not None:
            return found
    return None


def _choose_preferred_column(columns: List[str], preferred_order: List[str], fallback_candidates: List[str]):
    lookup = {str(c).strip().lower(): c for c in columns}
    for name in preferred_order:
        found = lookup.get(name.lower())
        if found is not None:
            return found
    return _find_first_existing(columns, fallback_candidates)


def read_tabular_file(file_path: str, sep: Optional[str] = None) -> pd.DataFrame:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(file_path, sep=sep or ",")
    if suffix == ".txt":
        return pd.read_csv(file_path, sep=sep or ";")
    if suffix == ".gz":
        return pd.read_csv(file_path, compression="gzip")
    if suffix in (".xls", ".xlsx", ".ods"):
        return pd.read_excel(file_path)

    raise ValueError("Unsupported tabular file type: {}".format(suffix))


def detect_csv_mapping(df: pd.DataFrame) -> Dict[str, Any]:
    cols = list(df.columns)

    mapping = {
        "timestamp_col": _find_first_existing(cols, COMMON_TIMESTAMP_COLUMNS),
        "activity_col": _choose_preferred_column(cols, PREFERRED_ACTIVITY_ORDER, COMMON_ACTIVITY_COLUMNS),
        "light_col": _choose_preferred_column(cols, PREFERRED_LIGHT_ORDER, COMMON_LIGHT_COLUMNS),
        "temperature_col": _find_first_existing(cols, COMMON_TEMPERATURE_COLUMNS),
        "nonwear_col": _find_first_existing(cols, COMMON_NONWEAR_COLUMNS),
    }

    return mapping


def load_custom_tabular(
    file_path: str,
    timestamp_col: str,
    activity_col: Optional[str] = None,
    light_col: Optional[str] = None,
    temperature_col: Optional[str] = None,
    nonwear_col: Optional[str] = None,
    sep: str = ",",
):
    df = read_tabular_file(file_path, sep=sep)

    if timestamp_col not in df.columns:
        raise ValueError("Timestamp column '{}' not found.".format(timestamp_col))

    work = df.copy()

    if timestamp_col == "Data" and "Hora" in work.columns:
        work["_combined_timestamp"] = (
            work["Data"].astype(str).str.strip() + " " + work["Hora"].astype(str).str.strip()
        )
        time_source = "_combined_timestamp"
    else:
        time_source = timestamp_col

    work[time_source] = pd.to_datetime(work[time_source], errors="coerce", dayfirst=True)
    work = work.dropna(subset=[time_source]).sort_values(time_source)

    out = pd.DataFrame(index=work[time_source])

    if activity_col:
        if activity_col not in work.columns:
            raise ValueError("Activity column '{}' not found.".format(activity_col))
        out["activity"] = pd.to_numeric(work[activity_col], errors="coerce")

    if light_col:
        if light_col not in work.columns:
            raise ValueError("Light column '{}' not found.".format(light_col))
        out["light"] = pd.to_numeric(work[light_col], errors="coerce")

    if temperature_col:
        if temperature_col not in work.columns:
            raise ValueError("Temperature column '{}' not found.".format(temperature_col))
        out["temperature"] = pd.to_numeric(work[temperature_col], errors="coerce")

    if nonwear_col:
        if nonwear_col not in work.columns:
            raise ValueError("Non-wear column '{}' not found.".format(nonwear_col))
        out["nonwear"] = pd.to_numeric(work[nonwear_col], errors="coerce")

    out = out.dropna(how="all")
    return out


def load_auto_tabular(file_path: str, sep: str = ",") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = read_tabular_file(file_path, sep=sep)
    mapping = detect_csv_mapping(df)

    if not mapping.get("timestamp_col") or not mapping.get("activity_col"):
        raise ValueError(
            "Could not automatically detect timestamp/activity columns. Please use manual mapping."
        )

    return load_custom_tabular(
        file_path=file_path,
        timestamp_col=mapping["timestamp_col"],
        activity_col=mapping.get("activity_col"),
        light_col=mapping.get("light_col"),
        temperature_col=mapping.get("temperature_col"),
        nonwear_col=mapping.get("nonwear_col"),
        sep=sep,
    ), mapping


def build_baseraw_from_dataframe(
    df: pd.DataFrame,
    name: str = "Mapped File",
    uuid: str = "mapped-device",
):
    if BaseRaw is None:
        raise ValueError("BaseRaw is not available in this pyActigraphy installation.")

    if "activity" not in df.columns:
        raise ValueError("Mapped table must contain an 'activity' column before conversion to BaseRaw.")

    work = df.copy().sort_index()

    if work.index.freq is None:
        inferred = pd.infer_freq(work.index)
        if inferred is not None:
            work = work.asfreq(inferred)

    if work.index.freq is None and len(work.index) >= 2:
        delta = work.index[1] - work.index[0]
        work = work.asfreq(delta)

    if work.index.freq is None:
        raise ValueError("Could not infer recording frequency from timestamps.")

    raw = BaseRaw(
        name=name,
        uuid=uuid,
        format="Pandas",
        axial_mode=None,
        start_time=work.index[0],
        period=(work.index[-1] - work.index[0]),
        frequency=work.index.freq,
        data=work["activity"],
        light=work["light"] if "light" in work.columns else None,
    )

    if "nonwear" in work.columns:
        try:
            raw.mask = (1 - work["nonwear"].fillna(0)).clip(lower=0, upper=1)
        except Exception:
            pass

    return raw