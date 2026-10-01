import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from app.research_data import daily_frame, align_daily
from app.edge_lab import signals, trades, analyze, mean_interval, summarize, edge_research
from app.universe import _parse


def sample(n=1700):
    rng=np.random.default_rng(2)
    close=100*np.exp(np.cumsum(rng.normal(.0005,.02,n)))
    return pd.DataFrame({'time':pd.bdate_range('2018-01-01',periods=n).strftime('%Y-%m-%d'),
        'Open':close*.998,'High':close*1.03,'Low':close*.97,'Close':close,
        'Volume':rng.integers(50000,200000,n)})


class EdgeTests(unittest.TestCase):
    def test_alignment_is_by_date_not_row_number(self):
        stock=sample(100);bench=stock.drop(index=[5,20]).copy()
        s,b,a=align_daily(stock,bench)
        self.assertEqual(s.time.tolist(),b.time.tolist())
        self.assertEqual(a['stock_only_dates'],2)
        self.assertEqual(a['aligned_bars'],98)
        np.testing.assert_allclose(s.Close,b.Close)
        self.assertFalse(a['forward_filled'])

    def test_daily_data_rejects_duplicate_and_invalid_prices(self):
        f=sample(20)
        for bad in (pd.concat([f,f.iloc[:1]]),f.assign(Open=-1),f.assign(Close=np.inf)):
            with self.assertRaises(ValueError):daily_frame(bad.to_dict('records'))
        self.assertEqual(len(daily_frame(f.to_dict('records'))),20)

    def test_signals_cannot_see_future(self):
        f=sample();b=sample();full=signals(f,b);prefix=signals(f.iloc[:800],b.iloc[:800])
        for k in full:pd.testing.assert_series_equal(full[k].iloc[:800],prefix[k])

    def test_next_open_gap_cost_and_nonoverlap(self):
        f=sample(80);f.loc[11,'Open']=200;f.loc[16,'Open']=220
        b=sample(80);b['Open']=100
        f,b,_=align_daily(f,b)
        rows,skipped=trades(f,b,pd.Series(True,index=f.index),5,10,80,30)
        first=rows[0]
        self.assertEqual(first['entry_index'],11);self.assertEqual(first['exit_index'],16)
        self.assertAlmostEqual(first['net_pct'],9.7)
        self.assertAlmostEqual(first['stress_excess_pct'],9.4)
        for prev,nxt in zip(rows,rows[1:]):self.assertGreater(nxt['entry_index'],prev['exit_index'])
        self.assertEqual(skipped,0)
        # Intraday information after an opening exit cannot change the trade set.
        f.loc[16,['High','Low','Volume']]=[220,220,0]
        changed,_=trades(f,b,pd.Series(True,index=f.index),5,10,80,30)
        self.assertEqual(rows,changed)

    def test_split_purges_cross_boundary_positions(self):
        f,b,_=align_daily(sample(1500),sample(1500));mask=pd.Series(True,index=f.index)
        early,_=trades(f,b,mask,20,252,975,30)
        late,_=trades(f,b,mask,20,975,1500,30)
        self.assertTrue(all(x['exit_index']<975 for x in early))
        self.assertTrue(all(x['signal_index']>=975 for x in late))

    def test_missing_session_windows_are_flagged_not_filled(self):
        f=sample(100);b=sample(100).drop(index=15)
        f,b,_=align_daily(f,b)
        rows,skipped=trades(f,b,pd.Series(True,index=f.index),20,10,100,30)
        self.assertGreater(skipped,0)
        self.assertTrue(all(not(x['signal_index']<15<x['exit_index']) for x in rows))

    def test_identical_stock_benchmark_cannot_show_net_edge(self):
        f=sample();out=analyze(f,f)
        self.assertFalse(out['live_approved'])
        for s in out['strategies']:
            self.assertEqual(s['evidence'],'INSUFFICIENT_EVIDENCE')
            if s['late']['n']:self.assertAlmostEqual(s['late']['mean_excess_pct'],-.3)

    def test_bootstrap_reproducible_and_sparse_samples_not_certified(self):
        self.assertIsNone(mean_interval([1]*11))
        self.assertEqual(mean_interval(range(30)),mean_interval(range(30)))
        self.assertIsNone(summarize([])['mean_excess_pct'])

    def test_old_alpha_uses_matching_calendar(self):
        from app import alpha_engine
        s=sample(450);b=s.drop(index=[6,23,260]).copy()
        rows=s.to_dict('records');brows=b.to_dict('records')
        def fake(code,period):return (b,brows) if code=='XU100' else (s,rows)
        with patch.object(alpha_engine,'_df',side_effect=fake),patch.object(alpha_engine,'score_frame',return_value={'short_score':80,'long_score':80}):
            alpha_engine._CACHE.clear();o=alpha_engine.validate_alpha('TEST')
        self.assertEqual(o['alignment']['stock_only_dates'],3)
        self.assertTrue(o['overlap_removed'])
        self.assertEqual(o['horizons']['20d']['mean_excess_pct'],0)

    def test_universe_header_never_becomes_a_stock(self):
        html='<table><tr><td>KOD</td><td>Şirket Ünvanı</td></tr><tr><td>ASELS</td><td>Aselsan</td></tr></table>'
        self.assertEqual([r['ticker'] for r in _parse(html)],['ASELS'])

    def test_api_bounds_and_catalog(self):
        from fastapi.testclient import TestClient
        from app.main import app
        c=TestClient(app)
        with patch('app.main.edge_research',return_value={'status':'OK'}) as f:
            self.assertEqual(c.get('/api/edge/ASELS?cost_bps=30').status_code,200)
            for val in ['nan','inf','-1','301']:
                self.assertEqual(c.get('/api/edge/ASELS?cost_bps='+val).status_code,422)
            self.assertEqual(f.call_count,1)
        d=c.get('/api/edge-catalog').json()
        self.assertEqual(len(d['hypotheses']),7)
        self.assertTrue(all(h['sources'] for h in d['hypotheses']))

    def test_source_failure_is_explicit(self):
        with patch('app.edge_lab.yahoo_rows',side_effect=RuntimeError('private upstream detail')):
            self.assertEqual(edge_research('FAIL')['status'],'SOURCE_UNAVAILABLE')

if __name__=='__main__':unittest.main()
