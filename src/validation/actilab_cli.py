#!/usr/bin/env python3
"""ActiLab reproducible local CLI: QC, pyActigraphy metrics, sleep, light, export.

Run from the *src* directory with: python -m validation.actilab_cli --help
Unlike the HTTP benchmark, no recording needs to be uploaded to a server.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import traceback

import pandas as pd

from backend.activity_mapping import normalize_activity_signal_settings
from backend.data_quality import inspect_initial_data_coverage, apply_data_quality_control
from backend.release_exports import build_release_tables, effective_methods_manifest
from backend.analysis import run_basic_pyactigraphy_analysis, run_basic_pylight_analysis

DEFAULT_HIGH_PY = ["average_daily_activity", "is", "ism", "isp", "iv", "ivm", "ivp",
                   "l5", "l5p", "m10", "m10p", "ra", "rap", "pra", "par", "kra", "kar"]
DEFAULT_LIGHT = {"light_exposure_level":"exposure_level", "summary_statistics_per_time_bin":"summary_stats",
                 "TAT":"tat", "MLiT":"mlit", "light_L5":"l5", "light_M10":"m10",
                 "light_IS":"is", "light_IV":"iv"}
SLEEP = ["sri", "sleep_midpoint", "tst", "waso", "sleep_efficiency"]


def _json_safe(value):
    if isinstance(value, dict): return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_json_safe(v) for v in value]
    if hasattr(value,"tolist"):
        try: return _json_safe(value.tolist())
        except Exception: pass
    if isinstance(value,pd.Series): return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value,pd.DataFrame): return value.reset_index().astype(str).to_dict("records")
    if pd.isna(value): return None
    if isinstance(value, (str,int,float,bool)) or value is None: return value
    return str(value)


def _write_json(path, data):
    Path(path).write_text(json.dumps(_json_safe(data),indent=2,allow_nan=False,default=str)+"\n",encoding="utf-8")


def _input_files(inputs):
    expanded=[]
    for input_path in inputs:
        path=Path(input_path).expanduser()
        if path.is_file(): expanded.append(path)
        elif path.is_dir():
            expanded.extend(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in
                            {".bin",".gt3x",".agd",".atr",".awd",".dqt",".rpx",".tal",".csv",".gz",".xlsx",".ods",".cwa"})
        else:
            import glob
            expanded.extend(Path(p) for p in glob.glob(str(path)) if Path(p).is_file())
    unique=[]
    for path in sorted(expanded):
        if path.resolve() not in [p.resolve() for p in unique]: unique.append(path)
    if not unique: raise ValueError("No input recordings found. Use one file, folder, or quoted glob")
    return unique


def _flatten_structure(metric, value):
    """Preserve arrays/series/profiles separately instead of averaging periods."""
    if isinstance(value,dict) and value.get("kind")=="series":
        return [{"metric":metric,"index":point.get("index",j),"value":point.get("value")}
                for j,point in enumerate(value.get("values") or []) if isinstance(point,dict)]
    if isinstance(value,(list,tuple)):
        return [{"metric":metric,"index":i,"value":_json_safe(v)} for i,v in enumerate(value)]
    if isinstance(value,dict) and "values" in value and "index" in value:
        return [{"metric":metric,"index":i,"value":_json_safe(v)} for i,v in enumerate(value.get("values") or [])]
    return []


def _load_recording(path, activity, signal, csv_mapping, separator):
    # Keep exactly the same native reader and raw processing code as ActiLab UI.
    from backend.app import _load_native_supported_file
    return _load_native_supported_file(str(path),activity_mapping=activity,csv_mapping=csv_mapping,
                                       csv_separator=separator,activity_signal_settings=signal)


def _sleep_windows(raw, path):
    if not path: return
    df=pd.read_csv(path)
    if not {'start','stop'} <= set(df): raise ValueError("Sleep-window CSV must contain start,stop columns")
    intervals=[]
    for row in df.to_dict("records"):
        start,stop=pd.Timestamp(row['start']),pd.Timestamp(row['stop'])
        if stop>start: intervals.append({'start':start.isoformat(),'stop':stop.isoformat(),'source':'cli_sleep_windows'})
    raw._ui_sleep_windows=intervals


def run_file(path, dest, args, config):
    dest.mkdir(parents=True,exist_ok=True)
    settings=normalize_activity_signal_settings({"epochSeconds":args.epoch,
          "thresholdMethod":args.threshold_method,"thresholdMg":args.threshold_mg,
          **config.get("activity_signal_settings",{})},args.activity)
    raw,reader=_load_recording(path,args.activity,settings,config.get("csv_mapping") or {},args.separator)
    _sleep_windows(raw,args.sleep_windows)
    initial=inspect_initial_data_coverage(raw)
    initial["reader_type"]=reader
    _write_json(dest/"initial_qc.json",initial)
    for mode,entry in initial['modes'].items():
        pd.DataFrame(entry['windows']).to_csv(dest/f"initial_qc_{mode}.csv",index=False)
    # Consistent final mask always applied to activity/sleep metrics.
    support={"masking":{"customizeDataQualityThresholds":True,
                        "minimumValidHoursPerDay":args.min_valid_hours,
                        "minimumValidDaysForRhythm":args.min_consecutive_days,
                        "respectNonwear":not args.ignore_nonwear,
                        "validDayWindowMode":args.day_mode,
                        "minimumSleepWindowCoverage":args.min_sleep_coverage}}
    clean,qc=apply_data_quality_control(raw,support)
    _write_json(dest/"final_qc.json",qc)
    pd.DataFrame(qc['daily_qc']).to_csv(dest/"qc_daily.csv",index=False)
    cleaned=getattr(clean,"_ui_source_activity_series",pd.Series(dtype=float))
    finalmask=getattr(clean,"_ui_analysis_valid_mask",pd.Series(False,index=cleaned.index))
    pd.DataFrame({"timestamp":cleaned.index,"activity_before_qc":cleaned.to_numpy(),
                  "valid_after_qc":finalmask.reindex(cleaned.index,fill_value=False).to_numpy(),
                  "activity_after_qc":cleaned.where(finalmask).to_numpy()}).to_csv(dest/"cleaned_epochs.csv",index=False)
    results={}
    issues=[]
    metric_ids=[]
    if args.stage in {'rhythm','all'}:
        metric_ids.extend(args.metrics.split(',') if args.metrics else DEFAULT_HIGH_PY)
    if args.stage in {'sleep','all'}:
        metric_ids.extend(SLEEP if args.sleep_metrics is None else args.sleep_metrics.split(','))
    metric_ids=list(dict.fromkeys(m.strip() for m in metric_ids if m.strip()))
    algo={'id':args.sleep_algorithm,'params':config.get('sleep_algorithm_params',{})}
    if metric_ids:
        kwargs={'metric_requests':[{'id':m,'params':{'binarize':args.binarize,'threshold':args.activity_threshold,
                      'period':args.period,'freq':args.metric_freq}} for m in metric_ids],
                'family_requests':[],'analysis_scope':'metric','algorithm_request':algo,
                'sleep_window_settings':config.get('sleep_window_settings', {'estimateWithoutDiary':False})}
        results=run_basic_pyactigraphy_analysis(clean,**kwargs)
    light_results={}
    if args.stage in {'light','all'}:
        for label,method in DEFAULT_LIGHT.items():
            try:
                light_results[label]=run_basic_pylight_analysis(clean,method,
                          channel=args.light_channel,threshold_lux=args.light_threshold,
                          binarize=False)
            except Exception as exc:
                issues.append({'metric':label,'status':'unavailable','reason':str(exc)})
    _write_json(dest/"metrics_full.json",results)
    _write_json(dest/"light_full.json",light_results)
    if metric_ids:
        pd.DataFrame([{'metric':m,'status':'available' if results.get(m) is not None else 'unavailable',
                       'source':'pyActigraphy','reason':'Missing reader method, insufficient valid days, or scoring/algorithm failure' if results.get(m) is None else ''} for m in metric_ids]).to_csv(dest/'metric_availability.csv',index=False)
    else:
        pd.DataFrame(columns=['metric','status','source','reason']).to_csv(dest/'metric_availability.csv',index=False)
    table=build_release_tables(clean,results,qc,source_name=path.name)
    pd.DataFrame(table['daily_rows']).to_csv(dest/'daily.csv',index=False)
    pd.DataFrame(table['aggregated_rows']).to_csv(dest/'aggregated.csv',index=False)
    _write_json(dest/'release_metadata.json',effective_methods_manifest(file_names=[path.name],reader_type=reader,
            activity_mapping={'requested':args.activity},settings=settings,analysis_config={'metrics':metric_ids,
            'sleep_algorithm':args.sleep_algorithm,'light_threshold_lux':args.light_threshold},
            data_quality=qc,provenance={'execution':'local_cli'} ,results=results))
    _write_json(dest/'issues.json',issues)
    return {'file':str(path),'reader':reader,'valid_days':qc['valid_days'],
            'nonwear_method':qc['nonwear_detection']['method'],'output_folder':str(dest)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('files',nargs='+',help='Recordings, directories or quoted globs')
    p.add_argument('--out',default='actilab_cli_results')
    p.add_argument('--stage',choices=['qc','rhythm','sleep','light','all'],default='all')
    p.add_argument('--activity',choices=['auto','original','accelerometer','enmo','mad','pim','zcm','tat'],default='auto')
    p.add_argument('--epoch',type=int,choices=[5,10,15,30,60],default=30)
    p.add_argument('--threshold-method',choices=['fixed','adaptive'],default='adaptive')
    p.add_argument('--threshold-mg',type=float)
    p.add_argument('--activity-threshold',type=float,default=4)
    p.add_argument('--binarize',action='store_true',help='Binarize rhythm metric inputs (often unsuitable for mg)')
    p.add_argument('--period',default='7D',help='PyActigraphy per-period metrics duration')
    p.add_argument('--metric-freq',default='1min',help='Resampling interval for IS/IV')
    p.add_argument('--metrics',help='Comma-separated pyActigraphy metric IDs for rhythm stage')
    p.add_argument('--sleep-metrics',help='Comma-separated sleep IDs, e.g. sri,sleep_midpoint')
    p.add_argument('--sleep-algorithm',choices=['roenneberg','crespo','cole_kripke','sadeh','oakley','scripps'],default='roenneberg')
    p.add_argument('--sleep-windows',help='CSV with start,stop columns for scored sleep periods')
    p.add_argument('--light-threshold',type=float,default=500,help='Lux, converted to correct light scale')
    p.add_argument('--light-channel',default=None)
    p.add_argument('--min-valid-hours',type=float,default=16)
    p.add_argument('--min-consecutive-days',type=int,default=2)
    p.add_argument('--min-sleep-coverage',type=float,default=0.8)
    p.add_argument('--day-mode',choices=['calendar_day','recording_anchored'],default='calendar_day')
    p.add_argument('--ignore-nonwear',action='store_true',help='Keep nonwear in final analysis (not recommended)')
    p.add_argument('--config',type=Path,help='Optional JSON with csv_mapping, activity_signal_settings, sleep_algorithm_params etc')
    p.add_argument('--separator',default=',')
    p.add_argument('--fail-fast',action='store_true')
    a=p.parse_args(argv)
    if not 0<a.min_valid_hours<=24: p.error('--min-valid-hours must be in (0,24]')
    if a.min_consecutive_days<1: p.error('--min-consecutive-days must be >=1')
    if not 0<=a.min_sleep_coverage<=1: p.error('--min-sleep-coverage must be in [0,1]')
    config=json.loads(a.config.read_text()) if a.config else {}
    root=Path(a.out).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
    outcomes=[]
    for i,path in enumerate(_input_files(a.files),1):
        sanitized=re.sub(r'[^A-Za-z0-9_.-]','_',path.name)[:95]
        digest=hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:8]
        dest=root/f'{sanitized}_{digest}'
        print(f'[{i}] Processing {path} -> {dest}',flush=True)
        try: outcomes.append({'success':True,**run_file(path,dest,a,config)})
        except Exception as exc:
            outcomes.append({'file':str(path),'success':False,'message':str(exc)})
            print(f'ERROR: {path}: {exc}',file=sys.stderr,flush=True)
            if a.fail_fast: raise
    pd.DataFrame(outcomes).to_csv(root/'batch_status.csv',index=False)
    _write_json(root/'run_config.json',{'generated_utc':datetime.now(timezone.utc).isoformat(),
        'arguments':vars(a),'config':config,'script':'validation.actilab_cli'})
    errors=sum(not x['success'] for x in outcomes)
    print(f'Finished {len(outcomes)} input(s): {errors} failed. Outputs: {root}')
    return 1 if errors else 0

if __name__=='__main__': raise SystemExit(main())
