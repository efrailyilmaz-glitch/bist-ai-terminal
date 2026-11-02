import unittest
from unittest.mock import patch
from app.trade_reality import trade_reality

def session(date,drift=.001,vol=.003):
    out=[];p=100.0;slot=40
    for i in range(28):
        o=p
        c=p*(1+drift if i%3 else 1-drift/2)
        h=max(o,c)*(1+vol)
        l=min(o,c)*(1-vol)
        out.append({'time':1_700_000_000+i*900,'open':o,'high':h,'low':l,'close':c,'volume':1_000_000,'slot':slot+i})
        p=c
    return out

class TradeRealityTests(unittest.TestCase):
    def days(self):
        return {f'2026-10-{d:02d}':session(f'2026-10-{d:02d}',.001+(d%3)*.0002,.0025+(d%4)*.0003) for d in range(1,22)}
    def test_replay_is_deterministic_and_bounded(self):
        with patch('app.trade_reality._session_rows',return_value=self.days()):
            a=trade_reality('TEST',100,97,106,'BUY',simulations=2000,seed=41,block_bars=3)
            b=trade_reality('TEST',100,97,106,'BUY',simulations=2000,seed=41,block_bars=3)
        self.assertEqual(a,b);self.assertEqual(a['status'],'OK')
        self.assertAlmostEqual(a['target_first_pct']+a['stop_first_pct']+a['neither_pct'],100,places=1)
        self.assertIn(a['verdict'],{'FAVORABLE','MARGINAL','UNFAVORABLE'})
    def test_short_geometry_supported(self):
        with patch('app.trade_reality._session_rows',return_value=self.days()):
            x=trade_reality('TEST',100,103,94,'SHORT',simulations=1000,seed=7)
        self.assertEqual(x['side'],'SHORT');self.assertEqual(x['status'],'OK')
    def test_bad_geometry_rejected(self):
        with self.assertRaises(ValueError):trade_reality('TEST',100,101,105,'BUY')
    def test_too_few_sessions_is_explicit(self):
        with patch('app.trade_reality._session_rows',return_value={'2026-10-01':session('2026-10-01')}):
            x=trade_reality('TEST',100,97,106)
        self.assertEqual(x['status'],'INSUFFICIENT_DATA')

if __name__=='__main__':unittest.main()
