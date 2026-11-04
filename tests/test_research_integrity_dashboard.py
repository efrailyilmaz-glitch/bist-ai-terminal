import unittest
from unittest.mock import patch
from app.research_integrity_dashboard import dashboard

class ResearchIntegrityDashboardTests(unittest.TestCase):
    def test_global_pass(self):
        with patch('app.research_integrity_dashboard.verify_ledger',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.verify_lineage_ledger',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.dataset_status',return_value={'status':'PIT_VERIFIED'}),             patch('app.research_integrity_dashboard.protected_status',return_value={'status':'OK'}),             patch('app.research_integrity_dashboard.model_history',return_value={'status':'OK','rows':[]}):
            r=dashboard()
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['counts']['blockers'],0)
    def test_lineage_failure_blocks(self):
        with patch('app.research_integrity_dashboard.verify_ledger',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.verify_lineage_ledger',return_value={'status':'FAIL'}),             patch('app.research_integrity_dashboard.dataset_status',return_value={'status':'PIT_VERIFIED'}),             patch('app.research_integrity_dashboard.protected_status',return_value={'status':'OK'}),             patch('app.research_integrity_dashboard.model_history',return_value={'status':'OK','rows':[]}):
            r=dashboard()
        self.assertEqual(r['status'],'BLOCK')
        self.assertIn('XS_LINEAGE_HASH_CHAIN',r['blockers'])
    def test_portfolio_panel_is_included(self):
        h={'status':'OK','portfolio':{},'curve':[],'rebalances':[],'positions':[]}
        with patch('app.research_integrity_dashboard.verify_ledger',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.verify_lineage_ledger',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.dataset_status',return_value={'status':'PIT_VERIFIED'}),             patch('app.research_integrity_dashboard.protected_status',return_value={'status':'OK'}),             patch('app.research_integrity_dashboard.model_history',return_value={'status':'OK','rows':[]}),             patch('app.research_integrity_dashboard.xs_history',return_value=h),             patch('app.research_integrity_dashboard.scorecard_build',return_value={'status':'OBSERVE'}),             patch('app.research_integrity_dashboard.data_quality_history',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.stress_history',return_value={'status':'PASS'}),             patch('app.research_integrity_dashboard.detect_xs_decay',return_value={'status':'HEALTHY'}):
            r=dashboard(1,days=30)
        self.assertIsNotNone(r['portfolio'])
        self.assertEqual(r['portfolio']['portfolio_id'],1)
        self.assertIn('FORWARD_EVIDENCE_SCORECARD',r['warnings'])

if __name__=='__main__':unittest.main()
