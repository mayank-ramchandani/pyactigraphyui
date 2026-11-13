#!/usr/bin/env python3
"""Compare matched ActiLab, GGIR and pyActigraphy CSVs on common keys.

Mapping JSON: {"continuous": {"RA": ["ra","RA","RA"]},
               "categorical": {"valid_day": ["valid_day","valid_day","valid_day"]}}
The order in each triple is ActiLab, GGIR, native pyActigraphy.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from .compare_outputs import compare_frames
except ImportError:
    from compare_outputs import compare_frames

TOOLS = ["actilab","ggir","pyactigraphy"]


def compare_three(inputs: list[pd.DataFrame], keys: list[str], mapping: dict):
    if len(inputs) != 3 or not keys:
        raise ValueError("Exactly three inputs and non-empty matching keys are required")
    if not (mapping.get("continuous") or mapping.get("categorical")):
        raise ValueError("Mapping must contain at least one metric")
    for tool,frame in zip(TOOLS,inputs):
        if any(key not in frame.columns for key in keys) or frame.duplicated(keys).any():
            raise ValueError(f"{tool} has missing or non-unique matching keys")
    reports=[]
    subset={}
    for i,tool in enumerate(TOOLS):
        requested={cols[i] for group in ("continuous","categorical") for cols in mapping.get(group,{}).values()}
        missing=requested-set(inputs[i].columns)
        if missing: raise ValueError(f"{tool} missing requested columns: {sorted(missing)}")
        rename={col:f"{tool}__{col}" for col in requested}
        subset[tool]=inputs[i][keys+sorted(requested)].rename(columns=rename)
    triple=subset["actilab"].merge(subset["ggir"],on=keys,how="inner",validate="one_to_one").merge(
        subset["pyactigraphy"],on=keys,how="inner",validate="one_to_one")
    if triple.empty: raise ValueError("No shared triple keys; align time zones, participant IDs and windows")
    for i,j in ((0,1),(0,2),(1,2)):
        a,b=TOOLS[i],TOOLS[j]
        cont=[(cols[i],cols[j]) for cols in mapping.get("continuous",{}).values()]
        cat=[(cols[i],cols[j]) for cols in mapping.get("categorical",{}).values()]
        report,_=compare_frames(inputs[i],inputs[j],keys,cont,categorical_pairs=cat,left_name=a,right_name=b)
        report["n_triple_matched_keys"]=len(triple)
        reports.append(report)
    three_way=[]
    for kind,group in (("continuous",mapping.get("continuous",{})),("categorical",mapping.get("categorical",{}))):
        for label,columns in group.items():
            values=[triple[f"{tool}__{col}"] for tool,col in zip(TOOLS,columns)]
            if kind=="continuous":
                arr=np.column_stack([pd.to_numeric(x,errors="coerce") for x in values])
                valid=np.isfinite(arr).all(axis=1)
                matched=arr[valid]
                three_way.append({"metric":label,"type":kind,"n_triplets":len(matched),
                                  "mean_per_row_max_min_difference":float(np.mean(np.ptp(matched,axis=1))) if len(matched) else None,
                                  "all_three_identical_count":int((np.ptp(matched,axis=1)==0).sum()) if len(matched) else 0})
            else:
                equal=values[0].notna() & values[1].notna() & values[2].notna()
                exact=(values[0].astype(str)==values[1].astype(str)) & (values[1].astype(str)==values[2].astype(str))
                n=int(equal.sum())
                three_way.append({"metric":label,"type":kind,"n_triplets":n,"all_three_identical_count":int((exact & equal).sum()),
                                  "three_way_percent_agreement":float(100*(exact & equal).sum()/n) if n else None})
    return pd.concat(reports,ignore_index=True),pd.DataFrame(three_way),triple


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--actilab",required=True)
    p.add_argument("--ggir",required=True)
    p.add_argument("--pyactigraphy",required=True)
    p.add_argument("--keys",required=True,help="Unique shared IDs, e.g. participant_id,date")
    p.add_argument("--mapping",required=True,help="JSON path with continuous/categorical mapping triples")
    p.add_argument("--out",default="three_way_comparison")
    a=p.parse_args(argv)
    mapping=json.loads(Path(a.mapping).read_text())
    for group in ("continuous","categorical"):
        for label,columns in mapping.get(group,{}).items():
            if len(columns)!=3: p.error(f"{group}.{label} must be a 3-column list")
    try:
        pairwise,overall,triple=compare_three([pd.read_csv(v) for v in (a.actilab,a.ggir,a.pyactigraphy)],
                                               [x.strip() for x in a.keys.split(",")],mapping)
    except ValueError as exc: p.error(str(exc))
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    pairwise.to_csv(a.out+"_pairwise.csv",index=False)
    overall.to_csv(a.out+"_three_way.csv",index=False)
    triple.to_csv(a.out+"_matched_rows.csv",index=False)
    print(f"Saved three comparison CSVs with {len(triple)} triply matched rows; statistical agreement is not validation.")
    return 0

if __name__=="__main__": raise SystemExit(main())
