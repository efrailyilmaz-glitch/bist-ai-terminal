import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import xs_tournament as xt

class XSTournamentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.tdb=Path(self.tmp.name)/'t.db'
        self.pdb=Path(self.tmp.name)/'p.db'
        self.a=patch('app.xs_tournament._db',return_value=self.tdb);self.a.start()
        self.b=patch('app.xs_paper._db',return_value=self.pdb);self.b.start()
        self.c=patch('app.xs_paper._price',side_effect=lambda t:100.0 if t!='XU100' else 10000.0);self.c.start()
    def tearDown(self):
        self.a.stop();self.b.stop();self.c.stop();self.tmp.cleanup()
    def test_create_three_equal_capital_challengers(self):
        r=xt.create(500000)
        self.assertEqual(r['status'],'OK')
        self.assertEqual(len(r['challengers']),3)
        self.assertTrue(all(x['portfolio_id'] for x in r['challengers']))
    def test_no_early_promotion(self):
        tid=xt.create()['tournament_id'];xt.start(tid)
        s=xt.snapshot(tid)
        self.assertTrue(all(x['status']=='OBSERVE' for x in s['meta_governance']['ranking']))
        self.assertEqual(s['meta_governance']['decision']['action'],'HOLD')

if __name__=='__main__':unittest.main()
