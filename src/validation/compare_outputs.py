#!/usr/bin/env python3
"""Matched ActiLab, GGIR, and/or native pyActigraphy agreement analysis.

Do NOT compare unaligned sleep epochs, missingness-imputed observations, or
mismatched acceleration units. Statistics assess agreement, not validation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from scipy import stats
except ImportError:  # scipy is optional; basic comparisons still work
    stats = None


def _number(value):
    return float(value) if np.isfinite(value) else None


def _icc_absolute_two_raters(a: np.ndarray, b: np.ndarray):
    """Two-way random-effects, single-measure absolute-agreement ICC(A,1)."""
    n = len(a)
    if n < 3:
        return None
    matrix = np.column_stack([a, b])
    grand = matrix.mean()
    rowmeans = matrix.mean(axis=1)
    colmeans = matrix.mean(axis=0)
    ss_row = 2 * ((rowmeans - grand) ** 2).sum()
    ss_col = n * ((colmeans - grand) ** 2).sum()
    ss_res = ((matrix - rowmeans[:, None] - colmeans[None, :] + grand) ** 2).sum()
    ms_row = ss_row / (n - 1)
    ms_col = ss_col
    ms_err = ss_res / (n - 1)
    denominator = ms_row + ms_err + 2 * (ms_col - ms_err) / n
    return _number((ms_row - ms_err) / denominator) if denominator > 0 else None


def _categorical(a: pd.Series, b: pd.Series, *, positive=None, ordinal=False) -> dict:
    # Explicitly preserve categories, including '0', '1', 'False' and 'True'.
    x, y = a.astype(str).str.strip(), b.astype(str).str.strip()
    valid = a.notna() & b.notna() & x.ne("") & y.ne("")
    x, y = x[valid].reset_index(drop=True), y[valid].reset_index(drop=True)
    if not len(x):
        return {"category_pairs": 0, "cohen_kappa": None, "accuracy": None}
    categories = sorted(set(x).union(y))
    matrix = pd.crosstab(pd.Categorical(x, categories), pd.Categorical(y, categories), dropna=False).to_numpy()
    n = matrix.sum()
    pa = np.trace(matrix) / n
    pe = float((matrix.sum(axis=1) @ matrix.sum(axis=0)) / (n*n))
    # If both raters always use the same single label, agreement is perfect.
    kappa = 1.0 if pe == 1 and pa == 1 else ((pa - pe) / (1 - pe) if pe < 1 else None)
    report = {"category_pairs": int(n), "categories": "|".join(categories),
              "percent_agreement": float(pa*100), "accuracy": float(pa),
              "cohen_kappa": _number(kappa) if kappa is not None else None}
    if ordinal and len(categories) > 1:
        rank = np.arange(len(categories))
        W = ((rank[:, None] - rank[None, :])/(len(categories)-1))**2
        observed = float(np.sum(W*matrix)/n)
        expected = float(np.sum(W*np.outer(matrix.sum(axis=1), matrix.sum(axis=0)))/(n*n))
        report["quadratic_weighted_kappa"] = _number(1-observed/expected) if expected > 0 else (1.0 if observed==0 else None)
    if len(categories) == 2:
        pos = str(positive).strip() if positive is not None else ("1" if "1" in categories else "True" if "True" in categories else categories[-1])
        if pos in categories:
            tp = int(((x == pos) & (y == pos)).sum())
            fp = int(((x != pos) & (y == pos)).sum())
            fn = int(((x == pos) & (y != pos)).sum())
            tn = int(((x != pos) & (y != pos)).sum())
            report.update({"positive_label": pos, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                           "sensitivity": tp/(tp+fn) if tp+fn else None,
                           "specificity": tn/(tn+fp) if tn+fp else None,
                           "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None})
    return report


def _numeric(a: pd.Series, b: pd.Series) -> dict:
    x, y = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
    valid = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    x, y = x[valid].to_numpy(float), y[valid].to_numpy(float)
    n = len(x)
    out = {"numeric_pairs": n, "missing_one_or_both": int(len(a) - n)}
    if n == 0:
        return out
    diff = x-y
    mean = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1)) if n > 1 else None
    vax = float(np.var(x, ddof=1)) if n > 1 else None
    vby = float(np.var(y, ddof=1)) if n > 1 else None
    pearson = float(np.corrcoef(x, y)[0,1]) if n > 1 and vax > 0 and vby > 0 else None
    ccc_denom = float(np.var(x, ddof=0) + np.var(y, ddof=0) + (np.mean(x)-np.mean(y))**2)
    ccc = 2*float(np.mean((x-np.mean(x))*(y-np.mean(y)))) / ccc_denom if ccc_denom > 0 else None
    spearman = float(stats.spearmanr(x,y).statistic) if stats is not None and n >= 3 and vax > 0 and vby > 0 else None
    tcrit = float(stats.t.ppf(0.975, n-1)) if stats is not None and n > 1 else 1.96
    se = sd/(n**0.5) if sd is not None else None
    out.update({"bias":mean,"bias_ci95_lower":mean-tcrit*se if se is not None else None,
                "bias_ci95_upper":mean+tcrit*se if se is not None else None,
                "mae":float(np.mean(np.abs(diff))),"rmse":float(np.sqrt(np.mean(diff**2))),
                "max_abs_diff":float(np.max(np.abs(diff))),
                "pearson_r":pearson,"spearman_r":spearman,"lin_ccc":_number(ccc) if ccc is not None else None,
                "icc_a1_absolute_agreement":_icc_absolute_two_raters(x,y),
                "bland_altman_bias":mean,
                "bland_altman_loa_lower":mean-1.96*sd if sd is not None else None,
                "bland_altman_loa_upper":mean+1.96*sd if sd is not None else None,
                "sd_paired_difference":sd})
    return out


def compare_frames(left: pd.DataFrame, right: pd.DataFrame, keys: list[str],
                   metric_pairs: list[tuple[str, str]], *, categorical_pairs=None, positive=None, ordinal=None,
                   left_name="actilab", right_name="ggir") -> tuple[pd.DataFrame, pd.DataFrame]:
    categorical_pairs = categorical_pairs or []
    columns_left = [col for col, _ in metric_pairs+categorical_pairs]
    columns_right = [col for _, col in metric_pairs+categorical_pairs]
    for col in keys + columns_left:
        if col not in left.columns:
            raise ValueError(f"{left_name} missing column {col!r}")
    for col in keys + columns_right:
        if col not in right.columns:
            raise ValueError(f"{right_name} missing column {col!r}")
    if not keys or left.duplicated(keys).any() or right.duplicated(keys).any():
        raise ValueError(f"Non-unique or missing match keys {keys!r}; align files and time windows first")
    # Give both dataframes explicit prefixes to avoid duplicate-column collisions.
    left_renamed = left.rename(columns={c: f"{left_name}__{c}" for c in columns_left})
    right_renamed = right.rename(columns={c: f"{right_name}__{c}" for c in columns_right})
    joined = left_renamed.merge(right_renamed, on=keys, how="outer", validate="one_to_one", indicator=True,
                               suffixes=(f"_{left_name}", f"_{right_name}"))
    matched = joined.loc[joined["_merge"] == "both"]
    if matched.empty:
        raise ValueError("No shared row keys: check subject IDs, calendar dates, timezone and epoch alignment")
    report=[]
    for lc,rc in metric_pairs+categorical_pairs:
        cat=(lc,rc) in categorical_pairs
        a,b=matched[f"{left_name}__{lc}"],matched[f"{right_name}__{rc}"]
        row={"left_tool":left_name, "right_tool":right_name,"left_metric":lc,"right_metric":rc,
             "kind":"categorical" if cat else "continuous", "matched_keys":int(len(matched)),
             "left_only_keys":int((joined["_merge"]=="left_only").sum()),
             "right_only_keys":int((joined["_merge"]=="right_only").sum()),
             "scientific_equivalence_confirmed":False}
        row.update(_categorical(a,b,positive=positive,ordinal=bool(ordinal)) if cat else _numeric(a,b))
        report.append(row)
    return pd.DataFrame(report),joined


def compare(actilab, ggir, keys, metric_pairs):
    """Backwards-compatible continuous comparison API."""
    return compare_frames(pd.read_csv(actilab),pd.read_csv(ggir),keys,metric_pairs)[0]


def _pairs(value):
    pairs=[]
    for chunk in value.split(",") if value else []:
        if ":" not in chunk:
            raise ValueError(f"Column mapping must be left:right: {chunk!r}")
        pairs.append(tuple(chunk.split(":",1)))
    return pairs


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actilab_csv")
    parser.add_argument("ggir_csv")
    parser.add_argument("--keys",required=True,help="Comma-separated UNIQUE matching columns in both CSVs")
    parser.add_argument("--metrics",default="",help="Continuous metric mappings, e.g. ra:RA,is:IS")
    parser.add_argument("--categorical",default="",help="Categorical mapping(s), e.g. valid_day:valid_day")
    parser.add_argument("--positive",help="Positive category for binary sensitivity/specificity")
    parser.add_argument("--ordinal",action="store_true",help="Also compute quadratic weighted kappa on ordinal category labels")
    parser.add_argument("--left-name",default="actilab")
    parser.add_argument("--right-name",default="ggir")
    parser.add_argument("--output",default="actilab_ggir_comparison.csv")
    parser.add_argument("--matched-output",help="Optional joined row-level data for independent audit")
    args=parser.parse_args(argv)
    try:
        continuous=_pairs(args.metrics)
        categorical=_pairs(args.categorical)
        if not continuous and not categorical: parser.error("Provide --metrics and/or --categorical")
        report,joined=compare_frames(pd.read_csv(args.actilab_csv),pd.read_csv(args.ggir_csv),
                                     [x.strip() for x in args.keys.split(",")],continuous,
                                     categorical_pairs=categorical,positive=args.positive,
                                     ordinal=args.ordinal,left_name=args.left_name,right_name=args.right_name)
    except ValueError as exc: parser.error(str(exc))
    report.to_csv(args.output,index=False)
    if args.matched_output: joined.to_csv(args.matched_output,index=False)
    print(report.to_string(index=False))
    print(f"Saved {args.output}. Agreement does NOT demonstrate pipeline equivalence.")
    return 0


if __name__=="__main__": raise SystemExit(main())
