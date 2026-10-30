import unittest
import numpy as np
import pandas as pd
from app.portfolio_guard import assess_frames

def frame(ret,seed=1):
    rng=np.random.default_rng(seed)
    r=np.asarray(ret,float)+rng.normal(0,.0002,len(ret))
    close=100*np.cumprod(1+r)
    return pd.DataFrame({'Close':close})

class PortfolioGuardTests(unittest.TestCase):
    def test_long_long_crowding_blocks(self):
        rng=np.random.default_rng(4);base=rng.normal(.0004,.012,260)
        frames={'NEW':frame(base,1),'A':frame(base,2),'B':frame(base,3),'XU100':frame(base*.8,5)}
        g=assess_frames('NEW',{'A':100,'B':100},frames,'BUY')
        self.assertEqual(g['status'],'BLOCK');self.assertEqual(g['risk_multiplier'],0)
    def test_short_can_offset_positive_corr(self):
        rng=np.random.default_rng(5);base=rng.normal(.0003,.011,260)
        frames={'NEW':frame(base,1),'A':frame(base,2),'XU100':frame(base*.8,3)}
        g=assess_frames('NEW',{'A':100},frames,'SHORT')
        self.assertNotEqual(g['status'],'BLOCK')
        self.assertLess(g['max_effective_corr'],0)
    def test_missing_candidate_history_derisks(self):
        g=assess_frames('NEW',{}, {'NEW':pd.DataFrame({'Close':[1,2,3]})},'BUY')
        self.assertEqual(g['status'],'UNKNOWN');self.assertLess(g['risk_multiplier'],1)

if __name__=='__main__':unittest.main()
