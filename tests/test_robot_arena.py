import copy,os,tempfile,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from unittest.mock import patch
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from app import auto_paper as p,robot_arena as a,robot_strategies as s

class RobotArenaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'BIST_ROBOT_ARENA_DIR':self.temp.name+'/arena','BIST_AUTO_PAPER_DIR':self.temp.name+'/auto'});self.env.start()
        self.now=datetime(2026,10,23,11,0,tzinfo=p.TR);self.token='x'*43;self.key=p._key(self.token)
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def row(self):
        return {'ticker':'TEST','as_of':'2026-10-22','history_bars':250,'signal_guard':{'status':'CLEAR'},'bar_provisional':False,'price':100.,'atr':2.,'short_score':82.,'long_score':78.,'supertrend':'BULLISH','macd_hist':1.,'adx':30.,'rsi':55.,'avg_value_turnover_20':50_000_000.,'risk':40.,'relative_strength_20':5.,'relative_strength_60':10.,'robot_features':{'alpha_bull':True,'alpha_bear':False,'ott_bull':True,'ott_bear':False,'tott_bull':True,'tott_bear':False,'ema50_bull':True,'ema20_bull':True,'benchmark_bull':True,'breakout_prior20':True,'breadth_pct':80.,'volume_confirm':1.5,'close_location':.8,'upper_wick':.1,'gap_atr':.5,'extension_atr':1.}}
    def quote(self,minute=0,px=100.,high=101.,low=99.):
        start=self.now+timedelta(minutes=minute);return {'start':start.isoformat(),'at':(start+timedelta(minutes=15)).isoformat(),'open':px,'close':px,'high':high,'low':low,'volume':1_000_000.}
    def running(self):
        root=a.fresh();root['enabled']=True;root['started_at']=self.now.isoformat()
        for b in root['bots'].values():b['enabled']=True
        return root
    def test_equal_capital_policy_no_copied_vendor_claims(self):
        root=a.fresh();self.assertEqual(len(root['bots']),6)
        for b in root['bots'].values():self.assertEqual(b['capital'],1_000_000);self.assertFalse(b['enabled']);self.assertFalse(b['config']['allow_short']);self.assertEqual(b['config'],root['config'])
        self.assertEqual({b['id'] for b in s.CATALOG},set(root['bots']))
        self.assertTrue(all(b['status']!='CONNECTED' for b in s.EXTERNAL))
    def test_independent_accounts_idempotent_creation_and_locked_common_policy(self):
        a.create(self.token);a.create('y'*43);a.configure(self.token,{'fee_bps':20,'allow_short':True});a.create(self.token)
        self.assertEqual(a.snapshot(self.token)['config']['fee_bps'],20);self.assertEqual(a.snapshot('y'*43)['config']['fee_bps'],10)
        for b in a._read(self.key)['bots'].values():self.assertEqual(b['config']['fee_bps'],20)
        with patch.object(a,'start_worker'):a.control(self.token,'start')
        with self.assertRaises(ValueError):a.configure(self.token,{'fee_bps':1})
        with self.assertRaises(ValueError):a.control(self.token,'reset')
    def test_config_validation_is_atomic(self):
        a.create(self.token)
        for payload in [{'fee_bps':float('nan')},{'slippage_bps':0},{'allow_short':1},{'fee_bps':20,'live':True}]:
            with self.assertRaises(ValueError):a.configure(self.token,payload)
        self.assertEqual(a.snapshot(self.token)['config']['fee_bps'],10)
    def test_all_strategies_guarded_and_no_symbol_bias(self):
        r=self.row()
        for sid in ('baseline','alphatrend','ott','tott','momentum','codex'):
            self.assertEqual(s.entry(sid,r)[0],'BUY');other=copy.deepcopy(r);other['ticker']='AHGAZ';self.assertEqual(s.entry(sid,r),s.entry(sid,other))
            for k,v in [('bar_provisional',True),('history_bars',100),('atr',float('nan')),('avg_value_turnover_20',1)]:
                bad=copy.deepcopy(r);bad[k]=v;self.assertIsNone(s.entry(sid,bad))
            bad=copy.deepcopy(r);bad['signal_guard']['status']='WAIT';self.assertIsNone(s.entry(sid,bad))
    def test_codex_requires_every_confirmation_and_has_exit(self):
        for k,v in [('benchmark_bull',False),('breadth_pct',54),('volume_confirm',1.1),('close_location',.5),('upper_wick',.5),('gap_atr',2),('extension_atr',3),('breakout_prior20',False)]:
            r=self.row();r['robot_features'][k]=v;self.assertIsNone(s.entry('codex',r),k)
        r=self.row();r['robot_features']['ema20_bull']=False;self.assertTrue(s.exit_reason('codex',r,{'quantity':1}))
    def test_full_coverage_and_breadth_gate_precede_entries(self):
        root=self.running();a.apply_scan(root,[self.row()],100,self.now)
        self.assertTrue(all(not b['pending'] for b in root['bots'].values()))
        a.apply_scan(root,[self.row()],1,self.now)
        self.assertTrue(all('TEST' in b['pending'] for b in root['bots'].values()));self.assertEqual(root['scan']['breadth_pct'],100)
        root=self.running();r=self.row();r['as_of']='2026-10-20';a.apply_scan(root,[r],1,self.now);self.assertFalse(root['bots']['codex']['pending'])
    def test_same_costs_next_bar_fills_and_open_loss_in_leaderboard(self):
        root=self.running();a.apply_scan(root,[self.row()],1,self.now+timedelta(minutes=1))
        for b in root['bots'].values():
            p.process_quote(b,'TEST',self.quote(),self.now+timedelta(minutes=16));self.assertFalse(b['orders'])
            p.process_quote(b,'TEST',self.quote(15),self.now+timedelta(minutes=31));self.assertEqual(len(b['orders']),1);self.assertGreater(b['orders'][0]['fee'],0)
            m=a.metrics(b);self.assertLess(m['return_pct'],0);self.assertEqual(m['closed_trades'],0);self.assertIsNone(m['profit_factor'])
        self.assertEqual(len({b['orders'][0]['price'] for b in root['bots'].values()}),1)
    def test_scan_fetches_once_for_all_bots_and_merges_stop_lane(self):
        root=self.running();b=root['bots']['baseline'];p.choose(b,[self.row()],1,self.now);p.process_quote(b,'TEST',self.quote(),self.now+timedelta(minutes=16));a._write(self.key,root)
        entered=threading.Event();release=threading.Event()
        def slow(*args,**kwargs):entered.set();self.assertTrue(release.wait(5));return [self.row()]
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'KAP'}]),patch.object(p,'closed_signals',side_effect=slow) as fetch,patch.object(p,'latest_quote',return_value=self.quote(15,90,91,89)),ThreadPoolExecutor(max_workers=2) as pool:
            future=pool.submit(a.cycle,self.key,self.now+timedelta(minutes=31),'scan');self.assertTrue(entered.wait(2));a.cycle(self.key,self.now+timedelta(minutes=31),'risk');self.assertFalse(a._read(self.key)['bots']['baseline']['positions']);release.set();future.result(timeout=5)
        saved=a._read(self.key);self.assertFalse(saved['bots']['baseline']['positions']);self.assertLess(saved['bots']['baseline']['max_drawdown_pct'],10);self.assertGreater(saved['bots']['baseline']['max_drawdown_pct'],0);self.assertEqual(fetch.call_count,1);self.assertTrue(fetch.call_args.kwargs['enrich'])
    def test_pause_during_download_wins_no_queued_entries(self):
        a._write(self.key,self.running())
        def slow(*args,**kwargs):
            with patch.object(a,'start_worker'):a.control(self.token,'pause')
            return [self.row()]
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'KAP'}]),patch.object(p,'closed_signals',side_effect=slow):a.cycle(self.key,self.now,'scan')
        root=a._read(self.key);self.assertFalse(root['enabled']);self.assertTrue(all(not b['pending'] for b in root['bots'].values()))
    def test_pause_cancels_entries_but_preserves_protection_and_close_all(self):
        root=self.running();a.apply_scan(root,[self.row()],1,self.now);p.process_quote(root['bots']['codex'],'TEST',self.quote(),self.now+timedelta(minutes=16));a._write(self.key,root)
        with patch.object(a,'start_worker'):a.control(self.token,'pause')
        root=a._read(self.key);self.assertTrue(root['bots']['codex']['positions']);self.assertTrue(all(not b['pending'] for b in root['bots'].values()))
        with patch.object(a,'start_worker'):a.control(self.token,'close_all')
        self.assertEqual(a._read(self.key)['bots']['codex']['pending']['TEST']['side'],'SELL')
    def test_benchmark_never_starts_before_decision_and_is_separate(self):
        root=self.running();root['started_at']=(self.now+timedelta(minutes=1)).isoformat();a._write(self.key,root)
        with patch.object(p,'latest_quote',return_value=self.quote()):a.cycle(self.key,self.now+timedelta(minutes=16),'risk')
        self.assertFalse(a._read(self.key)['benchmark'])
        with patch.object(p,'latest_quote',return_value=self.quote(15)):a.cycle(self.key,self.now+timedelta(minutes=31),'risk')
        d=a.snapshot(self.token);self.assertEqual(d['benchmark']['return_pct'],0);self.assertTrue(all(not b['orders'] for b in d['bots']))
    def test_fallback_universe_and_scan_failure_never_fake_results(self):
        a._write(self.key,self.running())
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'FALLBACK'}]):a.cycle(self.key,self.now)
        root=a._read(self.key);self.assertIn('KAP',root['error']);self.assertTrue(all(not b['pending'] for b in root['bots'].values()))
    def test_quotes_download_once_and_ledger_totals_survive_display_retention(self):
        root=self.running();a.apply_scan(root,[self.row()],1,self.now);a._write(self.key,root)
        with patch.object(p,'latest_quote',return_value=self.quote()) as fetch:a.cycle(self.key,self.now+timedelta(minutes=16),'risk')
        self.assertEqual(fetch.call_count,2)  # TEST once across all six bots, plus benchmark
        root=a._read(self.key)
        for b in root['bots'].values():
            p.queue(b,'TEST','SELL','exit',self.now+timedelta(minutes=16));p.process_quote(b,'TEST',self.quote(30,102,103,101),self.now+timedelta(minutes=46))
            m=a.metrics(b);b['orders']=[];later=a.metrics(b)
            self.assertEqual(m['fees_paid'],later['fees_paid']);self.assertEqual(later['closed_trades'],1);self.assertGreater(later['return_pct'],0)
            self.assertAlmostEqual(b['cash']-b['capital'],b['realized'],places=6)
    def test_common_short_gate_and_short_collateral_accounting(self):
        root=self.running();r=self.row();r.update({'short_score':20.,'long_score':25.,'rsi':40.,'supertrend':'BEARISH','macd_hist':-1.})
        for k in ('alpha','ott','tott'):r['robot_features'][k+'_bull']=False;r['robot_features'][k+'_bear']=True
        a.apply_scan(root,[r],1,self.now);self.assertTrue(all(not b['pending'] for b in root['bots'].values()))
        for b in root['bots'].values():b['config']['allow_short']=True
        a.apply_scan(root,[r],1,self.now)
        for sid in ('baseline','alphatrend','ott','tott'):
            b=root['bots'][sid];p.process_quote(b,'TEST',self.quote(),self.now+timedelta(minutes=16));self.assertLess(b['positions']['TEST']['quantity'],0);self.assertLess(b['cash'],b['capital'])
        self.assertFalse(root['bots']['codex']['pending']);self.assertFalse(root['bots']['momentum']['pending'])
    def test_ott_is_causal_and_features_use_confirmed_history(self):
        idx=pd.bdate_range(end='2026-10-23',periods=260);v=100+np.arange(260)*.1+np.sin(np.arange(260)/4)
        df=pd.DataFrame({'Open':v-.1,'High':v+1,'Low':v-1,'Close':v,'Volume':2_000_000.},index=idx)
        for length in (2,40):
            for out,prefix in zip(s.ott(df.Close,length,1.4),s.ott(df.Close.iloc[:220],length,1.4)):self.assertAlmostEqual(out.iloc[219],prefix.iloc[-1],places=10)
        original=df.copy();df.iloc[-1]=[1_000_000,1_000_001,999_999,1_000_000,2_000_000]
        with patch('app.market_data.daily_frames',return_value={'TEST':df,'XU100':original}):r=p.closed_signals(['TEST'],self.now,enrich=True)[0]
        self.assertEqual(r['as_of'],'2026-10-22');self.assertEqual(r['robot_features'],s.features(original.iloc[:-1],original.iloc[:-1]))
    def test_api_auth_and_no_live_or_reset_routes(self):
        from app.main import app
        c=TestClient(app);self.assertEqual(c.get('/api/robot-arena/account').status_code,400);h={'X-Bist-Paper-Token':self.token}
        self.assertFalse(c.get('/api/robot-arena/account',headers=h).json()['exists']);d=c.post('/api/robot-arena/create',headers=h).json();self.assertFalse(d['live_execution']);self.assertEqual(len(d['bots']),6)
        self.assertEqual(c.post('/api/robot-arena/control',headers=h,json={'action':'live'}).status_code,400)
        self.assertNotIn('signal_keys',str(d));self.assertNotIn(self.key,str(d));self.assertNotIn(self.token,str(d))

if __name__=='__main__':unittest.main()
