import unittest
import numpy as np
import pandas as pd
from app.adversarial_v2 import inject_multiday,stress,cross_sectional_stress,MULTI_SCENARIOS

def fixture(n=180,shift=0):
    rng=np.random.default_rng(75+shift)
    c=100+shift+np.arange(n)*.06+np.sin(np.arange(n)/9)*1.2
    return pd.DataFrame({'Open':c-.15,'High':c+.9,'Low':c-.9,'Close':c,
                         'Volume':1_800_000+rng.integers(0,250_000,n)})

class AdversarialV2Tests(unittest.TestCase):
    def test_injections_preserve_prefix_and_valid_ohlc(self):
        df=fixture()
        for name in MULTI_SCENARIOS:
            x=inject_multiday(df,name)
            pd.testing.assert_frame_equal(x.iloc[:-8],df[['Open','High','Low','Close','Volume']].iloc[:-8],check_dtype=False)
            self.assertTrue((x.High>=x[['Open','Close','Low']].max(axis=1)).all())
            self.assertTrue((x.Low<=x[['Open','Close','High']].min(axis=1)).all())
            self.assertTrue((x.Volume>=0).all())
    def test_stress_is_deterministic(self):
        a=stress(fixture());b=stress(fixture())
        self.assertEqual(a,b)
        self.assertEqual(a['version'],2)
        self.assertEqual(a['total'],len(MULTI_SCENARIOS))
        self.assertIn('multi-bar',a['limits'])
    def test_cross_sectional_stress_is_deterministic(self):
        frames={f'T{i}':fixture(180,i) for i in range(6)}
        a=cross_sectional_stress(frames);b=cross_sectional_stress(frames)
        self.assertEqual(a,b)
        self.assertEqual(a['status'],'OK')
        self.assertEqual(a['names'],6)
    def test_short_data_rejected(self):
        with self.assertRaises(ValueError):stress(fixture(40))
        self.assertEqual(cross_sectional_stress({'A':fixture()},min_names=5)['status'],'INSUFFICIENT_NAMES')

if __name__=='__main__':unittest.main()
