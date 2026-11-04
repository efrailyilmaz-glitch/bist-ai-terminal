import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import protected_feature_governance as pg

class ProtectedFeatureGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)/'fg.db'
        self.dbp=patch('app.protected_feature_governance._db',return_value=self.p);self.dbp.start()
    def tearDown(self):
        self.dbp.stop();self.tmp.cleanup()

    def row(self,feature,state='CHALLENGER_DISABLE',n=80,neg=2,cons=0,delta=-2):
        return {'feature':feature,'state':state,'challenger_multiplier':0.0,'max_with_n':n,
                'negative_horizons':neg,'consistent_horizons':cons,'weighted_delta_mean_excess_pct':delta,
                'evidence':[{'horizon':20,'with_n':n,'label':'NEGATIVE','delta_mean_excess_pct':delta}]}

    def test_protected_feature_never_downweights(self):
        r=pg.apply([self.row('trap_defense:BLOCK')])[0]
        self.assertTrue(r['protected'])
        self.assertEqual(r['state'],'PROTECTED')
        self.assertEqual(r['challenger_multiplier'],1.0)

    def test_penalty_requires_repeated_new_evidence(self):
        a=pg.apply([self.row('confirm:X',state='DOWNWEIGHT',n=50)])[0]
        b=pg.apply([self.row('confirm:X',state='DOWNWEIGHT',n=51)])[0]
        c=pg.apply([self.row('confirm:X',state='DOWNWEIGHT',n=52)])[0]
        self.assertEqual(a['state'],'OBSERVE')
        self.assertEqual(b['state'],'QUARANTINE')
        self.assertEqual(c['state'],'DOWNWEIGHT')

    def test_same_evidence_does_not_advance(self):
        a=pg.apply([self.row('confirm:Y',state='QUARANTINE',n=30)])[0]
        b=pg.apply([self.row('confirm:Y',state='QUARANTINE',n=30)])[0]
        self.assertEqual(a['hysteresis']['bad_streak'],1)
        self.assertEqual(b['hysteresis']['bad_streak'],1)
        self.assertFalse(b['hysteresis']['advanced'])

    def test_recovery_requires_three_new_healthy_evidence_points(self):
        pg.apply([self.row('confirm:Z',state='DOWNWEIGHT',n=50)])
        pg.apply([self.row('confirm:Z',state='DOWNWEIGHT',n=51)])
        pg.apply([self.row('confirm:Z',state='DOWNWEIGHT',n=52)])
        self.assertEqual(pg.status()['states'][0]['state'],'DOWNWEIGHT')
        for n in [53,54]:
            pg.apply([self.row('confirm:Z',state='SUPPORTED',n=n,neg=0,cons=2,delta=1.2)])
        self.assertEqual(pg.status()['states'][0]['state'],'DOWNWEIGHT')
        pg.apply([self.row('confirm:Z',state='SUPPORTED',n=55,neg=0,cons=2,delta=1.2)])
        self.assertEqual(pg.status()['states'][0]['state'],'SUPPORTED')

if __name__=='__main__':unittest.main()
