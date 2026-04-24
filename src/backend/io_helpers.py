from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import csv

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
    if suffix in ("csv", "txt", "gz"):
        head = _read_text_head(file_path).lower()

        if "actiware export file" in head or "actiware-exportdatei" in head or "fichier d'exportation actiware" in head:
            return "rpx"

        if "serial number:" in head and "sample rate:" in head and "store rate:" in head:
            return "dqt"

        if "luminosidade" in head and "atividade" in head and ("data; hora;" in head or "data;hora;" in head):
            return "tal"

        if "mesaid,line,linetime" in head:
            return "mesa"

        # Condor / ActTrust text exports used in pyActigraphy workflows
        if "date/time" in head and "pim" in head and "zcm" in head:
            return "atr"

        return "tabular"

    if suffix in ("xls", "xlsx", "ods"):
        return "tabular"

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