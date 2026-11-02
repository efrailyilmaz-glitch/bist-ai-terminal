import unittest, tempfile, sqlite3, time
from pathlib import Path
from unittest.mock import patch
import app.experience_engine as ex

class EvidenceLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'experience.db'
        self.pdb=patch.object(ex,'_db',return_value=self.db);self.pdb.start()
        self.pprice=patch.object(ex,'_latest_price',side_effect=lambda t:100.0 if t!='XU100' else 10000.0);self.pprice.start()
    def tearDown(self):
        self.pprice.stop();self.pdb.stop();self.tmp.cleanup()
    def signal(self,ticker='TEST'):
        return {'ticker':ticker,'grade':'STRONG','opportunity_score':82,'price':100.0,
                'as_of':time.strftime('%Y-%m-%d'),'fetched_at':time.time()-1,'bar_provisional':False,
                'confirmations':['x'],'warnings':[],'components':{'technical':80},'targets':{'short_target_1':105},
                'signal_guard':{'status':'CLEAR'},'trap_defense':{'status':'CLEAR'}}
    def test_chain_verifies_and_detects_tamper(self):
        a=ex.record_signal(self.signal('AAA'),{'decision':'PASS','committee_score':81,'regime':'BULL'})
        b=ex.record_signal(self.signal('BBB'),{'decision':'WATCH','committee_score':70,'regime':'SIDEWAYS'})
        self.assertTrue(a);self.assertTrue(b);self.assertEqual(ex.verify_ledger()['status'],'PASS')
        c=sqlite3.connect(self.db);c.execute("UPDATE signals SET grade='MEGA' WHERE id=?",(a,));c.commit();c.close()
        x=ex.verify_ledger();self.assertEqual(x['status'],'FAIL');self.assertIn(a,x['bad_ids'])
    def test_provisional_signal_is_not_recorded(self):
        s=self.signal();s['bar_provisional']=True
        self.assertIsNone(ex.record_signal(s,{}))

if __name__=='__main__':unittest.main()
