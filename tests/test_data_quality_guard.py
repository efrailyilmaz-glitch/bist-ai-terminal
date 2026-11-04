import json,unittest
from app.data_quality_guard import audit_current_snapshot,audit_training_panel,survivorship_guard,evaluate_history

class DataQualityGuardTests(unittest.TestCase):
    def test_low_current_coverage_blocks(self):
        rows=[{'ticker':'A','as_of':'2026-11-04','price':10,'ret_1':.01} for _ in range(5)]
        r=audit_current_snapshot(rows,requested=20)
        self.assertEqual(r['status'],'BLOCK')
        self.assertIn('LOW_CURRENT_COVERAGE',r['flags'])
    def test_mixed_asof_blocks(self):
        rows=[{'ticker':str(i),'as_of':'2026-11-04' if i<8 else '2026-11-03','price':10,'ret_1':.01} for i in range(10)]
        r=audit_current_snapshot(rows,requested=10,max_stale_share_pct=10)
        self.assertEqual(r['status'],'BLOCK')
        self.assertIn('STALE_OR_MIXED_AS_OF',r['flags'])
    def test_training_failure_blocks(self):
        r=audit_training_panel({'requested':100,'symbols':70,'failed':['X']*30})
        self.assertEqual(r['status'],'BLOCK')
    def test_current_universe_proxy_is_explicit(self):
        r=survivorship_guard(False,True)
        self.assertEqual(r['status'],'CAUTION')
        self.assertTrue(r['survivorship_bias_risk'])
    def test_promotion_observes_unresolved_survivorship(self):
        integrity={'current_quality':{'status':'PASS'},'training_quality':{'status':'PASS'},
                   'universe_integrity':survivorship_guard(False,True)}
        h={'rebalances':[{'integrity_json':json.dumps(integrity)}]}
        r=evaluate_history(h)
        self.assertEqual(r['status'],'OBSERVE')
        self.assertIn('SURVIVORSHIP_RISK_UNRESOLVED',r['reasons'])

if __name__=='__main__':unittest.main()
