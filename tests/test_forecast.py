import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from app.forecast_lab import features, neighbors, analyze_frame, EMBARGO

class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(17);n=2300
        c=100*np.exp(np.cumsum(rng.normal(.0002,.018,n)))
        cls.df=pd.DataFrame({'time':pd.bdate_range('2015-01-01',periods=n).strftime('%Y-%m-%d'),
                            'Open':c*.998,'High':c*1.015,'Low':c*.985,'Close':c,
                            'Volume':rng.integers(500000,2000000,n)})

    def test_features_do_not_see_future(self):
        np.testing.assert_allclose(features(self.df).iloc[:900], features(self.df.iloc[:900]), equal_nan=True)

    def test_analog_labels_are_purged_and_do_not_overlap(self):
        x=features(self.df).to_numpy(float)
        for h in (5,20,60):
            matches,_=neighbors(x,1500,h)
            self.assertGreaterEqual(len(matches),12)
            for i,_ in matches: self.assertLess(i+h,1500-EMBARGO)
            for a,(i,_) in enumerate(matches):
                for j,_ in matches[a+1:]: self.assertGreater(abs(i-j),h)

    def test_changing_future_cannot_change_historical_neighbor_selection(self):
        x=features(self.df).to_numpy(float);modified=x.copy();modified[1001:]=1e6
        self.assertEqual(neighbors(x,1000,20)[0],neighbors(modified,1000,20)[0])

    def test_validation_and_cost_accounting(self):
        gross=analyze_frame(self.df,horizon=20,cost_bps=0)
        net=analyze_frame(self.df,horizon=20,cost_bps=30)
        self.assertEqual(net['status'],'OK')
        for g,n in zip(gross['analogs'],net['analogs']):
            self.assertAlmostEqual(g['net_return_pct']-n['net_return_pct'],.3,places=2)
        for row in net['validation']['recent']:
            self.assertLess(row['latest_label_end'],row['query_index']-EMBARGO)
        self.assertEqual(net['evidence'],'ABSTAIN') # Random walk must not be advertised as proven.

    def test_invalid_horizon_is_rejected_by_api(self):
        from fastapi.testclient import TestClient
        from app.main import app
        with patch('app.main.forecast',return_value={'status':'OK'}) as f:
            c=TestClient(app)
            self.assertEqual(c.get('/api/forecast/ASELS?horizon=20').status_code,200)
            self.assertEqual(c.get('/api/forecast/ASELS?horizon=7').status_code,422)
            self.assertEqual(f.call_count,1)

if __name__=='__main__': unittest.main()
