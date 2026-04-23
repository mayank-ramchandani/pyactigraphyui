from pathlib import Path
from typing import Optional

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


def infer_reader_type(file_path: str):
    suffix = Path(file_path).suffix.lower().replace(".", "")
    if suffix in READERS:
      return suffix
    if suffix == "csv":
      return "csv"
    raise ValueError(f"Unsupported file type: {suffix}")


def load_native_file(file_path: str, reader_type: str):
    method_name = READERS.get(reader_type)
    if method_name is None:
        raise ValueError(f"Unsupported reader type: {reader_type}")

    if reader_type == "gt3x":
        reader = getattr(pyActigraphy.io, "read_gt3x", None)
        if reader is None:
            raise ValueError("This pyActigraphy installation does not expose 'read_gt3x'.")
        return reader(file_path)

    reader = getattr(pyActigraphy.io, method_name, None)
    if reader is None:
        raise ValueError(f"This pyActigraphy installation does not expose '{method_name}'.")

    return reader(file_path)


def read_csv_columns(file_path: str, sep: str = ","):
    df = pd.read_csv(file_path, sep=sep, nrows=5)
    return list(df.columns)


def validate_csv_file(file_path: str):
    return pd.read_csv(file_path)


def validate_custom_csv_file(file_path: str, sep: str = ","):
    return pd.read_csv(file_path, sep=sep)


def load_custom_csv(
    file_path: str,
    timestamp_col: str = "Timestamp",
    activity_col: Optional[str] = None,
    light_col: Optional[str] = None,
    temperature_col: Optional[str] = None,
    nonwear_col: Optional[str] = None,
    sep: str = ",",
):
    df = pd.read_csv(file_path, sep=sep)

    if timestamp_col not in df.columns:
        raise ValueError(f"Timestamp column '{timestamp_col}' not found in CSV.")

    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df.dropna(subset=[timestamp_col]).sort_values(timestamp_col)

    out = pd.DataFrame(index=df[timestamp_col])

    if activity_col:
        if activity_col not in df.columns:
            raise ValueError(f"Activity column '{activity_col}' not found in CSV.")
        out["activity"] = pd.to_numeric(df[activity_col], errors="coerce")

    if light_col:
        if light_col not in df.columns:
            raise ValueError(f"Light column '{light_col}' not found in CSV.")
        out["light"] = pd.to_numeric(df[light_col], errors="coerce")

    if temperature_col:
        if temperature_col not in df.columns:
            raise ValueError(f"Temperature column '{temperature_col}' not found in CSV.")
        out["temperature"] = pd.to_numeric(df[temperature_col], errors="coerce")

    if nonwear_col:
        if nonwear_col not in df.columns:
            raise ValueError(f"Non-wear column '{nonwear_col}' not found in CSV.")
        out["nonwear"] = pd.to_numeric(df[nonwear_col], errors="coerce")

    out = out.dropna(how="all")

    return out


def build_baseraw_from_dataframe(
    df: pd.DataFrame,
    name: str = "Mapped CSV",
    uuid: str = "csv-device",
):
    if BaseRaw is None:
        raise ValueError("BaseRaw is not available in this pyActigraphy installation.")

    if "activity" not in df.columns:
        raise ValueError("Mapped CSV must contain an 'activity' column before conversion to BaseRaw.")

    work = df.copy()
    work = work.sort_index()

    if work.index.freq is None:
        inferred = pd.infer_freq(work.index)
        if inferred is None:
            if len(work.index) < 2:
                raise ValueError("Could not infer recording frequency from CSV timestamps.")
            inferred = work.index[1] - work.index[0]
        work = work.asfreq(inferred)

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
        raw.mask = (1 - work["nonwear"].fillna(0)).clip(lower=0, upper=1)

    return raw


def load_selected_actigraphy_file(file_path: str):
    reader_type = infer_reader_type(file_path)
    if reader_type == "csv":
        return validate_custom_csv_file(file_path)
    return load_native_file(file_path, reader_type)