"""Daily research data: explicit calendar alignment, never positional matching."""
import numpy as np
import pandas as pd


def daily_frame(rows):
    frame = pd.DataFrame(rows).rename(columns={k:k.title() for k in ('open','high','low','close','volume')})
    required = ['time','Open','High','Low','Close','Volume']
    if not set(required).issubset(frame):
        raise ValueError('OHLCV veya tarih alanı eksik.')
    frame = frame[required].copy()
    frame['time'] = pd.to_datetime(frame.time, errors='coerce').dt.strftime('%Y-%m-%d')
    for c in required[1:]: frame[c] = pd.to_numeric(frame[c], errors='coerce')
    if frame.time.isna().any() or frame.time.duplicated().any():
        raise ValueError('Eksik veya tekrarlanan işlem tarihi.')
    if not np.isfinite(frame[required[1:]].to_numpy(float)).all():
        raise ValueError('Sayısal olmayan veya eksik OHLCV.')
    if ((frame[['Open','High','Low','Close']]<=0).any(axis=1) | (frame.Volume<0) |
        (frame.High<frame[['Open','Close','Low']].max(axis=1)) |
        (frame.Low>frame[['Open','Close']].min(axis=1))).any():
        raise ValueError('Tutarsız OHLCV.')
    return frame.sort_values('time').reset_index(drop=True)


def align_daily(stock, benchmark):
    """Keep a one-to-one intersection and source positions for gap detection."""
    if any(f.time.isna().any() or f.time.duplicated().any() for f in (stock,benchmark)):
        raise ValueError('Eksik veya tekrarlanan işlem tarihi; eşleme engellendi.')
    s = stock.sort_values('time').drop_duplicates('time').set_index('time').copy()
    b = benchmark.sort_values('time').drop_duplicates('time').set_index('time').copy()
    s['_source_pos'] = np.arange(len(s)); b['_source_pos'] = np.arange(len(b))
    dates = s.index.intersection(b.index).sort_values()
    missing = s.index.symmetric_difference(b.index)
    internal = sum(dates.min()<=d<=dates.max() for d in missing) if len(dates) else 0
    audit = {'stock_bars':len(s),'benchmark_bars':len(b),'aligned_bars':len(dates),
             'stock_only_dates':len(s.index.difference(b.index)),
             'benchmark_only_dates':len(b.index.difference(s.index)),
             'internal_unmatched_dates':int(internal), 'forward_filled':False}
    return s.loc[dates].reset_index(), b.loc[dates].reset_index(), audit
