import unittest
from app.model_zoo_lab import validate_candidate,score_candidate,catalog

class ModelZooLabTests(unittest.TestCase):
    def good(self):
        return {'id':'x','name':'Test','source':'lab','version':'1','license':'MIT',
                'input_schema':{'x':'float'},'output_schema':{'score':'float'},
                'point_in_time':True,'causality_status':'PASS','cost_stress_status':'PASS',
                'robustness_status':'PASS','execution_compatible':True,
                'forward_paper':{'days':120,'trades':45,'profit_factor':1.4,'max_drawdown_pct':5,'return_pct':12}}
    def test_all_gates_required(self):
        c=self.good();r=validate_candidate(c)
        self.assertEqual(r['status'],'ELIGIBLE_FOR_CHALLENGER')
        c['point_in_time']=False
        r=validate_candidate(c);self.assertEqual(r['status'],'RESEARCH_ONLY');self.assertIn('POINT_IN_TIME_OK',r['veto_reasons'])
    def test_uncertain_license_never_passes(self):
        c=self.good();c['license']='UNKNOWN'
        self.assertEqual(validate_candidate(c)['status'],'RESEARCH_ONLY')
    def test_score_requires_forward_gate(self):
        c=self.good();self.assertIsNotNone(score_candidate(c)['score'])
        c['forward_paper']['trades']=10
        self.assertIsNone(score_candidate(c)['score'])
    def test_catalog_has_external_sources(self):
        ids={x['id'] for x in catalog()['models']}
        self.assertIn('qlib_gbdt',ids);self.assertIn('hf_finance_model',ids)

if __name__=='__main__':unittest.main()
