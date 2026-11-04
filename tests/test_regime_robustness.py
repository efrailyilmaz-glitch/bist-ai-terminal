import unittest
from app.regime_robustness import evaluate

class RegimeRobustnessTests(unittest.TestCase):
    def history(self,edge_map=None,steps=80):
        edge_map=edge_map or {'BULL':.12,'BEAR':.10,'RANGE':.08,'HIGH_VOL':.09}
        curve=[{'excess_pct':0.0,'benchmark_equity':100.0}]
        ex=0.0;b=100.0
        seq=[]
        for i in range(steps):
            if i%4==0: br=.008
            elif i%4==1: br=-.008
            elif i%4==2: br=.0005
            else: br=.02 if (i//4)%2==0 else -.02
            b*=1+br
            if abs(br)>=.015: reg='HIGH_VOL'
            elif br>.003: reg='BULL'
            elif br<-.003: reg='BEAR'
            else: reg='RANGE'
            ex+=edge_map.get(reg,0)
            curve.append({'excess_pct':ex,'benchmark_equity':b})
        return {'curve':list(reversed(curve))}
    def test_balanced_regimes_pass(self):
        r=evaluate(self.history())
        self.assertEqual(r['status'],'PASS')
        self.assertGreaterEqual(r['populated_regimes'],3)
    def test_bad_bear_and_high_vol_observes(self):
        r=evaluate(self.history({'BULL':.12,'BEAR':-.10,'RANGE':.08,'HIGH_VOL':-.12}))
        self.assertEqual(r['status'],'OBSERVE')
        self.assertTrue(any(x in r['reasons'] for x in ['BEAR_REGIME_EDGE_NEGATIVE','HIGH_VOL_EDGE_NEGATIVE']))
    def test_small_sample_waits(self):
        r=evaluate(self.history(steps=10))
        self.assertEqual(r['status'],'INSUFFICIENT_REGIME_SAMPLE')

if __name__=='__main__':unittest.main()
