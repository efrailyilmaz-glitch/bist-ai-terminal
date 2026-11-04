import unittest
from unittest.mock import patch
from app.ensemble_challenger import build,evidence_gate

class EnsembleChallengerTests(unittest.TestCase):
    def cand(self,i,scores=None,days=120,as_of='2026-11-04'):
        scores=scores if scores is not None else list(range(12))
        return {'id':f'M{i}','name':f'Model {i}','as_of':as_of,'model_fingerprint':f'fp{i}',
                'rows':[{'ticker':f'T{j:02d}','score':float(scores[j])} for j in range(12)],
                'forward_evidence':{'days':days,'rebalances':20,'excess_pct':4+i*.2,'max_drawdown_pct':4,
                                    'lineage_status':'PASS','reproducible':True}}
    def test_requires_three_mature_models(self):
        c=[self.cand(1),self.cand(2),self.cand(3,days=40)]
        r=build(c)
        self.assertEqual(r['status'],'INSUFFICIENT_DIVERSITY')
        self.assertEqual(r['eligible_models'],2)
    def test_asof_mismatch_blocks(self):
        c=[self.cand(1),self.cand(2),self.cand(3,as_of='2026-11-03')]
        r=build(c)
        self.assertEqual(r['status'],'AS_OF_MISMATCH')
    def test_diverse_models_build_research_ensemble(self):
        a=list(range(12));b=list(reversed(range(12)));c=[0,2,4,6,8,10,1,3,5,7,9,11]
        with patch('app.ensemble_challenger.register_artifact',return_value={'registry_id':1,'model_fingerprint':'ens'}):
            r=build([self.cand(1,a),self.cand(2,b),self.cand(3,c)])
        self.assertIn(r['status'],['OK','CAUTION'])
        self.assertEqual(len(r['components']),3)
        self.assertTrue(all(x['weight']<=.400001 for x in r['components']))
        self.assertEqual(r['common_symbols'],12)
        self.assertEqual(r['promotion_status'],'RESEARCH_ONLY')
        self.assertFalse(r['paper_execution_enabled'])
        self.assertFalse(r['live_execution'])
    def test_identical_rankings_flag_redundancy(self):
        a=list(range(12))
        with patch('app.ensemble_challenger.register_artifact',return_value={'registry_id':1,'model_fingerprint':'ens'}):
            r=build([self.cand(1,a),self.cand(2,a),self.cand(3,a)])
        self.assertEqual(r['status'],'CAUTION')
        self.assertIn('HIGH_MODEL_REDUNDANCY',r['flags'])
    def test_reproducibility_is_required(self):
        c=self.cand(1);c['forward_evidence']['reproducible']=False
        g=evidence_gate(c)
        self.assertEqual(g['status'],'OBSERVE')
        self.assertIn('REPRODUCIBILITY_NOT_PASS',g['reasons'])

if __name__=='__main__':unittest.main()
