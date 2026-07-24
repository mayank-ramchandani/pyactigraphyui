from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import csv
import gzip
import io
import re
import unicodedata

import pandas as pd
import pyActigraphy

from .activity_mapping import attach_mapping_metadata, mapping_metadata, normalize_activity_mapping
from .accelerometer_loader import (
    load_accelerometer_as_baseraw,
    load_accelerometer_csv_as_baseraw,
    looks_like_accelerometer_timeseries_file,
)
from .gt3x_loader import load_gt3x_as_baseraw, load_gt3x_light_as_raw
from .geneactiv_bin import (
    GeneActivRaw,
    SimpleLightRecording,
    looks_like_geneactiv_bin,
    read_raw_geneactiv_bin,
)

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
    "Heure",
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
    "Activité",
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
    "Lumière blanche",
    "Rotes Licht",
    "Grünes Licht",
    "Blaues Licht",
    "Lumière rouge",
    "Lumière verte",
    "Lumière bleue",
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
    "Statut hors poignet",
    "Hors poignet",
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
    "Activité",
]

PREFERRED_LIGHT_ORDER = [
    "LIGHT",
    "AMB LIGHT",
    "Luminosidade",
    "Lux",
    "light",
    "Weißes Licht",
    "Lumière blanche",
    "whitelight",
    "MELANOPIC_LUX",
    "CLEAR",
]

COMMON_SEPARATORS = [",", ";", "\t", "|"]


def _decode_text_bytes(raw: bytes) -> Tuple[str, str]:
    """Decode text uploads without assuming every CSV is UTF-8.

    Actiware exports are commonly written as UTF-8 or Windows-1252.  UTF-16 is
    also accepted for spreadsheet exports.  Latin-1 is retained as a final,
    lossless fallback so column inspection can still provide a useful error.
    """
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"

    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    return raw.decode("utf-8", errors="replace"), "utf-8-replacement"


def detect_text_encoding(file_path: str, n_bytes: int = 65536) -> str:
    opener = gzip.open if str(file_path).lower().endswith(".gz") else open
    with opener(file_path, "rb") as handle:
        raw = handle.read(n_bytes)
    _text, encoding = _decode_text_bytes(raw)
    return encoding


def _read_text(file_path: str, n_chars: Optional[int] = None) -> Tuple[str, str]:
    opener = gzip.open if str(file_path).lower().endswith(".gz") else open
    with opener(file_path, "rb") as handle:
        raw = handle.read() if n_chars is None else handle.read(max(n_chars * 4, n_chars))
    text, encoding = _decode_text_bytes(raw)
    return (text if n_chars is None else text[:n_chars]), encoding


def _read_text_head(file_path: str, n_chars: int = 20000) -> str:
    text, _encoding = _read_text(file_path, n_chars=n_chars)
    return text


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
    """Compatibility wrapper retained for callers of the former preview reader."""
    return load_gt3x_as_baseraw(
        file_path,
        epoch_period=30,
        activity_mapping="auto",
    )

def load_native_file(
    file_path: str,
    reader_type: str,
    activity_mapping: str = "auto",
    purpose: str = "activity",
):
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
        if str(purpose or "activity").strip().lower() == "light":
            return load_gt3x_light_as_raw(file_path, epoch_period=30)
        return load_gt3x_as_baseraw(
            file_path, epoch_period=30, activity_mapping=requested_mapping
        )

    # Philips Actiware/RPX exports are often distributed as localized CSVs.
    # pyActigraphy's RPX reader assumes a narrow English layout and can leave
    # ``data_offset`` undefined for French/German exports. Parse the epoch table
    # directly, while retaining the normal source-activity semantics.
    if reader_type == "rpx" and Path(file_path).suffix.lower() in {".csv", ".txt", ".gz"}:
        if requested_mapping not in {"auto", "original"}:
            raise ValueError(
                f"{requested_mapping.upper()} cannot be derived from an Actiware/RPX count export. "
                "Choose Recommended/Source activity, or upload raw tri-axial data."
            )
        require_activity = str(purpose or "activity").strip().lower() != "light"
        mapped_df, _mapping = load_auto_tabular(file_path, require_activity=require_activity)
        return build_baseraw_from_dataframe(
            mapped_df,
            name=Path(file_path).name,
            uuid=f"rpx-{Path(file_path).stem}",
            require_activity=require_activity,
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


def _try_read_delimited(file_path: str, sep: str, header_row: int, encoding: str):
    return pd.read_csv(
        file_path,
        sep=sep,
        header=header_row,
        engine="python",
        on_bad_lines="skip",
        encoding=encoding,
        compression="infer",
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

    encoding = detect_text_encoding(file_path)
    best_df = None
    best_score = -1

    for sep in seps:
        for header_row in range(0, 80):
            try:
                df = _try_read_delimited(
                    file_path,
                    sep=sep,
                    header_row=header_row,
                    encoding=encoding,
                )
                if df is None or df.empty:
                    continue

                cols = list(df.columns)
                score = 0
                if _looks_like_real_header(cols):
                    score += 100
                score += len([c for c in cols if str(c).strip()])

                if score > best_score:
                    best_score = score
                    best_df = df

                if _looks_like_real_header(cols):
                    df.attrs["source_encoding"] = encoding
                    return df
            except Exception:
                continue

    if best_df is not None:
        best_df.attrs["source_encoding"] = encoding
        return best_df

    raise ValueError("Could not parse tabular file with any supported delimiter/header combination.")


def _normalize_column_label(value: Any) -> str:
    text = str(value or "").replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


_RPX_DATE_ALIASES = {"date", "datum", "data"}
_RPX_TIME_ALIASES = {"time", "heure", "zeit", "hora"}
_RPX_ACTIVITY_ALIASES = {"activity", "activite", "aktivitat", "atividade", "pim", "tat", "zcm"}
_RPX_ROW_ALIASES = {"line", "ligne", "zeile", "linha", "row"}


def _unique_headers(headers: List[str]) -> List[str]:
    counts: Dict[str, int] = {}
    output: List[str] = []
    for index, value in enumerate(headers):
        label = str(value or "").strip() or f"column_{index + 1}"
        count = counts.get(label, 0)
        counts[label] = count + 1
        output.append(label if count == 0 else f"{label}_{count + 1}")
    return output


def _find_rpx_epoch_header(rows: List[List[str]]) -> Optional[int]:
    best_index = None
    best_score = -1
    for index, row in enumerate(rows):
        normalized = [_normalize_column_label(value) for value in row]
        labels = set(normalized)
        has_date = bool(labels & _RPX_DATE_ALIASES)
        has_time = bool(labels & _RPX_TIME_ALIASES)
        has_activity = bool(labels & _RPX_ACTIVITY_ALIASES)
        if not (has_date and has_time and has_activity):
            continue
        score = 100
        score += 10 if labels & _RPX_ROW_ALIASES else 0
        score += sum(
            token in labels
            for token in (
                "lumiereblanche",
                "weisseslicht",
                "whitelight",
                "roteslicht",
                "gruneslicht",
                "blaueslicht",
            )
        )
        score += len([value for value in row if str(value).strip()])
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def _read_rpx_epoch_table(file_path: str) -> pd.DataFrame:
    """Read localized Philips Actiware/RPX CSV exports directly.

    pyActigraphy's RPX reader assumes a narrow English export layout and can
    leave ``data_offset`` undefined for French/German variants.  This parser
    locates the actual epoch table by semantic column names and supports both
    UTF-8 and Windows-1252 exports.
    """
    text, encoding = _read_text(file_path)
    rows = list(csv.reader(io.StringIO(text), delimiter=","))
    header_idx = _find_rpx_epoch_header(rows)
    if header_idx is None:
        raise ValueError(
            "Could not find the epoch-by-epoch activity table in this Actiware/RPX export. "
            "Re-export the file with epoch data included."
        )

    headers = _unique_headers(rows[header_idx])
    normalized_headers = [_normalize_column_label(value) for value in headers]
    date_index = next((i for i, value in enumerate(normalized_headers) if value in _RPX_DATE_ALIASES), None)
    time_index = next((i for i, value in enumerate(normalized_headers) if value in _RPX_TIME_ALIASES), None)
    activity_index = next((i for i, value in enumerate(normalized_headers) if value in _RPX_ACTIVITY_ALIASES), None)

    if date_index is None or time_index is None or activity_index is None:
        raise ValueError("The Actiware/RPX epoch table is missing date, time, or activity columns.")

    candidate_rows = []
    for row in rows[header_idx + 1 :]:
        if not row or not any(str(value).strip() for value in row):
            continue
        candidate_rows.append(list(row[: len(headers)]) + [""] * max(0, len(headers) - len(row)))

    df = pd.DataFrame(candidate_rows, columns=headers)
    if df.empty:
        raise ValueError(
            "The Actiware/RPX epoch table was found, but it contained no epoch rows."
        )

    combined = (
        df.iloc[:, date_index].astype(str).str.strip()
        + " "
        + df.iloc[:, time_index].astype(str).str.strip()
    )
    parsed_timestamp = pd.to_datetime(combined, errors="coerce", dayfirst=True)
    has_activity = df.iloc[:, activity_index].astype(str).str.strip().ne("")
    df = df.loc[parsed_timestamp.notna() & has_activity].copy()

    if len(df) < 2:
        raise ValueError(
            "The Actiware/RPX epoch table was found, but fewer than two valid timestamped activity rows were available."
        )

    df.attrs["source_encoding"] = encoding
    df.attrs["rpx_header_row"] = int(header_idx)
    df.attrs["rpx_localized_parser"] = True
    return df


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


def _coerce_localized_numeric(series: pd.Series) -> pd.Series:
    """Convert numeric columns that may use decimal commas or localized NA text."""
    missing_tokens = {
        "", "nan", "na", "n/a", "null", "none", "kz", "n.v.", "nv",
        "non applicable", "nicht verfugbar", "nicht verfügbar", "non saisi",
    }

    def convert(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip().replace("\u00a0", "").replace(" ", "")
        if text.lower() in missing_tokens:
            return None
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")
        return text

    return pd.to_numeric(series.map(convert), errors="coerce")


def _canonical_light_channel(column_name: str) -> Optional[str]:
    normalized = _normalize_column_label(column_name)
    aliases = {
        "light": "LIGHT",
        "lux": "LIGHT",
        "illuminance": "LIGHT",
        "amblight": "LIGHT",
        "whitelight": "LIGHT",
        "weisseslicht": "LIGHT",
        "weisselicht": "LIGHT",
        "lumiereblanche": "LIGHT",
        "luminosidade": "LIGHT",
        "redlight": "RED LIGHT",
        "roteslicht": "RED LIGHT",
        "lumiererouge": "RED LIGHT",
        "greenlight": "GREEN LIGHT",
        "gruneslicht": "GREEN LIGHT",
        "grueneslicht": "GREEN LIGHT",
        "lumiereverte": "GREEN LIGHT",
        "bluelight": "BLUE LIGHT",
        "blaueslicht": "BLUE LIGHT",
        "lumierebleue": "BLUE LIGHT",
        "irlight": "IR LIGHT",
        "uvalight": "UVA LIGHT",
        "uvblight": "UVB LIGHT",
        "melanopiclux": "MELANOPIC_LUX",
        "clear": "CLEAR",
    }
    return aliases.get(normalized)


def _detect_light_column_map(columns: List[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for column in columns:
        canonical = _canonical_light_channel(str(column))
        if canonical and canonical not in result:
            result[canonical] = column
    return result


def detect_csv_mapping(df: pd.DataFrame) -> Dict[str, Any]:
    cols = list(df.columns)

    mapping = {
        "timestamp_col": _find_first_existing(
            cols,
            [
                "DATE/TIME", "Timestamp", "timestamp", "DateTime", "datetime",
                "Data", "Date", "DATE", "Datum",
            ],
        ),
        "time_col": _find_first_existing(cols, ["Time", "Hora", "Zeit", "Heure"]),
        "activity_col": _choose_preferred_column(
            cols,
            [
                "PIM", "TAT", "ZCM", "Atividade", "Activity", "activity",
                "VM", "Axis1", "Aktivität", "Activité", "PAXMTSH", "PAXMTSM",
            ],
            COMMON_ACTIVITY_COLUMNS + ["Activité", "PAXMTSH", "PAXMTSM"],
        ),
        "light_col": _choose_preferred_column(
            cols,
            [
                "LIGHT", "AMB LIGHT", "Luminosidade", "Lux", "light",
                "Weißes Licht", "Lumière blanche", "whitelight",
                "MELANOPIC_LUX", "CLEAR", "PAXLXMM", "PAXLXSH",
            ],
            COMMON_LIGHT_COLUMNS + ["Lumière blanche", "PAXLXMM", "PAXLXSH"],
        ),
        "temperature_col": _find_first_existing(cols, COMMON_TEMPERATURE_COLUMNS),
        "nonwear_col": _find_first_existing(cols, COMMON_NONWEAR_COLUMNS),
        "participant_col": _find_first_existing(cols, ["SEQN", "participant", "participant_id", "subject", "subject_id"]),
        "light_columns": _detect_light_column_map(cols),
    }

    return mapping


def _looks_like_nhanes_paxhr(df: pd.DataFrame) -> bool:
    normalized = {_normalize_column_label(column) for column in df.columns}
    return {"seqn", "paxdayh", "paxssnhp", "paxmtsh"}.issubset(normalized)


def _nhanes_paxhr_guidance() -> str:
    return (
        "This appears to be the NHANES PAXHR_H cohort-level hour-summary dataset, not a single timestamped "
        "actigraphy recording. Filter it to one SEQN, merge PAXFDAY and PAXFTIME from PAXHD_H, and use "
        "PAXSSNHP to build a participant-relative hourly time index. Because the public files do not include "
        "the actual calendar date, choose and document a synthetic anchor date consistent with the reported "
        "day of week. Then map PAXMTSH as activity. Do not combine participants into one pyActigraphy run."
    )


def tabular_guidance(df: pd.DataFrame) -> Optional[str]:
    """Return format-specific guidance for tabular data that needs preparation."""
    if _looks_like_nhanes_paxhr(df):
        return _nhanes_paxhr_guidance()
    return None


def load_custom_tabular(
    file_path: str,
    timestamp_col: str,
    activity_col: Optional[str] = None,
    light_col: Optional[str] = None,
    temperature_col: Optional[str] = None,
    nonwear_col: Optional[str] = None,
    time_col: Optional[str] = None,
    sep: str = ",",
    require_activity: bool = True,
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
        work["_combined_timestamp"] = work["Data"].astype(str).str.strip() + " " + work["Hora"].astype(str).str.strip()
        time_source = "_combined_timestamp"
    elif timestamp_col == "Date" and "Time" in work.columns:
        work["_combined_timestamp"] = work["Date"].astype(str).str.strip() + " " + work["Time"].astype(str).str.strip()
        time_source = "_combined_timestamp"
    elif timestamp_col == "Date" and "Heure" in work.columns:
        work["_combined_timestamp"] = work["Date"].astype(str).str.strip() + " " + work["Heure"].astype(str).str.strip()
        time_source = "_combined_timestamp"
    elif timestamp_col == "Datum" and "Zeit" in work.columns:
        work["_combined_timestamp"] = work["Datum"].astype(str).str.strip() + " " + work["Zeit"].astype(str).str.strip()
        time_source = "_combined_timestamp"
    else:
        time_source = timestamp_col

    work[time_source] = pd.to_datetime(work[time_source], errors="coerce", dayfirst=True)
    work = work.dropna(subset=[time_source]).sort_values(time_source)

    out = pd.DataFrame(index=pd.DatetimeIndex(work[time_source]))

    if activity_col:
        if activity_col not in work.columns:
            raise ValueError("Activity column '{}' not found.".format(activity_col))
        out["activity"] = _coerce_localized_numeric(work[activity_col]).to_numpy()
    elif require_activity:
        raise ValueError("Select an activity column for this actigraphy file.")

    light_columns = _detect_light_column_map(list(work.columns))
    if light_col:
        if light_col not in work.columns:
            raise ValueError("Light column '{}' not found.".format(light_col))
        selected_canonical = _canonical_light_channel(light_col) or "LIGHT"
        light_columns = {selected_canonical: light_col, **light_columns}

    for canonical, source_column in light_columns.items():
        out[f"light__{canonical}"] = _coerce_localized_numeric(work[source_column]).to_numpy()

    if temperature_col:
        if temperature_col not in work.columns:
            raise ValueError("Temperature column '{}' not found.".format(temperature_col))
        out["temperature"] = _coerce_localized_numeric(work[temperature_col]).to_numpy()

    if nonwear_col:
        if nonwear_col not in work.columns:
            raise ValueError("Non-wear column '{}' not found.".format(nonwear_col))
        out["nonwear"] = _coerce_localized_numeric(work[nonwear_col]).to_numpy()
        out.attrs["nonwear_source_column"] = str(nonwear_col)

    out.attrs["source_encoding"] = df.attrs.get("source_encoding")
    out.attrs["source_mapping"] = {
        "timestamp_col": timestamp_col,
        "time_col": time_col,
        "activity_col": activity_col,
        "light_col": light_col,
        "temperature_col": temperature_col,
        "nonwear_col": nonwear_col,
    }
    out = out.dropna(how="all")
    return out


def load_auto_tabular(
    file_path: str,
    sep: str = ",",
    require_activity: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = read_tabular_file(file_path, sep=sep)
    mapping = detect_csv_mapping(df)

    guidance = tabular_guidance(df)
    if guidance and not mapping.get("timestamp_col"):
        raise ValueError(guidance)

    if not mapping.get("timestamp_col"):
        raise ValueError(
            "Could not automatically detect a timestamp column. Enable manual CSV mapping and select the timestamp column."
        )
    if require_activity and not mapping.get("activity_col"):
        raise ValueError(
            "Could not automatically detect an activity column. Enable manual CSV mapping and select the activity column."
        )
    if not require_activity and not mapping.get("activity_col") and not mapping.get("light_col"):
        raise ValueError(
            "Could not automatically detect a light column. Enable manual CSV mapping and select the light column."
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
        require_activity=require_activity,
    ), mapping


def build_baseraw_from_dataframe(
    df: pd.DataFrame,
    name: str = "Mapped File",
    uuid: str = "mapped-device",
    require_activity: bool = True,
):
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
        diffs = work.index.to_series().diff().dropna()
        delta = diffs.median() if len(diffs) else work.index[1] - work.index[0]
        if pd.isna(delta) or delta <= pd.Timedelta(0):
            raise ValueError("Could not infer recording frequency from timestamps.")
        work = work.asfreq(delta)

    if work.index.freq is None:
        raise ValueError("Could not infer recording frequency from timestamps.")

    if "activity" in work.columns:
        activity = pd.to_numeric(work["activity"], errors="coerce")
    elif require_activity:
        raise ValueError("Mapped table must contain an activity column before analysis.")
    else:
        activity = pd.Series(index=work.index, data=float("nan"), name="activity")

    channels: Dict[str, pd.Series] = {}
    for column in work.columns:
        if str(column).startswith("light__"):
            channel_name = str(column).split("light__", 1)[1]
            channels[channel_name] = pd.to_numeric(work[column], errors="coerce").rename(channel_name)
    if "light" in work.columns and "LIGHT" not in channels:
        channels["LIGHT"] = pd.to_numeric(work["light"], errors="coerce").rename("LIGHT")

    raw = GeneActivRaw(
        data=activity.rename("activity"),
        light=SimpleLightRecording(channels),
        format="Mapped tabular actigraphy",
        name=name,
        metadata={
            "source": "mapped_tabular",
            "uuid": uuid,
            "source_encoding": df.attrs.get("source_encoding"),
            "source_mapping": df.attrs.get("source_mapping", {}),
            "light_channels": list(channels.keys()),
        },
    )

    if "nonwear" in work.columns:
        source_column = str(df.attrs.get("nonwear_source_column", "nonwear"))
        normalized_name = _normalize_column_label(source_column)
        values = pd.to_numeric(work["nonwear"], errors="coerce")
        if normalized_name in {"wear", "worn", "wearstatus"}:
            raw.mask = values.fillna(0).clip(lower=0, upper=1)
        else:
            raw.mask = (1 - values.fillna(0)).clip(lower=0, upper=1)
        raw._ui_detected_nonwear_source = source_column

    return attach_mapping_metadata(
        raw,
        mapping_metadata(
            "original",
            "original",
            source="mapped_tabular",
            available_mappings=["auto", "original"],
            note="The mapped source activity column is used without deriving ENMO, MAD, or processed acceleration.",
        ),
    )

