import unittest
from app.meta_governance import conservative_score,rank_forward_bots,meta_decision

class MetaGovernanceTests(unittest.TestCase):
    def row(self,id,ret=10,dd=4,pf=1.5,trades=40,fees=1000):
        return {'id':id,'name':id,'metrics':{'return_pct':ret,'max_drawdown_pct':dd,'profit_factor':pf,'closed_trades':trades,'fees_paid':fees}}
    def test_small_samples_are_shrunk(self):
        m=self.row('x')['metrics']
        self.assertLess(abs(conservative_score(m,20)),abs(conservative_score(m,120)))
    def test_eligibility_requires_forward_evidence(self):
        r=rank_forward_bots([self.row('a')],120,5)
        self.assertEqual(r[0]['status'],'ELIGIBLE')
        r=rank_forward_bots([self.row('a',trades=5)],120,5)
        self.assertEqual(r[0]['status'],'OBSERVE')
    def test_challenger_needs_margin(self):
        ranking=[{'id':'a','status':'ELIGIBLE','score':5.0},{'id':'b','status':'ELIGIBLE','score':6.0}]
        self.assertEqual(meta_decision(ranking,'a')['action'],'HOLD')
        ranking=[{'id':'b','status':'ELIGIBLE','score':8.0},{'id':'a','status':'ELIGIBLE','score':5.0}]
        self.assertEqual(meta_decision(ranking,'a')['champion'],'b')

if __name__=='__main__':unittest.main()
