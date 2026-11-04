import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import autonomous_research_loop as arl

class AutonomousResearchLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)/'r.db'
        self.pat=patch('app.autonomous_research_loop._db',return_value=self.p);self.pat.start()
    def tearDown(self):
        self.pat.stop();self.tmp.cleanup()
    def test_failed_validation_stays_research_only(self):
        with patch('app.autonomous_research_loop.purged_walk_forward_cost_reality',return_value={'status':'OK','net_mean_spread_5d':-0.01,'rebalances':10,'capacity_flagged_rebalances':0}),             patch('app.autonomous_research_loop.pit_universe_status',return_value={'status':'CURRENT_UNIVERSE_PROXY'}):
            r=arl.run_once(auto_create_paper=True)
        self.assertEqual(r['status'],'RESEARCH_ONLY')
        self.assertIsNone(r['tournament_id'])
    def test_passing_validation_creates_one_idempotent_tournament(self):
        validation={'status':'OK','net_mean_spread_5d':0.01,'rebalances':20,'capacity_flagged_rebalances':2}
        snap={'challengers':[],'days':1,'paper_champion':None,'meta_governance':{'ranking':[]}}
        with patch('app.autonomous_research_loop.purged_walk_forward_cost_reality',return_value=validation),             patch('app.autonomous_research_loop.pit_universe_status',return_value={'status':'PIT_VERIFIED'}),             patch('app.autonomous_research_loop.xs_tournament.create',return_value={'status':'OK','tournament_id':7}) as create,             patch('app.autonomous_research_loop.xs_tournament.start'),             patch('app.autonomous_research_loop.xs_scheduler.configure'),             patch('app.autonomous_research_loop.xs_scheduler.run_once',return_value={'status':'IDLE'}),             patch('app.autonomous_research_loop.xs_tournament.snapshot',return_value=snap):
            a=arl.run_once(force_rebalance=False)
            b=arl.run_once(force_rebalance=False)
        self.assertEqual(a['tournament_id'],7)
        self.assertEqual(b['tournament_id'],7)
        self.assertEqual(create.call_count,1)
    def test_promotion_review_is_research_label_only(self):
        validation={'status':'OK','net_mean_spread_5d':0.01,'rebalances':20,'capacity_flagged_rebalances':0}
        snap={'challengers':[{'id':'x','portfolio_id':1,'forward_scorecard':{'status':'ELIGIBLE_FOR_REVIEW'}}],
              'days':120,'paper_champion':'x','meta_governance':{'ranking':[]}}
        with patch('app.autonomous_research_loop.purged_walk_forward_cost_reality',return_value=validation),             patch('app.autonomous_research_loop.pit_universe_status',return_value={'status':'PIT_VERIFIED'}),             patch('app.autonomous_research_loop.xs_tournament.create',return_value={'status':'OK','tournament_id':8}),             patch('app.autonomous_research_loop.xs_tournament.start'),             patch('app.autonomous_research_loop.xs_scheduler.configure'),             patch('app.autonomous_research_loop.xs_scheduler.run_once',return_value={'status':'IDLE'}),             patch('app.autonomous_research_loop.xs_tournament.snapshot',return_value=snap):
            r=arl.run_once()
        self.assertEqual(r['status'],'PROMOTION_REVIEW')
        self.assertIn('never authorizes production/live execution',r['policy'])

if __name__=='__main__':unittest.main()
