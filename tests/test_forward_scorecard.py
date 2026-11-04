import unittest
from unittest.mock import patch
from app.forward_scorecard import build

class ForwardScorecardTests(unittest.TestCase):
    def hist(self):
        return {'portfolio':{'capital':1_000_000,'last_equity':1_080_000},
                'curve':[{'excess_pct':5.0,'drawdown_pct':-2.0}],
                'rebalances':[{'model_registry_id':1,'model_fingerprint':'x','turnover_pct':20,'cost':100,'ranking_as_of':'2026-11-01','ranking_snapshot_json':'[]'}]*12,
                'positions':[{'ticker':'A','weight':.2},{'ticker':'B','weight':.2},{'ticker':'C','weight':.2}]}
    def test_all_pass_yields_review(self):
        with patch('app.forward_scorecard.hard_gate',return_value={'status':'PROMOTION_REVIEW','reasons':[],'metrics':{}}),             patch('app.forward_scorecard.statistical_gate',return_value={'status':'PASS','reasons':[]}),             patch('app.forward_scorecard.regime_gate',return_value={'status':'PASS','reasons':[]}),             patch('app.forward_scorecard.data_quality_gate',return_value={'status':'PASS','reasons':[]}),             patch('app.forward_scorecard.factor_gate',return_value={'status':'PASS','reasons':[]}),             patch('app.forward_scorecard.stress_gate',return_value={'status':'PASS','reasons':[]}),             patch('app.forward_scorecard.detect_xs_decay',return_value={'status':'HEALTHY'}):
            r=build(self.hist(),120,3)
        self.assertEqual(r['status'],'ELIGIBLE_FOR_REVIEW')
        self.assertEqual(r['evidence_score_pct'],100.0)
    def test_failed_gate_cannot_be_overridden(self):
        with patch('app.forward_scorecard.hard_gate',return_value={'status':'OBSERVE','reasons':['X'],'metrics':{}}),             patch('app.forward_scorecard.detect_xs_decay',return_value={'status':'HEALTHY'}):
            r=build(self.hist(),120,3)
        self.assertNotEqual(r['status'],'ELIGIBLE_FOR_REVIEW')
        self.assertIn('X',r['reasons'])

if __name__=='__main__':unittest.main()
