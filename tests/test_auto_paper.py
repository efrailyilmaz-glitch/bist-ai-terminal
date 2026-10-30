import copy, json, os, tempfile, unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import auto_paper as m

class AutoPaperTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,23,11,0,tzinfo=m.TR)
        self.a=m.fresh();self.a['enabled']=True
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'BIST_AUTO_PAPER_DIR':self.temp.name});self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def row(self,code='TEST',short=False):
        return {'ticker':code,'history_bars':250,'as_of':'2026-10-22','signal_guard':{'status':'CLEAR'},'short_score':20 if short else 82,'long_score':25 if short else 78,'supertrend':'BEARISH' if short else 'BULLISH','macd_hist':-1. if short else 1.,'adx':30.,'rsi':40. if short else 55.,'risk':40,'atr':2.,'price':100.,'avg_value_turnover_20':50_000_000.}
    def quote(self,minutes=0,price=100.,high=101.,low=99.,volume=1_000_000):
        start=self.now+timedelta(minutes=minutes)
        return {'start':start.isoformat(),'at':(start+timedelta(minutes=15)).isoformat(),'open':price,'close':price,'high':high,'low':low,'volume':volume}
    def enter(self,short=False):
        m.choose(self.a,[self.row(short=short)],1,self.now)
        q=self.quote();m.process_quote(self.a,'TEST',q,self.now+timedelta(minutes=16));return q
    def test_long_short_round_trip_includes_fees_and_slippage(self):
        for short in [False,True]:
            self.a=m.fresh();self.a['enabled']=True;self.enter(short)
            p=self.a['positions']['TEST'];self.assertLess(p['quantity'],0) if short else self.assertGreater(p['quantity'],0)
            self.assertLess(self.a['cash'],1_000_000)
            m.queue(self.a,'TEST','COVER' if short else 'SELL','exit',self.now+timedelta(minutes=16))
            q=self.quote(30,98 if short else 102,103.,97.)
            m.process_quote(self.a,'TEST',q,self.now+timedelta(minutes=46))
            self.assertFalse(self.a['positions']);self.assertAlmostEqual(self.a['cash']-1_000_000,self.a['realized'],places=5)
            self.assertGreater(self.a['orders'][0]['fee'],0);self.assertNotEqual(self.a['orders'][0]['price'],q['close'])
    def test_no_same_or_pre_decision_bar_fill(self):
        m.choose(self.a,[self.row()],1,self.now+timedelta(minutes=1))
        q=self.quote();m.process_quote(self.a,'TEST',q,self.now+timedelta(minutes=16));self.assertFalse(self.a['orders'])
        later=self.quote(15);m.process_quote(self.a,'TEST',later,self.now+timedelta(minutes=31));self.assertEqual(len(self.a['orders']),1)
        m.process_quote(self.a,'TEST',later,self.now+timedelta(minutes=32));self.assertEqual(len(self.a['orders']),1)
    def test_stale_future_invalid_and_weekend_quotes_rejected(self):
        for q,now in [(self.quote(),self.now+timedelta(hours=2)),(self.quote(30),self.now),(self.quote(volume=0),self.now+timedelta(minutes=16)),(self.quote(high=90),self.now+timedelta(minutes=16)),(self.quote(),self.now+timedelta(days=1))]:
            self.assertFalse(m.valid_quote(q,now))
    def test_stop_before_target_and_gap_loss(self):
        self.enter();p=self.a['positions']['TEST']
        q=self.quote(15,90.,115.,89.)
        m.process_quote(self.a,'TEST',q,self.now+timedelta(minutes=31))
        self.assertFalse(self.a['positions']);self.assertLess(self.a['orders'][0]['price'],90.);self.assertLess(self.a['orders'][0]['pnl'],0)
    def test_entry_bar_cannot_trigger_prior_intrabar_stop(self):
        r=self.row();r['atr']=.5;m.choose(self.a,[r],1,self.now)
        q=self.quote(high=101,low=98);m.process_quote(self.a,'TEST',q,self.now+timedelta(minutes=16))
        self.assertEqual(len(self.a['orders']),1);self.assertTrue(self.a['positions'])
    def test_guard_and_partial_scan_no_entries(self):
        for state in ['WAIT','BLOCK','UNKNOWN']:
            r=self.row();r['signal_guard']['status']=state;self.assertIsNone(m.signal(r))
        m.choose(self.a,[self.row()],100,self.now);self.assertFalse(self.a['pending'])
        r=self.row();r['as_of']='2026-10-19';m.choose(self.a,[r],1,self.now);self.assertFalse(self.a['pending'])
    def test_short_disabled_and_signal_date_dedup(self):
        self.a['config']['allow_short']=False;m.choose(self.a,[self.row(short=True)],1,self.now);self.assertFalse(self.a['pending'])
        m.choose(self.a,[self.row()],1,self.now);self.assertEqual(len(self.a['pending']),1)
        self.a['pending'].clear();m.choose(self.a,[self.row()],1,self.now);self.assertFalse(self.a['pending'])
    def test_risk_size_gross_limits_and_volume_cap(self):
        self.a['config']['gross_pct']=10
        self.enter();v=m.valuation(self.a);self.assertLessEqual(v['gross'],100_000);self.assertLessEqual(abs(self.a['positions']['TEST']['quantity'])*4,5_000)
        m.choose(self.a,[self.row('NEXT')],1,self.now);q=self.quote();m.process_quote(self.a,'NEXT',q,self.now+timedelta(minutes=16));self.assertLessEqual(len(self.a['positions']),1)
    def test_daily_risk_halt_stops_entries_and_queues_exit(self):
        self.enter();m.risk_check(self.a,self.now);self.a['cash']-=30_000
        m.risk_check(self.a,self.now);self.assertEqual(self.a['risk_halt'],'DAILY_LOSS');self.assertEqual(self.a['pending']['TEST']['side'],'SELL')
    def test_borrow_cost_charged_once_per_calendar_day(self):
        self.enter(short=True);m.risk_check(self.a,self.now);m.risk_check(self.a,self.now+timedelta(days=3));cost=self.a['borrow_cost'];self.assertGreater(cost,0)
        m.risk_check(self.a,self.now+timedelta(days=3,minutes=1));self.assertEqual(cost,self.a['borrow_cost'])
    def test_corporate_action_scale_jump_never_fakes_fill(self):
        self.enter();q=self.quote(15,50,51,49);m.process_quote(self.a,'TEST',q,self.now+timedelta(minutes=31))
        self.assertEqual(len(self.a['orders']),1);self.assertIn('TEST',self.a['quote_errors'])
    def test_accounts_are_isolated_persistent_and_config_atomic(self):
        t1=m.create_account()['token'];t2=m.create_account()['token'];m.configure(t1,{'allow_short':False})
        self.assertFalse(m.snapshot(t1)['config']['allow_short']);self.assertTrue(m.snapshot(t2)['config']['allow_short'])
        with self.assertRaises(ValueError):m.configure(t1,{'risk_pct':float('nan')})
        self.assertEqual(m.snapshot(t1)['config']['risk_pct'],.5)
        self.assertEqual(len(list(m._directory().glob('*.json'))),2)
    def test_pause_cancels_entries_keeps_protective_positions(self):
        token=m.create_account()['token'];key=m._key(token);self.enter();m._write(key,self.a)
        with patch.object(m,'start_worker'):m.control(token,'pause')
        a=m._read(key);self.assertFalse(a['enabled']);self.assertTrue(a['positions']);self.assertFalse(a['pending'])
        with patch.object(m,'start_worker'):m.control(token,'close_all')
        self.assertEqual(m.snapshot(token)['pending']['TEST']['side'],'SELL')
    def test_api_has_no_live_mode_and_auth_is_required(self):
        from app.main import app
        c=TestClient(app);self.assertEqual(c.get('/api/auto-paper/account').status_code,400)
        token=c.post('/api/auto-paper/accounts').json()['token'];headers={'X-Bist-Paper-Token':token}
        d=c.get('/api/auto-paper/account',headers=headers).json();self.assertFalse(d['live_execution']);self.assertEqual(d['mode'],'PAPER')
        self.assertEqual(c.post('/api/auto-paper/control',headers=headers,json={'action':'live'}).status_code,400)
        self.assertEqual(c.post('/api/auto-paper/config',headers=headers,json={'live':True}).status_code,400)
    def test_demo_is_separate_and_exercises_all_four_sides(self):
        r=m.demo();self.assertEqual(r['mode'],'SYNTHETIC_DEMO');self.assertEqual({o['side'] for o in r['orders']},{'BUY','SELL','SHORT','COVER'})
        self.assertTrue(all(o['source']=='SYNTHETIC' for o in r['orders']));self.assertFalse(list(m._directory().glob('*.json')))
    def test_worker_cycle_selects_then_fills_next_bar_and_persists(self):
        token=m.create_account()['token'];key=m._key(token);a=m._read(key);a['enabled']=True;m._write(key,a)
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'KAP'}]),patch.object(m,'closed_signals',return_value=[self.row()]),patch.object(m,'latest_quote',return_value=self.quote()):
            m.cycle(key,self.now);self.assertEqual(len(m._read(key)['orders']),0);self.assertIn('TEST',m._read(key)['pending'])
            m.cycle(key,self.now+timedelta(minutes=16));a=m._read(key);self.assertEqual(len(a['orders']),1);self.assertIn('TEST',a['positions'])
            m.cycle(key,self.now+timedelta(minutes=17));self.assertEqual(len(m._read(key)['orders']),1)
    def test_pause_during_network_fetch_wins(self):
        token=m.create_account()['token'];key=m._key(token);a=m._read(key);a['enabled']=True;m.choose(a,[self.row()],1,self.now);m._write(key,a)
        def quote(*args):
            with patch.object(m,'start_worker'):m.control(token,'pause')
            return self.quote()
        with patch.object(m,'latest_quote',side_effect=quote),patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'KAP'}]),patch.object(m,'closed_signals',return_value=[self.row()]):
            m.cycle(key,self.now+timedelta(minutes=16))
        a=m._read(key);self.assertFalse(a['enabled']);self.assertFalse(a['orders'])
    def test_fallback_universe_never_opens_entries(self):
        token=m.create_account()['token'];key=m._key(token);a=m._read(key);a['enabled']=True;m._write(key,a)
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'FALLBACK'}]):m.cycle(key,self.now)
        a=m._read(key);self.assertFalse(a['pending']);self.assertIn('KAP',a['error'])
    def test_open_daily_bar_is_excluded_from_signal_and_benchmark(self):
        import numpy as np,pandas as pd
        close=100+np.arange(260)*.1+np.sin(np.arange(260)/4)
        df=pd.DataFrame({'Open':close-.1,'High':close+1,'Low':close-1,'Close':close,'Volume':2_000_000},index=pd.bdate_range(end='2026-10-23',periods=260))
        df.iloc[-1]=[1_000_000,1_000_001,999_999,1_000_000,2_000_000]
        with patch('app.market_data.yf.download',return_value=df):out=m.closed_signals(['TEST'],self.now)
        self.assertEqual(out[0]['as_of'],'2026-10-22');self.assertEqual(out[0]['history_bars'],259);self.assertLess(out[0]['price'],200);self.assertFalse(out[0]['bar_provisional'])
    def test_daily_scan_failure_does_not_disable_existing_stop(self):
        self.enter();token=m.create_account()['token'];key=m._key(token);m._write(key,self.a)
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'KAP'}]),patch.object(m,'closed_signals',side_effect=ValueError('daily source offline')),patch.object(m,'latest_quote',return_value=self.quote(15,90,91,89)):
            m.cycle(key,self.now+timedelta(minutes=31))
        a=m._read(key);self.assertFalse(a['positions']);self.assertIn('daily source',a['error'])
