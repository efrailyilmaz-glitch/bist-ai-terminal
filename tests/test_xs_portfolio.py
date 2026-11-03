import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from app import xs_portfolio as xp

class XSPortfolioTests(unittest.TestCase):
    def ranked(self):
        return [{'ticker':f'T{i}','score':10-i,'value_turnover':100_000_000,'price':100} for i in range(8)]
    def risk_data(self):
        idx=pd.date_range('2025-01-01',periods=260)
        d={f'T{i}':pd.Series(np.sin(np.arange(260)/20+i)*.005 + i*.00001,index=idx) for i in range(8)}
        return pd.DataFrame(d),pd.Series(np.zeros(260),index=idx)
    def frames(self):
        idx=pd.date_range('2025-01-01',periods=260)
        out={'XU100':pd.DataFrame({'Close':100+np.arange(260)*.05},index=idx)}
        for i in range(8):out[f'T{i}']=pd.DataFrame({'Close':100+np.arange(260)*.03+i},index=idx)
        return out
    def test_weights_sum_and_cap(self):
        with patch('app.xs_portfolio._load',return_value=self.risk_data()),patch('app.xs_portfolio.daily_frames',return_value=self.frames()):
            r=xp.construct(self.ranked(),max_weight=.2)
        self.assertEqual(r['status'],'OK')
        self.assertAlmostEqual(sum(x['weight_pct'] for x in r['rows']),100,places=1)
        self.assertLessEqual(max(x['weight_pct'] for x in r['rows']),20.1)
    def test_liquidity_only_reduces(self):
        x=self.ranked();x[0]['value_turnover']=1
        with patch('app.xs_portfolio._load',return_value=self.risk_data()),patch('app.xs_portfolio.daily_frames',return_value=self.frames()):
            r=xp.construct(x,portfolio_value=1_000_000,adv_limit_pct=1)
        self.assertTrue(any(f['ticker']=='T0' for f in r['liquidity_flags']))

if __name__=='__main__':unittest.main()
