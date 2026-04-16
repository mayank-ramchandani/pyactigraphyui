from pathlib import Path

import pandas as pd
import pyActigraphy

REQUIRED_CSV_COLUMNS = [
    "subject_id",
    "Date",
    "Time",
    "Timestamp",
    "AxisXCounts",
    "AxisYCounts",
    "AxisZCounts",
    "VM",
]

READERS = {
    "agd": "read_raw_agd",
    "atr": "read_raw_atr",
    "awd": "read_raw_awd",
    "bba": "read_raw_bba",
    "dqt": "read_raw_dqt",
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

    reader = getattr(pyActigraphy.io, method_name, None)
    if reader is None:
        raise ValueError(f"This pyActigraphy installation does not expose '{method_name}'.")

    return reader(file_path)


def validate_csv_file(file_path: str):
    df = pd.read_csv(file_path)

    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required CSV columns: {', '.join(missing)}")

    if list(df.columns[: len(REQUIRED_CSV_COLUMNS)]) != REQUIRED_CSV_COLUMNS:
        raise ValueError(
            "CSV columns are not in the expected order. "
            f"Expected beginning columns: {', '.join(REQUIRED_CSV_COLUMNS)}"
        )

    return df


def validate_custom_csv_file(file_path: str, sep: str = ","):
    df = pd.read_csv(file_path, sep=sep)
    missing = [column for column in REQUIRED_CSV_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"CSV file is missing required columns: {', '.join(missing)}")

    expected_prefix = list(df.columns[: len(REQUIRED_CSV_COLUMNS)])
    if expected_prefix != REQUIRED_CSV_COLUMNS:
        raise ValueError(
            "CSV columns are not in the expected order. Expected prefix: "
            + ", ".join(REQUIRED_CSV_COLUMNS)
        )

    return df


def load_custom_csv(
    file_path: str,
    timestamp_col: str = "Timestamp",
    activity_col: str | None = None,
    light_col: str | None = None,
    temperature_col: str | None = None,
    sep: str = ",",
):
    df = validate_custom_csv_file(file_path, sep=sep)
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df.dropna(subset=[timestamp_col]).sort_values(timestamp_col)

    out = pd.DataFrame(index=df[timestamp_col])

    if activity_col:
        out["activity"] = pd.to_numeric(df[activity_col], errors="coerce")
    if light_col and light_col in df.columns:
        out["light"] = pd.to_numeric(df[light_col], errors="coerce")
    if temperature_col and temperature_col in df.columns:
        out["temperature"] = pd.to_numeric(df[temperature_col], errors="coerce")

    return out


def load_selected_actigraphy_file(file_path: str):
    reader_type = infer_reader_type(file_path)
    if reader_type == "csv":
        return validate_custom_csv_file(file_path)
    return load_native_file(file_path, reader_type)
