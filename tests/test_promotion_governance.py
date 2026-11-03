import unittest
from unittest.mock import patch
from app.promotion_governance import evaluate

class PromotionGovernanceTests(unittest.TestCase):
    def history(self,linked=True,turn=20,cost=100):
        rebs=[]
        for i in range(12):
            rebs.append({'turnover_pct':turn,'cost':cost,'model_registry_id':1 if linked else None,'model_fingerprint':'x' if linked else None})
        return {'portfolio':{'capital':1_000_000,'last_equity':1_080_000},
                'curve':[{'excess_pct':5.0,'drawdown_pct':-3.0}],
                'rebalances':rebs}
    def test_good_forward_evidence_reaches_review(self):
        with patch('app.promotion_governance.verify_lineage_ledger',return_value={'status':'PASS'}):
            r=evaluate(self.history(),120)
        self.assertEqual(r['status'],'PROMOTION_REVIEW')
    def test_lineage_failure_blocks(self):
        with patch('app.promotion_governance.verify_lineage_ledger',return_value={'status':'FAIL'}):
            r=evaluate(self.history(),120)
        self.assertEqual(r['status'],'BLOCK')
        self.assertIn('LINEAGE_INTEGRITY_FAIL',r['reasons'])
    def test_missing_model_links_not_eligible(self):
        with patch('app.promotion_governance.verify_lineage_ledger',return_value={'status':'PASS'}):
            r=evaluate(self.history(linked=False),120)
        self.assertEqual(r['status'],'OBSERVE')
        self.assertIn('MODEL_REPRODUCIBILITY_INCOMPLETE',r['reasons'])
    def test_high_turnover_or_cost_blocks_review(self):
        with patch('app.promotion_governance.verify_lineage_ledger',return_value={'status':'PASS'}):
            r=evaluate(self.history(turn=90,cost=4000),120)
        self.assertEqual(r['status'],'OBSERVE')
        self.assertTrue(any(x in r['reasons'] for x in ['AVERAGE_TURNOVER_TOO_HIGH','COST_BURDEN_TOO_HIGH']))

if __name__=='__main__':unittest.main()
