import unittest
from unittest.mock import patch
from app.external_challenger import adapter_catalog,run_candidate

class ExternalChallengerTests(unittest.TestCase):
    def test_uncleared_license_is_blocked(self):
        r=run_candidate('finrl_policy')
        self.assertEqual(r['status'],'LICENSE_BLOCK')
        self.assertFalse(r['live_execution'])

    def test_sequence_adapter_not_ready(self):
        r=run_candidate('qlib_lstm')
        self.assertEqual(r['status'],'ADAPTER_NOT_READY')
        self.assertEqual(r['promotion_status'],'RESEARCH_ONLY')

    def test_qlib_gbdt_executes_research_only(self):
        ranking={'status':'OK','as_of':'2026-11-04','symbols':20,
                 'rows':[{'ticker':'AAA','score':1.0}],
                 'train_rows':1000,'current_quality':{'status':'PASS'},
                 'training_quality':{'status':'PASS'},'universe_integrity':{'status':'PASS'},
                 'neutralization':{'status':'PASS'},
                 'model_artifact':{'registry_id':10,'model_fingerprint':'upstream'}}
        artifact={'registry_id':11,'model_fingerprint':'external'}
        with patch('app.external_challenger.adapter_status',return_value={'lightgbm_installed':True}),\
             patch('app.external_challenger.current_ranking',return_value=ranking),\
             patch('app.external_challenger.register_artifact',return_value=artifact):
            r=run_candidate('qlib_gbdt')
        self.assertEqual(r['status'],'OK')
        self.assertEqual(r['external_model_artifact']['registry_id'],11)
        self.assertFalse(r['paper_execution_enabled'])
        self.assertFalse(r['live_execution'])
        self.assertEqual(r['promotion_status'],'RESEARCH_ONLY')
        self.assertEqual(r['adapter_mode'],'INTERNAL_CONCEPT_REIMPLEMENTATION')

    def test_catalog_never_marks_uncleared_license_ready(self):
        with patch('app.external_challenger.adapter_status',return_value={'lightgbm_installed':True}):
            c=adapter_catalog()
        fin=next(x for x in c['rows'] if x['id']=='finrl_policy')
        self.assertFalse(fin['ready'])
        self.assertFalse(fin['license_ok'])

if __name__=='__main__':unittest.main()
