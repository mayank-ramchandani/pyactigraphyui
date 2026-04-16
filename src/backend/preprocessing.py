import numpy as np
import pandas as pd


def preprocess_timeseries(df, activity_transform="none", light_transform="none", resample_freq="1min"):
    x = df.copy()

    if resample_freq:
        x = x.resample(resample_freq).mean(numeric_only=True)

    if "activity" in x.columns and activity_transform == "zscore":
        mean = x["activity"].mean()
        std = x["activity"].std()
        if std and not np.isnan(std):
            x["activity"] = (x["activity"] - mean) / std

    if "light" in x.columns and light_transform == "log":
        x["light"] = np.log1p(x["light"].clip(lower=0))

    return x


def filter_days(df, mode="all"):
    if mode == "weekdays":
        return df[df.index.dayofweek < 5]
    if mode == "weekends":
        return df[df.index.dayofweek >= 5]
    return df


def normalize_period_string(value: str | None, default="7D"):
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


def parse_number_list(value, cast=float):
    if value is None:
        return []
    if isinstance(value, list):
        try:
            return [cast(item) for item in value]
        except Exception:
            return []
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",") if item.strip()]
        try:
            return [cast(item) for item in parts]
        except Exception:
            return []
    try:
        return [cast(value)]
    except Exception:
        return []
