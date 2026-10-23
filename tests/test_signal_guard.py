import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from app.signal_guard import assess, daily_metadata
from app.scoring import score_frame

class SignalGuardTests(unittest.TestCase):
    def sample(self):
        close=100+np.sin(np.arange(90)/4)
        return pd.DataFrame({'Open':close-.1,'High':close+1,'Low':close-1,'Close':close,'Volume':2_000_000},index=pd.date_range('2026-01-01',periods=90))
    def test_clear_not_probability(self):
        g=assess(self.sample());self.assertEqual(g['status'],'CLEAR');self.assertIn('olasılığı değildir',g['limits'])
    def test_fake_breakout_volume_rejection(self):
        d=self.sample();d.iloc[-1]=[101,120,98,99,15_000_000]
        g=assess(d);self.assertEqual(g['status'],'BLOCK')
        self.assertTrue({'FAILED_BREAKOUT','VOLUME_REJECTION','VOLUME_SPIKE'} <= {f['code'] for f in g['flags']})
        row=score_frame(d);self.assertLessEqual(row['short_score'],47);self.assertLessEqual(row['long_score'],47);self.assertLessEqual(row['alpha_score'],47)
    def test_bad_bars_fail_closed(self):
        d=self.sample();d.iloc[-1,d.columns.get_loc('High')]=1
        self.assertEqual(assess(d)['status'],'BLOCK');self.assertIsNone(score_frame(d))
        d=self.sample();d.index=[d.index[0]]*len(d);self.assertIsNone(score_frame(d))
    def test_missing_and_nan(self):
        self.assertEqual(assess(self.sample().drop(columns='Volume'))['status'],'BLOCK')
        d=self.sample();d.iloc[-1,0]=float('nan');self.assertIsNone(score_frame(d))
    def test_daily_freshness_and_unclosed(self):
        now=datetime(2026,10,15,14,tzinfo=ZoneInfo('Europe/Istanbul'))
        r=daily_metadata(score_frame(self.sample()),'2026-10-15',now)
        self.assertFalse(r['guard_clear']);self.assertTrue(r['bar_provisional']);self.assertLessEqual(r['short_score'],67)
        r=daily_metadata(score_frame(self.sample()),'2026-09-01',now);self.assertEqual(r['signal_guard']['status'],'BLOCK');self.assertLessEqual(r['alpha_score'],47)
    def test_threshold_is_not_volume_only(self):
        d=self.sample();d.iloc[-1,d.columns.get_loc('Volume')]=12_000_000
        self.assertNotEqual(assess(d)['status'],'CLEAR')
    def test_no_forward_data(self):
        d=self.sample();a=assess(d.iloc[:60]);d.iloc[60:,3]*=100
        self.assertEqual(a,assess(d.iloc[:60]))

    def test_missing_benchmark_is_not_zero_return(self):
        from unittest.mock import patch
        from app import market_data as m
        m._DAILY_CACHE.clear()
        with patch.object(m.yf,'download',return_value=pd.DataFrame()):
            m._BENCH_CACHE['ts']=0
            self.assertEqual(m._benchmark_returns(),(None,None))
        m._BENCH_CACHE['ts']=0
    def test_unavailable_indicators_not_filled_for_filter(self):
        d=self.sample();d['Close']=100.;d['Open']=100.;d['High']=101.;d['Low']=99.
        r=score_frame(d)
        self.assertIsNone(r['rsi']);self.assertFalse(r['guard_clear'])
