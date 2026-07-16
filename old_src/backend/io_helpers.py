from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import csv

import pandas as pd
import pyActigraphy

from .activity_mapping import attach_mapping_metadata, mapping_metadata, normalize_activity_mapping
from .accelerometer_loader import (
    load_accelerometer_as_baseraw,
    load_accelerometer_csv_as_baseraw,
    looks_like_accelerometer_timeseries_file,
)
from .gt3x_loader import load_gt3x_as_baseraw
from .geneactiv_bin import looks_like_geneactiv_bin, read_raw_geneactiv_bin

try:
    from pyActigraphy.io import BaseRaw
except Exception:
    BaseRaw = None

READERS = {
    "agd": "read_raw_agd",
    "atr": "read_raw_atr",
    "awd": "read_raw_awd",
    "bba": "read_raw_bba",
    "bin": "read_raw_bba",
    "dqt": "read_raw_dqt",
    "mesa": "read_raw_mesa",
    "mtn": "read_raw_mtn",
    "rpx": "read_raw_rpx",
    "tal": "read_raw_tal",
}

COMMON_TIMESTAMP_COLUMNS = [
    "DATE/TIME",
    "Timestamp",
    "timestamp",
    "DateTime",
    "datetime",
    "time",
    "Time",
    "date_time",
    "Data",
    "Hora",
    "Date",
    "DATE",
    "Datum",
    "Zeit",
]

COMMON_ACTIVITY_COLUMNS = [
    "PIM",
    "TAT",
    "ZCM",
    "VM",
    "vm",
    "activity",
    "Activity",
    "Axis1",
    "AxisXCounts",
    "activity_counts",
    "counts",
    "Atividade",
    "Activity Marker",
    "Aktivität",
]

COMMON_LIGHT_COLUMNS = [
    "LIGHT",
    "AMB LIGHT",
    "Luminosidade",
    "Lux",
    "light",
    "Light",
    "lux",
    "Illuminance",
    "illuminance",
    "RED LIGHT",
    "GREEN LIGHT",
    "BLUE LIGHT",
    "IR LIGHT",
    "UVA LIGHT",
    "UVB LIGHT",
    "MELANOPIC_LUX",
    "CLEAR",
    "whitelight",
    "Weißes Licht",
]

COMMON_TEMPERATURE_COLUMNS = [
    "temperature",
    "Temperature",
    "temp",
    "Temp",
    "TEMPERATURE",
    "EXT TEMPERATURE",
]

COMMON_NONWEAR_COLUMNS = [
    "nonwear",
    "NonWear",
    "mask",
    "Mask",
    "wear",
    "Wear",
    "offwrist",
    "Status „Nicht am Handgelenk“",
]

PREFERRED_ACTIVITY_ORDER = [
    "PIM",
    "TAT",
    "ZCM",
    "Atividade",
    "Activity",
    "activity",
    "VM",
    "Axis1",
    "Aktivität",
]

PREFERRED_LIGHT_ORDER = [
    "LIGHT",
    "AMB LIGHT",
    "Luminosidade",
    "Lux",
    "light",
    "Weißes Licht",
    "whitelight",
    "MELANOPIC_LUX",
    "CLEAR",
]

COMMON_SEPARATORS = [",", ";", "\t", "|"]


def _read_text_head(file_path: str, n_chars: int = 20000) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(n_chars)


def infer_reader_type(file_path: str):
    path = Path(file_path)
    name = path.name.lower()
    suffix = path.suffix.lower().replace(".", "")

    # Handle compound compressed names before looking only at the final suffix.
    # Path("sample-timeSeries.csv.gz").suffix is just ".gz", so the old code
    # treated uploaded Oxford outputs as generic tabular files.
    if name.endswith((".bin", ".bin.gz")):
        try:
            if looks_like_geneactiv_bin(file_path):
                return "geneactiv_bin_accelerometer"
        except Exception:
            pass
        return "raw_accelerometer_needs_conversion"

    if name.endswith((".cwa", ".cwa.gz")):
        return "raw_accelerometer_needs_conversion"

    if name.endswith((".csv.gz", ".txt.gz")):
        try:
            if looks_like_accelerometer_timeseries_file(file_path):
                return "accelerometer_timeseries_csv"
        except Exception:
            pass
        return "tabular"

    if suffix in ("awd", "agd", "atr", "bba", "dqt", "gt3x", "mesa", "mtn", "rpx", "tal"):
        return suffix

    if suffix in ("csv", "txt"):
        head = _read_text_head(file_path).lower()

        if "actiware export file" in head or "actiware-exportdatei" in head or "fichier d'exportation actiware" in head:
            return "rpx"

        if "serial number:" in head and "sample rate:" in head and "store rate:" in head:
            return "dqt"

        if "luminosidade" in head and "atividade" in head and ("data; hora;" in head or "data;hora;" in head):
            return "tal"

        if "mesaid,line,linetime" in head:
            return "mesa"

        if "date/time" in head and "pim" in head and "zcm" in head:
            return "atr"

        # Oxford accelerometer output from accProcess, recommended for larger .bin/.cwa files.
        # Try the real parser even when the text-head heuristic is inconclusive.
        try:
            if looks_like_accelerometer_timeseries_file(file_path):
                return "accelerometer_timeseries_csv"
        except Exception:
            pass

        return "tabular"

    if suffix in ("xls", "xlsx", "ods"):
        return "tabular"

    raise ValueError(
        "Unsupported file type: {}. Supported native formats include .agd, .atr, .awd, .bba, .bin, .cwa, .dqt, .gt3x, .mesa, .mtn, .rpx, .tal, plus supported tabular files.".format(suffix)
    )



class SimpleRawPreview:
    def __init__(self, data, format_name="ActiGraph GT3X raw preview"):
        self.data = data
        self.format = format_name


def _unwrap_pyactigraphy_reader(reader_result):
    if hasattr(reader_result, "readers") and len(reader_result.readers) > 0:
        return reader_result.readers[0]

    if isinstance(reader_result, (list, tuple)) and len(reader_result) > 0:
        return reader_result[0]

    return reader_result

class SimpleRawPreview:
    def __init__(self, data, format_name="ActiGraph GT3X raw preview"):
        self.data = data
        self.format = format_name


def _get_nested_attr(obj, attr_names):
    for attr_name in attr_names:
        current = obj
        ok = True
        for part in attr_name.split("."):
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                ok = False
                break
        if ok and current is not None:
            return current
    return None


def _coerce_numeric_sample_rate(value, fallback=30.0):
    if value is None:
        return fallback
    try:
        if isinstance(value, str):
            value = value.lower().replace("hz", "").replace("sample_rate", "").strip()
        rate = float(value)
        if rate > 0:
            return rate
    except Exception:
        pass
    return fallback


def _make_gt3x_datetime_index(n_rows, start_time=None, sample_rate=None):
    start = pd.to_datetime(start_time, errors="coerce") if start_time is not None else pd.NaT
    if pd.isna(start):
        start = pd.Timestamp("2000-01-01 00:00:00")

    rate = _coerce_numeric_sample_rate(sample_rate, fallback=30.0)
    step_ns = int(1_000_000_000 / rate)
    return pd.date_range(start=start, periods=n_rows, freq=pd.to_timedelta(step_ns, unit="ns"))


def _unwrap_pyactigraphy_reader(reader_result):
    if hasattr(reader_result, "readers") and len(reader_result.readers) > 0:
        return reader_result.readers[0]

    if isinstance(reader_result, (list, tuple)) and len(reader_result) > 0:
        return reader_result[0]

    return reader_result


def _read_gt3x_file(file_path: str):
    try:
        from pygt3x.reader import FileReader
    except Exception as exc:
        raise ValueError(
            "This .gt3x file is a raw ActiGraph archive, not a pyActigraphy .agd database. "
            "Install pygt3x to preview .gt3x files directly: pip install pygt3x. "
            "For pyActigraphy sleep/activity metrics, export the recording from ActiLife as .agd "
            "or epoch-count CSV."
        ) from exc

    try:
        with FileReader(file_path) as reader:
            df = reader.to_pandas()

            start_time = _get_nested_attr(
                reader,
                [
                    "start_time",
                    "start_datetime",
                    "start_date",
                    "info.start_time",
                    "info.start_datetime",
                    "info.start_date",
                    "metadata.start_time",
                    "metadata.start_datetime",
                    "metadata.start_date",
                ],
            )

            sample_rate = _get_nested_attr(
                reader,
                [
                    "sample_rate",
                    "sampling_rate",
                    "frequency",
                    "fs",
                    "info.sample_rate",
                    "info.sampling_rate",
                    "info.frequency",
                    "metadata.sample_rate",
                    "metadata.sampling_rate",
                    "metadata.frequency",
                ],
            )

    except Exception as exc:
        raise ValueError(
            "Could not read the .gt3x file with pygt3x. If the file opens in ActiLife, "
            "export it as .agd or CSV and upload that instead. "
            f"Original error: {exc}"
        ) from exc

    if df is None or len(df) == 0:
        raise ValueError("The .gt3x file was read, but no samples were found.")

    df = df.copy()

    timestamp_col = None
    for candidate in ["timestamp", "Timestamp", "time", "Time", "datetime", "DateTime", "date_time"]:
        if candidate in df.columns:
            timestamp_col = candidate
            break

    if timestamp_col is not None:
        df.index = pd.to_datetime(df[timestamp_col], errors="coerce")
        df = df.loc[df.index.notna()]
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = _make_gt3x_datetime_index(
            len(df),
            start_time=start_time,
            sample_rate=sample_rate,
        )

    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        raise ValueError("The .gt3x file was read, but no numeric acceleration columns were found.")

    lower_cols = {str(c).strip().lower(): c for c in numeric_df.columns}

    axis_sets = [
        ("x", "y", "z"),
        ("axis1", "axis2", "axis3"),
        ("axisx", "axisy", "axisz"),
        ("x-axis", "y-axis", "z-axis"),
        ("x_axis", "y_axis", "z_axis"),
    ]

    selected_axes = None
    for axis_names in axis_sets:
        if all(name in lower_cols for name in axis_names):
            selected_axes = [lower_cols[name] for name in axis_names]
            break

    if selected_axes is not None:
        vm = numeric_df[selected_axes].pow(2).sum(axis=1) ** 0.5

        if vm.quantile(0.95) < 16:
            series = ((vm - 1).clip(lower=0) * 1000).rename("ENMO_mg_preview")
        else:
            series = vm.rename("vector_magnitude_preview")
    else:
        series = numeric_df.iloc[:, 0].rename(str(numeric_df.columns[0]))

    series = series.sort_index().dropna()

    if len(series) == 0:
        raise ValueError("The .gt3x file was read, but the preview activity series was empty.")

    return SimpleRawPreview(
        series,
        format_name="ActiGraph GT3X raw preview via pygt3x",
    )

def load_native_file(file_path: str, reader_type: str, activity_mapping: str = "auto"):
    requested_mapping = normalize_activity_mapping(activity_mapping)

    if reader_type == "raw_accelerometer_needs_conversion":
        return load_accelerometer_as_baseraw(
            file_path, epoch_period=30, activity_mapping=requested_mapping
        )

    if reader_type == "geneactiv_bin_accelerometer":
        return read_raw_geneactiv_bin(
            file_path, resample_freq="30s", activity_mapping=requested_mapping
        )

    if reader_type == "accelerometer_timeseries_csv":
        return load_accelerometer_csv_as_baseraw(
            file_path, epoch_period=30, activity_mapping=requested_mapping
        )

    if reader_type == "gt3x":
        return load_gt3x_as_baseraw(
            file_path, epoch_period=30, activity_mapping=requested_mapping
        )

    if requested_mapping not in {"auto", "original"}:
        raise ValueError(
            f"{requested_mapping.upper()} requires a compatible raw tri-axial or preprocessed mapping. "
            f"The detected '{reader_type}' reader exposes an existing activity/count series only. "
            "Choose Recommended/Source activity for this file, or upload raw .bin/.cwa/.gt3x data."
        )

    method_name = READERS.get(reader_type)
    if method_name is None:
        raise ValueError("Unsupported native reader type: {}".format(reader_type))

    reader = getattr(pyActigraphy.io, method_name, None)
    if reader is None:
        raise ValueError("This pyActigraphy installation does not expose '{}'.".format(method_name))

    raw = _unwrap_pyactigraphy_reader(reader(file_path))
    return attach_mapping_metadata(
        raw,
        mapping_metadata(
            requested_mapping,
            "original",
            source=f"pyActigraphy:{reader_type}",
            available_mappings=["auto", "original"],
            note="This format already supplies its own device/source activity series.",
        ),
    )


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


def _sniff_separator(file_path: str, fallback=","):
    try:
        sample = _read_text_head(file_path, n_chars=5000)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,|\t,")
        return dialect.delimiter
    except Exception:
        return fallback


def _looks_like_real_header(columns):
    cols = [str(c).strip() for c in columns if str(c).strip()]
    if len(cols) < 2:
        return False

    known = (
        [x.lower() for x in COMMON_TIMESTAMP_COLUMNS]
        + [x.lower() for x in COMMON_ACTIVITY_COLUMNS]
        + [x.lower() for x in COMMON_LIGHT_COLUMNS]
        + [x.lower() for x in COMMON_TEMPERATURE_COLUMNS]
        + [x.lower() for x in COMMON_NONWEAR_COLUMNS]
    )

    matches = 0
    for c in cols:
        if c.lower() in known:
            matches += 1

    return matches >= 1


def _try_read_delimited(file_path: str, sep: str, header_row: int):
    return pd.read_csv(
        file_path,
        sep=sep,
        header=header_row,
        engine="python",
        on_bad_lines="skip",
    )


def _read_delimited_with_header_detection(file_path: str, preferred_sep: Optional[str] = None):
    seps = []
    if preferred_sep:
        seps.append(preferred_sep)

    sniffed = _sniff_separator(file_path, fallback=",")
    if sniffed not in seps:
        seps.append(sniffed)

    for sep in COMMON_SEPARATORS:
        if sep not in seps:
            seps.append(sep)

    best_df = None
    best_score = -1

    for sep in seps:
        for header_row in range(0, 30):
            try:
                df = _try_read_delimited(file_path, sep=sep, header_row=header_row)
                if df is None or df.empty:
                    continue

                cols = list(df.columns)
                score = 0
                if _looks_like_real_header(cols):
                    score += 10
                score += len([c for c in cols if str(c).strip()])

                if score > best_score:
                    best_score = score
                    best_df = df

                if _looks_like_real_header(cols):
                    return df
            except Exception:
                continue

    if best_df is not None:
        return best_df

    raise ValueError("Could not parse tabular file with any supported delimiter/header combination.")


def _read_rpx_epoch_table(file_path: str) -> pd.DataFrame:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    header_idx = None
    for idx, line in enumerate(lines):
        if '"Zeile","Datum","Zeit"' in line or '"Line","Date","Time"' in line:
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError("Could not find RPX epoch data header.")

    from io import StringIO
    table_text = "".join(lines[header_idx:])
    return pd.read_csv(StringIO(table_text), engine="python")


def read_tabular_file(file_path: str, sep: Optional[str] = None) -> pd.DataFrame:
    suffix = Path(file_path).suffix.lower()

    if suffix in (".csv", ".txt", ".gz"):
        head = _read_text_head(file_path).lower()
        if "actiware export file" in head or "actiware-exportdatei" in head or "fichier d'exportation actiware" in head:
            return _read_rpx_epoch_table(file_path)
        return _read_delimited_with_header_detection(file_path, preferred_sep=sep)

    if suffix in (".xls", ".xlsx", ".ods"):
        return pd.read_excel(file_path)

    raise ValueError("Unsupported tabular file type: {}".format(suffix))


def detect_csv_mapping(df: pd.DataFrame) -> Dict[str, Any]:
    cols = list(df.columns)

    mapping = {
        "timestamp_col": _find_first_existing(
            cols,
            [
                "DATE/TIME",
                "Timestamp",
                "timestamp",
                "DateTime",
                "datetime",
                "Data",
                "Date",
                "DATE",
                "Datum",
            ],
        ),
        "time_col": _find_first_existing(
            cols,
            [
                "Time",
                "Hora",
                "Zeit",
            ],
        ),
        "activity_col": _choose_preferred_column(
            cols,
            [
                "PIM",
                "TAT",
                "ZCM",
                "Atividade",
                "Activity",
                "activity",
                "VM",
                "Axis1",
                "Aktivität",
            ],
            COMMON_ACTIVITY_COLUMNS,
        ),
        "light_col": _choose_preferred_column(
            cols,
            [
                "LIGHT",
                "AMB LIGHT",
                "Luminosidade",
                "Lux",
                "light",
                "Weißes Licht",
                "whitelight",
                "MELANOPIC_LUX",
                "CLEAR",
            ],
            COMMON_LIGHT_COLUMNS,
        ),
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
    time_col: Optional[str] = None,
    sep: str = ",",
):
    df = read_tabular_file(file_path, sep=sep)

    if timestamp_col not in df.columns:
        raise ValueError("Timestamp column '{}' not found.".format(timestamp_col))

    work = df.copy()

    if time_col and time_col in work.columns:
        work["_combined_timestamp"] = (
            work[timestamp_col].astype(str).str.strip() + " " + work[time_col].astype(str).str.strip()
        )
        time_source = "_combined_timestamp"
    elif timestamp_col == "Data" and "Hora" in work.columns:
        work["_combined_timestamp"] = (
            work["Data"].astype(str).str.strip() + " " + work["Hora"].astype(str).str.strip()
        )
        time_source = "_combined_timestamp"
    elif timestamp_col == "Date" and "Time" in work.columns:
        work["_combined_timestamp"] = (
            work["Date"].astype(str).str.strip() + " " + work["Time"].astype(str).str.strip()
        )
        time_source = "_combined_timestamp"
    elif timestamp_col == "Datum" and "Zeit" in work.columns:
        work["_combined_timestamp"] = (
            work["Datum"].astype(str).str.strip() + " " + work["Zeit"].astype(str).str.strip()
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
        time_col=mapping.get("time_col"),
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
    work = work[~work.index.duplicated(keep="first")]

    if len(work.index) < 2:
        raise ValueError("Need at least 2 valid timestamps after parsing.")

    inferred = None
    if work.index.freq is None:
        try:
            if len(work.index) >= 3:
                inferred = pd.infer_freq(work.index)
        except Exception:
            inferred = None

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