"""Compare matched preprocessed outputs; numeric comparison is NOT method validation."""
import argparse
import csv
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd


def compare(actilab, ggir, keys, metric_pairs):
    left = pd.read_csv(actilab)
    right = pd.read_csv(ggir)
    for col in keys + [a for a, _ in metric_pairs]:
        if col not in left:
            raise ValueError(f"ActiLab missing column {col!r}")
    for col in keys + [b for _, b in metric_pairs]:
        if col not in right:
            raise ValueError(f"GGIR missing column {col!r}")
    if left.duplicated(keys).any() or right.duplicated(keys).any():
        raise ValueError(f"Non-unique match keys {keys!r}; disambiguate source and window before comparing")
    merged = left.merge(right, on=keys, how="outer", indicator=True, suffixes=("_actilab", "_ggir"))
    n_both = int(merged["_merge"].eq("both").sum())
    if not n_both:
        raise ValueError("No shared row keys; verify dates/participant identity and timezones")
    report = []
    for acti_col, ggir_col in metric_pairs:
        a = f"{acti_col}_actilab" if acti_col == ggir_col else acti_col
        b = f"{ggir_col}_ggir" if acti_col == ggir_col else ggir_col
        part = merged[merged["_merge"].eq("both")]
        ax, by = pd.to_numeric(part[a], errors="coerce"), pd.to_numeric(part[b], errors="coerce")
        mask = ax.notna() & by.notna() & np.isfinite(ax) & np.isfinite(by)
        diff = ax[mask] - by[mask]
        correlation = float(np.corrcoef(ax[mask], by[mask])[0, 1]) if mask.sum() >= 3 and ax[mask].std() > 0 and by[mask].std() > 0 else None
        report.append({
            "actilab_metric": acti_col, "ggir_metric": ggir_col,
            "matched_keys": n_both, "numeric_pairs": int(mask.sum()),
            "actilab_only_keys": int(merged["_merge"].eq("left_only").sum()),
            "ggir_only_keys": int(merged["_merge"].eq("right_only").sum()),
            "missing_one_or_both": int((~mask).sum()),
            "bias": float(diff.mean()) if len(diff) else None,
            "mae": float(diff.abs().mean()) if len(diff) else None,
            "rmse": float(np.sqrt((diff ** 2).mean())) if len(diff) else None,
            "max_abs_diff": float(diff.abs().max()) if len(diff) else None,
            "pearson_r": correlation,
            "scientific_equivalence_confirmed": False,
        })
    return pd.DataFrame(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actilab_csv")
    parser.add_argument("ggir_csv")
    parser.add_argument("--keys", required=True, help="Comma-separated unique matching columns present in both files")
    parser.add_argument("--metrics", required=True, help="Comma-separated column mappings left:right")
    parser.add_argument("--output", default="actilab_ggir_comparison.csv")
    args = parser.parse_args()
    pairs = []
    for chunk in args.metrics.split(","):
        if ":" not in chunk:
            parser.error("Every metric mapping needs ActiLab_column:GGIR_column")
        pairs.append(tuple(chunk.split(":", 1)))
    report = compare(args.actilab_csv, args.ggir_csv, args.keys.split(","), pairs)
    report.to_csv(args.output, index=False)
    print(report.to_string(index=False))
    print(f"Wrote {args.output}. Numeric agreement does NOT establish scientific equivalence.")


if __name__ == "__main__":
    main()
