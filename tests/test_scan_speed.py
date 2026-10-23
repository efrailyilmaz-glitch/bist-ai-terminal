import os, tempfile, threading, unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from unittest.mock import patch
import numpy as np
import pandas as pd
from app import auto_paper as auto,market_data as market

class ScanSpeedTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,23,11,0,tzinfo=auto.TR)
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'BIST_AUTO_PAPER_DIR':self.temp.name});self.env.start()
        market._DAILY_CACHE.clear();market._BENCH_CACHE['ts']=0
        c=100+np.arange(260)*.1+np.sin(np.arange(260)/4)
        self.df=pd.DataFrame({'Open':c-.1,'High':c+1,'Low':c-1,'Close':c,'Volume':2_000_000},index=pd.bdate_range(end='2026-10-23',periods=260))
    def tearDown(self):
        market._DAILY_CACHE.clear();market._BENCH_CACHE['ts']=0
        self.env.stop();self.temp.cleanup()
    def account(self,positions=False):
        token=auto.create_account()['token'];key=auto._key(token);a=auto._read(key);a['enabled']=True
        if positions:
            a['cash']=990_000;a['positions']['TEST']={'quantity':100,'avg':100.,'fees':0.,'opened_at':self.now.isoformat(),'entry_bar':self.now.isoformat(),'stop':96.,'target':108.,'reason':'fixture'}
        auto._write(key,a);return key
    def test_daily_cache_reuses_snapshot_without_mutating_other_consumers(self):
        with patch.object(market.yf,'download',return_value=self.df) as fetch:
            first=market.daily_frames(['TEST'])['TEST'];first.iloc[0,0]=-1
            second=market.daily_frames(['TEST'])['TEST']
            self.assertGreater(second.iloc[0,0],0);self.assertEqual(fetch.call_count,1)
            self.assertEqual(first.attrs['fetched_at'],second.attrs['fetched_at'])
    def test_parallel_consumers_share_one_inflight_download(self):
        started=threading.Event();release=threading.Event();waiting=threading.Event()
        def download(*args,**kwargs):started.set();self.assertTrue(release.wait(3));return self.df
        with patch.object(market.yf,'download',side_effect=download) as fetch,ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(market.daily_frames,['TEST']);self.assertTrue(started.wait(1))
            event=market._DAILY_FLIGHTS['TEST'];original=event.wait
            def wait(timeout):waiting.set();return original(timeout)
            with patch.object(event,'wait',side_effect=wait):
                second=pool.submit(market.daily_frames,['TEST']);self.assertTrue(waiting.wait(1));release.set()
                self.assertIn('TEST',first.result(timeout=2));self.assertIn('TEST',second.result(timeout=2))
            self.assertEqual(fetch.call_count,1);self.assertFalse(market._DAILY_FLIGHTS)
    def test_failure_does_not_poison_cache_or_leave_locked_flights(self):
        clock=[1000.]
        with patch.object(market.time,'time',side_effect=lambda:clock[0]),patch.object(market.yf,'download',side_effect=[ValueError('offline'),self.df]) as fetch:
            self.assertEqual(market.daily_frames(['TEST']),{});self.assertFalse(market._DAILY_FLIGHTS)
            self.assertEqual(market.daily_frames(['TEST']),{});self.assertEqual(fetch.call_count,1)
            clock[0]+=31;self.assertIn('TEST',market.daily_frames(['TEST']));self.assertEqual(fetch.call_count,2)
    def test_close_boundary_invalidates_pre_close_cache(self):
        with patch.object(market,'daily_epoch',side_effect=['2026-10-22','2026-10-23']),patch.object(market.yf,'download',return_value=self.df) as fetch:
            market.daily_frames(['TEST']);market.daily_frames(['TEST']);self.assertEqual(fetch.call_count,2)
    def test_regular_and_auto_scans_share_raw_data_but_not_open_bar_signals(self):
        with patch.object(market.yf,'download',return_value=self.df) as fetch:
            normal=market._scan_chunk(['TEST'],0.,0.)
            closed=auto.closed_signals(['TEST'],self.now)
            normal_again=market._scan_chunk(['TEST'],0.,0.)
            self.assertEqual(fetch.call_count,2)
            self.assertEqual([c.args[0] for c in fetch.call_args_list],[['TEST.IS'],['XU100.IS']])
            self.assertEqual(normal[0]['as_of'],'2026-10-23');self.assertEqual(closed[0]['as_of'],'2026-10-22')
            self.assertEqual(normal[0]['fetched_at'],normal_again[0]['fetched_at'])
    def test_partial_packets_continue_immediately_and_complete_scan_cools_down(self):
        key=self.account();u=[{'ticker':'T'+str(i),'source':'KAP'} for i in range(40)]
        with patch('app.universe.get_universe',return_value=u),patch.object(auto,'closed_signals',return_value=[]):
            auto.cycle(key,self.now,lane='scan');a=auto._read(key)
            self.assertEqual(a['scan']['cursor'],20);self.assertTrue(auto.scan_due(a,self.now))
            auto.cycle(key,self.now+timedelta(seconds=1),lane='scan');a=auto._read(key)
            self.assertEqual(a['scan']['completed_count'],40);self.assertEqual(a['scan']['duration_sec'],1.)
            self.assertFalse(auto.scan_due(a,self.now+timedelta(seconds=2)))
            self.assertTrue(auto.scan_due(a,self.now+timedelta(minutes=11)))
    def test_failed_scan_backs_off_instead_of_hammering_provider(self):
        key=self.account()
        with patch('app.universe.get_universe',side_effect=ValueError('offline')):auto.cycle(key,self.now,lane='scan')
        a=auto._read(key);self.assertFalse(auto.scan_due(a,self.now+timedelta(seconds=1)));self.assertTrue(auto.scan_due(a,self.now+timedelta(seconds=31)))
    def test_blocked_daily_download_does_not_block_stop_execution_or_lose_ledger(self):
        key=self.account(positions=True);started=threading.Event();release=threading.Event()
        def slow(*args):started.set();self.assertTrue(release.wait(4));return []
        q={'start':(self.now+timedelta(minutes=15)).isoformat(),'at':(self.now+timedelta(minutes=30)).isoformat(),'open':90.,'high':91.,'low':89.,'close':90.,'volume':1_000_000}
        with patch('app.universe.get_universe',return_value=[{'ticker':'TEST','source':'KAP'}]),patch.object(auto,'closed_signals',side_effect=slow),patch.object(auto,'latest_quote',return_value=q),ThreadPoolExecutor(max_workers=2) as pool:
            scan=pool.submit(auto.cycle,key,self.now+timedelta(minutes=31),'scan');self.assertTrue(started.wait(1))
            try:
                risk=pool.submit(auto.cycle,key,self.now+timedelta(minutes=31),'risk');risk.result(timeout=2)
                a=auto._read(key);self.assertFalse(a['positions']);self.assertEqual(a['orders'][0]['side'],'SELL');self.assertFalse(scan.done())
            finally:release.set()
            scan.result(timeout=2)
        a=auto._read(key);self.assertFalse(a['positions']);self.assertEqual(len(a['orders']),1);self.assertLess(a['realized'],0)
