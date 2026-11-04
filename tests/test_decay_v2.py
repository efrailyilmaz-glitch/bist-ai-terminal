import unittest
from app.decay_v2 import detect_trade_decay,detect_xs_decay

class DecayV2Tests(unittest.TestCase):
    def test_trade_expectancy_confident_flip_decays(self):
        orders=[]
        for i in range(12):orders.append({'pnl':100.0})
        for i in range(12):orders.append({'pnl':-120.0})
        bot={'orders':list(reversed(orders)),'curve':[{'equity':1_000_000+i*100} for i in range(50)]}
        r=detect_trade_decay(bot,min_trades=24,window=12)
        self.assertEqual(r['status'],'DECAY')
        self.assertTrue(any(x in r['flags'] for x in ['EXPECTANCY_SIGN_FLIP','RECENT_EXPECTANCY_CONFIDENTLY_NEGATIVE']))

    def test_xs_recent_excess_sign_flip_decays(self):
        curve=[];ex=0.0;bench=1_000_000
        curve.append({'excess_pct':ex,'benchmark_equity':bench})
        for i in range(20):
            ex+=.12;bench*=1.004 if i%2==0 else .996
            curve.append({'excess_pct':ex,'benchmark_equity':bench})
        for i in range(20):
            ex-=.15;bench*=1.004 if i%2==0 else .996
            curve.append({'excess_pct':ex,'benchmark_equity':bench})
        history={'curve':list(reversed(curve)),'rebalances':[]}
        r=detect_xs_decay(history,min_steps=30,window=15)
        self.assertEqual(r['status'],'DECAY')
        self.assertIn('EXCESS_SIGN_FLIP',r['flags'])

    def test_stable_positive_xs_edge_not_decay(self):
        curve=[];ex=0.0;bench=1_000_000
        curve.append({'excess_pct':ex,'benchmark_equity':bench})
        for i in range(45):
            ex+=.05;bench*=1.002 if i%2==0 else .999
            curve.append({'excess_pct':ex,'benchmark_equity':bench})
        r=detect_xs_decay({'curve':list(reversed(curve)),'rebalances':[]},min_steps=30,window=15)
        self.assertEqual(r['status'],'STABLE')

if __name__=='__main__':unittest.main()
