import unittest
import pandas as pd
from unittest.mock import patch
from app import cross_sectional_ml as xs

def ff(seed):
    n=260
    dates=[f'2025-{(i//28)%12+1:02d}-{i%28+1:02d}' for i in range(n)]
    data={c:[(i+1)*(seed+1)*0.0001 + (j+1)*0.00001 for i in range(n)] for j,c in enumerate(xs.FEATURES)}
    data['label_5d']=[((i%11)-5)*0.002 + seed*0.0003 for i in range(n)]
    return pd.DataFrame(data,index=dates)

class CrossSectionalMLTests(unittest.TestCase):
    def test_panel_builds_relative_label(self):
        with patch('app.cross_sectional_ml.feature_frame',side_effect=lambda t,p:''):
            pass
    def test_panel_shape_and_excess(self):
        with patch('app.cross_sectional_ml.feature_frame',side_effect=lambda t,p:ff(int(t[1:]))):
            r=xs.build_panel(['T0','T1','T2','T3','T4','T5'],limit=6)
        self.assertEqual(r['status'],'OK')
        self.assertGreater(r['symbols'],0)
        self.assertIn('label_excess_5d',r['frame'].columns)
        self.assertTrue(all(('xs_'+c) in r['frame'].columns for c in xs.FEATURES))
    def test_rank_ic_positive(self):
        g=pd.DataFrame({'prediction':[1,2,3,4,5],'label_excess_5d':[1,2,3,4,5]})
        self.assertAlmostEqual(xs._rank_ic(g),1.0)
    def test_optional_adapter_safe(self):
        with patch('app.cross_sectional_ml.build_panel',return_value={'status':'OK','frame':pd.DataFrame(),'symbols':20,'dates':220,'features':['x']}),patch('app.cross_sectional_ml.adapter_status',return_value={'lightgbm_installed':False,'status':'ADAPTER_UNAVAILABLE'}):
            r=xs.run_lab(['A'])
        self.assertEqual(r['status'],'ADAPTER_UNAVAILABLE')

if __name__=='__main__':unittest.main()
