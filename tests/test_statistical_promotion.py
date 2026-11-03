import unittest
from app.statistical_promotion import bootstrap_confidence

class StatisticalPromotionTests(unittest.TestCase):
    def curve(self,steps=40,edge=.12,bench=.004):
        rows=[];ex=0.0;b=100.0
        rows.append({'excess_pct':ex,'benchmark_equity':b})
        for i in range(steps):
            ex+=edge
            b*=1+(bench if i%3==0 else (-bench if i%3==1 else 0))
            rows.append({'excess_pct':ex,'benchmark_equity':b})
        return rows
    def test_positive_stable_edge_passes(self):
        r=bootstrap_confidence(self.curve(),simulations=1500,seed=61,test_count=3)
        self.assertEqual(r['status'],'PASS')
        self.assertGreater(r['bootstrap']['ci_low'],0)
    def test_small_sample_observes(self):
        r=bootstrap_confidence(self.curve(steps=10),simulations=1000)
        self.assertEqual(r['status'],'INSUFFICIENT_STATISTICAL_SAMPLE')
    def test_negative_edge_does_not_pass(self):
        r=bootstrap_confidence(self.curve(edge=-.08),simulations=1500,seed=61,test_count=3)
        self.assertEqual(r['status'],'OBSERVE')
        self.assertIn('BOOTSTRAP_LOWER_BOUND_NOT_POSITIVE',r['reasons'])

if __name__=='__main__':unittest.main()
