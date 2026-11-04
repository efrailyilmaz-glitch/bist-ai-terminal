import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import champion_governance as cg

class ChampionGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)/'g.db'
        self.dbp=patch('app.champion_governance._db',return_value=self.p);self.dbp.start()
    def tearDown(self):
        self.dbp.stop();self.tmp.cleanup()
    def row(self,vid,count,status='ELIGIBLE',decay='STABLE',score=10):
        return {'id':vid,'metrics':{'rebalance_count':count,'status':status,'score':score},'decay_v2':{'status':decay}}

    def test_same_evidence_does_not_advance_streak(self):
        r1=cg.evaluate(1,[self.row('A',12)],None)
        r2=cg.evaluate(1,[self.row('A',12)],None)
        self.assertEqual(r1['states']['A']['good_streak'],1)
        self.assertEqual(r2['states']['A']['good_streak'],1)
        self.assertFalse(r2['states']['A']['advanced'])

    def test_three_new_healthy_evidence_points_nominate_paper_champion(self):
        cg.evaluate(1,[self.row('A',12)],None)
        cg.evaluate(1,[self.row('A',13)],None)
        r=cg.evaluate(1,[self.row('A',14)],None)
        self.assertEqual(r['states']['A']['state'],'CHALLENGER_READY')
        self.assertEqual(r['decision']['action'],'NOMINATE_PAPER_CHAMPION')
        self.assertEqual(r['decision']['paper_champion'],'A')

    def test_champion_two_decay_evidence_points_quarantine(self):
        cg.evaluate(2,[self.row('A',12,decay='DECAY')],'A')
        r=cg.evaluate(2,[self.row('A',13,decay='DECAY')],'A')
        self.assertEqual(r['states']['A']['state'],'QUARANTINE')
        self.assertEqual(r['decision']['action'],'QUARANTINE_HOLD')

    def test_quarantined_champion_needs_three_new_stable_points_to_recover(self):
        cg.evaluate(3,[self.row('A',12,decay='DECAY')],'A')
        cg.evaluate(3,[self.row('A',13,decay='DECAY')],'A')
        cg.evaluate(3,[self.row('A',14,decay='STABLE')],'A')
        cg.evaluate(3,[self.row('A',15,decay='STABLE')],'A')
        r=cg.evaluate(3,[self.row('A',16,decay='STABLE')],'A')
        self.assertEqual(r['states']['A']['state'],'ACTIVE')

    def test_rotation_requires_margin_and_persistence(self):
        # Incumbent active, challenger gets three distinct healthy evidence points.
        cg.evaluate(4,[self.row('A',20,score=10),self.row('B',12,score=14)],'A')
        cg.evaluate(4,[self.row('A',20,score=10),self.row('B',13,score=14)],'A')
        r=cg.evaluate(4,[self.row('A',20,score=10),self.row('B',14,score=14)],'A')
        self.assertEqual(r['decision']['action'],'ROTATE_PAPER_CHAMPION')
        self.assertEqual(r['decision']['paper_champion'],'B')

if __name__=='__main__':unittest.main()
