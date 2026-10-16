import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
import numpy as np
import pandas as pd
from app.community_indicators import calculate,confirmed_frame,snapshot,chart_series,evaluate


def fixture(n=650):
 rng=np.random.default_rng(71);c=100+np.arange(n)*.03+np.sin(np.arange(n)*.19)*8+rng.normal(0,.3,n)
 return pd.DataFrame({'time':pd.bdate_range('2022-01-03',periods=n).strftime('%Y-%m-%d'),'Open':c-.2,'High':c+1,'Low':c-1,'Close':c,'Volume':1000000+rng.integers(0,500000,n)})

class CommunityTests(unittest.TestCase):
 def test_no_future_dependency(self):
  df=fixture();prefix=calculate(df.iloc[:400]);full=calculate(df).iloc[:400]
  pd.testing.assert_frame_equal(prefix,full)
  altered=df.copy();altered.loc[400:,'Close']*=1.7;altered.loc[400:,'Open']*=1.7;altered.loc[400:,'High']*=1.7;altered.loc[400:,'Low']*=1.7
  pd.testing.assert_frame_equal(prefix,calculate(altered).iloc[:400])
 def test_constant_range_atr_reference(self):
  df=fixture(120);df[['Open','High','Low','Close']]=[100,101,99,100]
  f=calculate(df)
  self.assertAlmostEqual(f.ce_long.iloc[21],94);self.assertAlmostEqual(f.ce_short.iloc[21],106)
  self.assertAlmostEqual(f.ut_stop.iloc[9],98)
  self.assertAlmostEqual(f.chop.iloc[-1],100)
  self.assertTrue(f.wt.isna().all());self.assertFalse(f.ut_cross_up.any());self.assertFalse(f.ce_cross_up.any())
 def test_daily_and_weekly_confirmation(self):
  df=fixture(3);df.time=['2026-10-12','2026-10-15','2026-10-16']
  before=datetime(2026,10,16,18,19,tzinfo=ZoneInfo('Europe/Istanbul'));after=before.replace(minute=20)
  self.assertEqual(len(confirmed_frame(df,now=before)[0]),2);self.assertEqual(len(confirmed_frame(df,now=after)[0]),3)
  weeks=df.iloc[:1].copy();self.assertTrue(confirmed_frame(weeks,'1wk',before)[0].empty);self.assertEqual(len(confirmed_frame(weeks,'1wk',after)[0]),1)
  df.time=['2026-10-12','2026-10-15','2027-01-01'];self.assertEqual(confirmed_frame(df,now=after)[1],1)
 def test_bad_bars_and_dates_rejected(self):
  for field,value in [('High',0),('Volume',-1),('Close',float('nan')),('time','bad')]:
   df=fixture();df.loc[60,field]=value
   with self.assertRaises(ValueError):calculate(df)
  df=fixture();df.loc[60,'time']=df.loc[59,'time']
  with self.assertRaises(ValueError):calculate(df)
 def test_payload_finite_and_source_times(self):
  import json
  df=fixture();s=snapshot(df);p=chart_series(df)
  self.assertEqual(s['community_status'],'OK');self.assertEqual(s['community_as_of'],df.time.iloc[-1])
  self.assertIn('wt',p['series']);json.dumps(p,allow_nan=False);json.dumps(s,allow_nan=False)
  times=set(df.time);self.assertTrue(all(x['time'] in times for series in p['series'].values() for x in series))
 def test_short_history_is_explicit(self):
  self.assertEqual(snapshot(fixture(20))['community_status'],'INSUFFICIENT_DATA')
  self.assertEqual(chart_series(fixture(20))['series'],{})
 def test_costs_and_no_success_claim(self):
  df=fixture();a=evaluate(df,0);b=evaluate(df,60)
  self.assertEqual(a['status'],'OK');trades=0
  for x,y in zip(a['results'],b['results']):
   self.assertEqual(x['evidence'],'UNVALIDATED')
   for period in ['early','late']:
    self.assertEqual(x[period]['trades'],y[period]['trades']);trades+=x[period]['trades']
    if x[period]['trades']:self.assertAlmostEqual(x[period]['mean_net_pct']-y[period]['mean_net_pct'],.6,places=2)
  self.assertGreater(trades,0)
 def test_chart_api_contains_community_series(self):
  from fastapi.testclient import TestClient
  from app.main import app
  from app import market_data
  df=fixture();rows=df.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'}).to_dict('records')
  market_data._CHART_CACHE.clear()
  with patch('app.market_data.yahoo_rows',return_value={'ticker':'TEST','period':'5y','interval':'1d','currency':'TRY','candles':rows}):
   response=TestClient(app).get('/api/chart/TEST?period=5y&interval=1d')
  self.assertEqual(response.status_code,200)
  data=response.json();self.assertTrue(data['community']['series']['wt']);self.assertEqual(data['community']['series']['wt'][-1]['time'],rows[-1]['time'])
 def test_api_symbol_validation_and_data_failure(self):
  from fastapi.testclient import TestClient
  from app.main import app
  client=TestClient(app)
  self.assertEqual(client.get('/api/community-research/BAD!?cost_bps=30').status_code,422)
  with patch('app.market_data.yahoo_rows',side_effect=ValueError('provider secret')):
   d=client.get('/api/community-research/ASELS').json();self.assertEqual(d['status'],'NO_DATA');self.assertNotIn('secret',str(d))
  self.assertEqual(client.get('/api/community-catalog').status_code,200)
if __name__=='__main__':unittest.main()
