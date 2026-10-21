import time
import unittest
from unittest.mock import patch
from app.opportunity_engine import score_opportunity, rank_opportunities, radar_snapshot, _STATE

class RankingTests(unittest.TestCase):
    def tech(self,status='CLEAR'):
        return {'ticker':'TEST','price':100,'short_score':100,'long_score':100,'smart_money_score':100,'relative_strength_20':20,'risk':20,'signal_guard':{'status':status},'supertrend':'BULLISH','ichimoku':'BULLISH','breakout20':True,'volume_ratio':2,'as_of':'2026-10-21','fetched_at':time.time()}
    def test_guard_cannot_be_bypassed_by_opportunity_bonuses(self):
        fund={'fundamental_score':100,'quality_score':100,'growth_score':100}
        for status,cap in [('WAIT',67),('BLOCK',47),('UNKNOWN',47)]:
            out=score_opportunity(self.tech(status),fund,{'analyst_score':100},{'global_score':100})
            self.assertNotIn(out['grade'],['MEGA','STRONG','WATCH'])
            for key in ['opportunity_score','short_opportunity_score','long_opportunity_score']:self.assertLessEqual(out[key],cap)
        self.assertGreater(score_opportunity(self.tech(),fund,{'analyst_score':100},{'global_score':100})['opportunity_score'],67)
    def test_global_sort_keeps_unenriched_and_failed_enrichment(self):
        def r(t,s):return {'ticker':t,'opportunity_score':s,'grade':'NORMAL'}
        basic=[r('A',90),r('B',85),r('C',80)]
        result=rank_opportunities(basic,[r('A',30)])
        self.assertEqual([x['ticker'] for x in result],['B','C','A'])
        self.assertEqual(len(result),3)
        self.assertEqual(rank_opportunities([{**r('X',47),'grade':'BLOCK'}],[]),[])
    def test_old_persisted_radar_not_returned_as_current(self):
        with patch.dict(_STATE,{'opportunities':[{'fetched_at':time.time()-1300},{'ticker':'FRESH','fetched_at':time.time()}]}):
            self.assertEqual([r['ticker'] for r in radar_snapshot()['opportunities']],['FRESH'])
