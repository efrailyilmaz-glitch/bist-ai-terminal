import unittest
from app.strategy_decay import detect_decay

class StrategyDecayTests(unittest.TestCase):
    def bot(self,pnls):
        orders=[{'pnl':x} for x in reversed(pnls)]
        curve=[{'equity':1_000_000+i*1000} for i in range(80)]
        return {'orders':orders,'curve':curve}
    def test_insufficient_forward_history(self):
        d=detect_decay(self.bot([100]*10))
        self.assertEqual(d['status'],'INSUFFICIENT')
    def test_sign_flip_and_pf_collapse_flags_decay(self):
        pnls=[1500,-500]*6 + [-1200,300]*6
        d=detect_decay(self.bot(pnls))
        self.assertEqual(d['status'],'DECAY')
        self.assertIn('EXPECTANCY_SIGN_FLIP',d['flags'])
        self.assertIn('PROFIT_FACTOR_DECAY',d['flags'])
    def test_stable_positive_process(self):
        pnls=[1200,-400,900,-300]*6
        d=detect_decay(self.bot(pnls))
        self.assertIn(d['status'],{'STABLE','WATCH'})
        self.assertNotIn('EXPECTANCY_SIGN_FLIP',d['flags'])

if __name__=='__main__':unittest.main()
