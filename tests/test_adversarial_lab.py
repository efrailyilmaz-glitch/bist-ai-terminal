import unittest
import numpy as np
import pandas as pd
from app.adversarial_lab import inject,stress,SCENARIOS

def fixture(n=180):
    rng=np.random.default_rng(33)
    c=100+np.arange(n)*.08+np.sin(np.arange(n)/8)*1.5
    return pd.DataFrame({'Open':c-.2,'High':c+1,'Low':c-1,'Close':c,'Volume':2_000_000+rng.integers(0,300_000,n)})

class AdversarialLabTests(unittest.TestCase):
    def test_all_scenarios_are_causal_and_valid(self):
        df=fixture()
        for name in SCENARIOS:
            x=inject(df,name)
            self.assertEqual(len(x),len(df))
            self.assertTrue((x.High>=x[['Open','Close','Low']].max(axis=1)).all())
            self.assertTrue((x.Low<=x[['Open','Close','High']].min(axis=1)).all())
            self.assertTrue((x.Volume>=0).all())
    def test_stress_report_is_explicit_and_repeatable(self):
        df=fixture();a=stress(df);b=stress(df)
        self.assertEqual(a,b);self.assertEqual(a['total'],len(SCENARIOS))
        self.assertEqual({x['scenario'] for x in a['scenarios']},set(SCENARIOS))
        self.assertIn('Synthetic OHLCV',a['limits'])
    def test_short_or_bad_data_rejected(self):
        with self.assertRaises(ValueError):stress(fixture(20))
        df=fixture();df.loc[df.index[-1],'Close']=np.nan
        with self.assertRaises(ValueError):stress(df)

if __name__=='__main__': unittest.main()
