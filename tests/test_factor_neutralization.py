import json,unittest
import numpy as np
import pandas as pd
from app.factor_neutralization import neutralize,evaluate_history

class FactorNeutralizationTests(unittest.TestCase):
    def frame(self,n=40):
        x=np.linspace(-2,2,n)
        return pd.DataFrame({
            'ticker':[f'T{i}' for i in range(n)],
            'raw_score':2.5*x+0.8*np.sin(np.arange(n)),
            'ret_20':x,
            'vol_20':np.cos(np.arange(n)/4)+2,
            'ema50_gap':x*.5+np.sin(np.arange(n)/3),
            'sector':['BANK']*(n//2)+['INDUSTRY']*(n-n//2)
        })
    def test_factor_exposure_is_reduced(self):
        r=neutralize(self.frame())
        self.assertIn(r['status'],['PASS','CAUTION'])
        d=r['diagnostics']
        self.assertLessEqual(d['max_neutral_abs_factor_corr'],.15)
        self.assertGreater(d['max_raw_abs_factor_corr'],d['max_neutral_abs_factor_corr'])
    def test_missing_sector_is_explicit(self):
        f=self.frame().drop(columns=['sector'])
        r=neutralize(f)
        self.assertIn('SECTOR_METADATA_INCOMPLETE',r['flags'])
    def test_promotion_requires_neutralization_evidence(self):
        h={'rebalances':[{'integrity_json':json.dumps({'neutralization':{'status':'PASS','diagnostics':{'max_neutral_abs_factor_corr':.05}}})}]}
        self.assertEqual(evaluate_history(h)['status'],'PASS')
        h2={'rebalances':[{'integrity_json':json.dumps({})}]}
        self.assertEqual(evaluate_history(h2)['status'],'OBSERVE')

if __name__=='__main__':unittest.main()
