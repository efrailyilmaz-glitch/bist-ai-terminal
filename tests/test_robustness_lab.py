import unittest
import numpy as np
import pandas as pd
from app.robustness_lab import pbo_cscv,walk_forward_surface,stability_map,deflated_sharpe

class RobustnessLabTests(unittest.TestCase):
    def test_pbo_and_surface_are_finite(self):
        rng=np.random.default_rng(7);n=630
        base=rng.normal(.0004,.01,n)
        data={}
        for i in range(8):
            data[f's{i}']=base*(1-.04*i)+rng.normal(0,.003+i*.0002,n)
        r=pd.DataFrame(data)
        p=pbo_cscv(r);w=walk_forward_surface(r)
        self.assertEqual(p['status'],'OK');self.assertTrue(0<=p['pbo_pct']<=100)
        self.assertEqual(w['status'],'OK');self.assertGreater(w['folds'],0)
        self.assertTrue(np.isfinite(w['median_surface_corr']))
    def test_overfit_family_is_not_magically_certified(self):
        rng=np.random.default_rng(9);n=640
        r=pd.DataFrame({f's{i}':rng.normal(0,.012,n) for i in range(10)})
        p=pbo_cscv(r)
        self.assertEqual(p['status'],'OK');self.assertGreaterEqual(p['combinations'],20)
        self.assertIn('proof',p['interpretation'])
    def test_deflated_sharpe_probability_is_bounded(self):
        rng=np.random.default_rng(11);n=700
        signal=rng.normal(.0007,.01,n)
        r=pd.DataFrame({'best':signal,**{f'n{i}':rng.normal(0,.012,n) for i in range(7)}})
        d=deflated_sharpe(r)
        self.assertEqual(d['status'],'OK');self.assertTrue(0<=d['dsr_probability_pct']<=100)
        self.assertEqual(d['trials'],8)

    def test_plateau_reports_width(self):
        rng=np.random.default_rng(2);r=pd.DataFrame({f's{i}':rng.normal(.0003,.01,500) for i in range(5)})
        x=stability_map(r);self.assertEqual(x['candidate_count'],5);self.assertTrue(0<x['plateau_pct']<=100)
    def test_short_samples_rejected(self):
        r=pd.DataFrame({'a':[0.0]*50,'b':[0.0]*50,'c':[0.0]*50})
        self.assertEqual(pbo_cscv(r)['status'],'INSUFFICIENT_DATA')
        self.assertEqual(walk_forward_surface(r)['status'],'INSUFFICIENT_DATA')

if __name__=='__main__':unittest.main()
