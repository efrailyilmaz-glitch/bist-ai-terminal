import unittest
import pandas as pd
from unittest.mock import patch
from app import cross_sectional_ml as xs

class PurgedWalkForwardTests(unittest.TestCase):
    def panel(self):
        dates=[f'{2024+i//240:04d}-{(i//20)%12+1:02d}-{i%20+1:02d}' for i in range(500)]
        rows=[]
        for d_i,d in enumerate(dates):
            for s in range(20):
                row={'date':d,'ticker':f'T{s:02d}','label_excess_5d':((s-10)/1000)+(d_i%7)*.0001}
                for j,c in enumerate(xs.FEATURES):row['xs_'+c]=(s-10)/5+(j*.01)
                rows.append(row)
        return {'status':'OK','frame':pd.DataFrame(rows),'symbols':20,'dates':len(dates),'features':['xs_'+c for c in xs.FEATURES]}
    def test_adapter_unavailable_safe(self):
        with patch('app.cross_sectional_ml.build_panel',return_value=self.panel()),patch('app.cross_sectional_ml.adapter_status',return_value={'lightgbm_installed':False,'status':'ADAPTER_UNAVAILABLE'}):
            r=xs.purged_walk_forward_lab()
        self.assertEqual(r['status'],'ADAPTER_UNAVAILABLE')
    def test_insufficient_dates(self):
        p=self.panel();p['frame']=p['frame'][p['frame'].date.isin(sorted(p['frame'].date.unique())[:100])];p['dates']=100
        with patch('app.cross_sectional_ml.build_panel',return_value=p),patch('app.cross_sectional_ml.adapter_status',return_value={'lightgbm_installed':True,'status':'READY'}):
            r=xs.purged_walk_forward_lab(train_days=120,test_days=30)
        self.assertEqual(r['status'],'INSUFFICIENT_DATES')

if __name__=='__main__':unittest.main()
