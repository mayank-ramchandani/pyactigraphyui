#!/usr/bin/env python3
"""Independent native pyActigraphy metric calls for reproducible comparison.

Two input modes:
  * An ActiLab `cleaned_epochs.csv` common input (for .bin/.gt3x parity).
  * A native pyActigraphy reader-supported recording (e.g. .agd/.awd).

Importantly, common-input analysis is independent at the metric-call level, NOT
at the preprocessing/reader level. It must not be described as three independent
raw pipelines or used to claim GGIR equivalence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

DEFAULT_METRICS = ['average_daily_activity', 'IS','ISm','ISp','IV','IVm','IVp',
                   'L5','L5p','M10','M10p','RA','RAp','pRA','pAR','kRA','kAR']


def load_common_epochs(path: Path, recording_id: str):
    from pyActigraphy.io import BaseRaw
    frame = pd.read_csv(path)
    needed={'timestamp','activity_after_qc'}
    if not needed.issubset(frame):
        raise ValueError(f'Common-epoch CSV must have {sorted(needed)} columns')
    frame['timestamp']=pd.to_datetime(frame['timestamp'],errors='raise')
    if frame['timestamp'].duplicated().any():
        raise ValueError('Duplicate timestamps in common epoch data')
    series=pd.Series(pd.to_numeric(frame['activity_after_qc'],errors='coerce').to_numpy(),
                     index=pd.DatetimeIndex(frame['timestamp']),name='Activity').sort_index()
    if len(series)<2:
        raise ValueError('At least two epochs are required')
    freq=pd.to_timedelta(series.index.to_series().diff().dropna().mode().iloc[0])
    if freq<=pd.Timedelta(0):
        raise ValueError('Nonpositive analytical epoch')
    if not (series.index.to_series().diff().dropna() == freq).all():
        raise ValueError('Common-epoch file must have a regular timestamp grid; export full cleaned_epochs.csv')
    return BaseRaw(name=recording_id,uuid=recording_id,format='Pandas',axial_mode=None,
                   start_time=series.index[0],period=series.index[-1]-series.index[0],
                   frequency=freq,data=series,light=None)


def load_native_file(path: Path):
    import pyActigraphy.io as io
    readers={'.agd':'read_raw_agd','.atr':'read_raw_atr','.awd':'read_raw_awd',
             '.dqt':'read_raw_dqt','.mesa':'read_raw_mesa','.mtn':'read_raw_mtn',
             '.rpx':'read_raw_rpx','.tal':'read_raw_tal','.bba':'read_raw_bba'}
    ext=path.suffix.lower()
    reader=readers.get(ext)
    if not reader:
        raise ValueError(f'pyActigraphy native reader not verified for {ext or "unknown"}. For .bin/.gt3x use --epochs exported by ActiLab.')
    func=getattr(io,reader,None)
    if not callable(func):
        raise ValueError(f'{reader} unavailable in installed pyActigraphy')
    return func(str(path))


def _summarize(value):
    if value is None:
        return None,'null'
    if isinstance(value,(bool,np.bool_)):
        return int(value),'boolean'
    if isinstance(value,(float,int,np.number)):
        return float(value) if np.isfinite(value) else None,'scalar'
    if isinstance(value,(pd.Timedelta,np.timedelta64)):
        return float(pd.Timedelta(value).total_seconds()/60),'minutes'
    if isinstance(value,pd.Series):
        return None,'series'
    if isinstance(value,pd.DataFrame):
        return None,'dataframe'
    if isinstance(value,(list,tuple,np.ndarray)):
        return None,'array'
    try:
        return float(value),'scalar'
    except (ValueError,TypeError):
        return None,type(value).__name__


def native_metrics(raw, metric_ids, *, freq='1min', threshold=4, binarize=False, period='7D'):
    """Call library methods directly, without using ActiLab's metric dispatcher."""
    out={}
    for metric in metric_ids:
        method=getattr(raw,metric,None)
        if not callable(method):
            out[metric]={'status':'unavailable','reason':'Method absent on this raw type','value':None,'kind':'missing'}
            continue
        params={'binarize':bool(binarize),'threshold':threshold}
        if metric=='average_daily_activity': params['freq']='5min'
        if metric in ('IS','IV'): params['freq']=freq
        if metric in ('ISm','IVm'): params.pop('threshold',None) if not binarize else None
        if metric.endswith('p') and metric in ('ISp','IVp','L5p','M10p','RAp'):
            params['period']=period
            if metric in ('ISp','IVp'): params['freq']=freq
            params['verbose']=False
        if metric in ('pRA','pAR','kRA','kAR'):
            params.pop('binarize',None)
            params['period']=None
            if metric in ('kRA','kAR'): params['freq']=freq
        try:
            result=method(**params)
            scalar,kind=_summarize(result)
            out[metric]={'status':'available' if result is not None else 'unavailable',
                         'value':scalar,'kind':kind,
                         'reason':'' if result is not None else 'Library returned None'}
        except Exception as exc:
            out[metric]={'status':'unavailable','value':None,'kind':'error',
                         'reason':f'{type(exc).__name__}: {exc}'}
    return out


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--epochs',type=Path,help='ActiLab common input: cleaned_epochs.csv')
    modes.add_argument('--native',type=Path,help='Native pyActigraphy reader-supported file (e.g. .agd)')
    parser.add_argument('--source-name',help='Common recording ID in result comparison; defaults to input filename')
    parser.add_argument('--metrics',default=','.join(DEFAULT_METRICS))
    parser.add_argument('--freq',default='1min')
    parser.add_argument('--threshold',type=float,default=4)
    parser.add_argument('--binarize',action='store_true')
    parser.add_argument('--period',default='7D')
    parser.add_argument('--out',type=Path,default=Path('pyactigraphy_reference_results'))
    args=parser.parse_args(argv)
    reference=args.epochs or args.native
    recording_id=args.source_name or reference.name
    raw=load_common_epochs(reference,recording_id) if args.epochs else load_native_file(reference)
    results=native_metrics(raw,[m.strip() for m in args.metrics.split(',') if m.strip()],freq=args.freq,
                           threshold=args.threshold,binarize=args.binarize,period=args.period)
    args.out.mkdir(parents=True,exist_ok=True)
    scalar={'source_file':recording_id}
    details=[]
    for metric,info in results.items():
        # Only scalars in common wide table; complex native profiles remain flagged.
        if info['kind'] in ('scalar','boolean','minutes'): scalar[metric]=info['value']
        details.append({'source_file':recording_id,'metric':metric,**info})
    pd.DataFrame([scalar]).to_csv(args.out/'pyactigraphy_aggregated.csv',index=False)
    pd.DataFrame(details).to_csv(args.out/'pyactigraphy_metric_status.csv',index=False)
    (args.out/'method_config.json').write_text(json.dumps({'input':str(reference),'input_type':'common_actilab_epochs' if args.epochs else 'native_pyactigraphy',
        'independent_preprocessing':bool(args.native),'source_file':recording_id,'parameters':vars(args)},indent=2,default=str),encoding='utf-8')
    print(f'Saved {len(details)} pyActigraphy metric attempts to {args.out}. Check per-metric status before comparing.')
    return 0

if __name__=='__main__': raise SystemExit(main())
