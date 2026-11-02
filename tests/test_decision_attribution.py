import unittest, tempfile, sqlite3, json, time
from pathlib import Path
from unittest.mock import patch
import app.experience_engine as ex
from app.decision_attribution import attribution

class DecisionAttributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'experience.db'
        self.pdb=patch.object(ex,'_db',return_value=self.db);self.pdb.start()
        c=ex._conn()
        now=time.time()
        for i in range(40):
            feat=(i<20)
            setup={'confirmations':['Feature A'] if feat else [],'warnings':[],
                   'components':{'technical_short':80 if feat else 50},
                   'signal_guard':{'status':'CLEAR'},'trap_defense':{'status':'CLEAR'}}
            excess=(-2.0 if feat else 1.5) + (i%3)*.1
            c.execute('''INSERT INTO signals(created_epoch,created_at,ticker,grade,opportunity_score,entry_price,benchmark_price,setup_json,settled_20,excess_20)
                         VALUES(?,?,?,?,?,?,?,?,1,?)''',(now+i,str(i),f'T{i}','STRONG',80,100,10000,json.dumps(setup),excess))
        c.commit();c.close()
    def tearDown(self):
        self.pdb.stop();self.tmp.cleanup()
    def test_negative_feature_is_flagged(self):
        r=attribution(20,min_samples=10)
        row=next(x for x in r['rows'] if x['feature']=='confirm:Feature A')
        self.assertEqual(row['label'],'NEGATIVE')
        self.assertLess(row['delta_mean_excess_pct'],0)
        self.assertTrue(any(x['feature']=='confirm:Feature A' for x in r['prune_candidates']))
    def test_small_samples_remain_unknown(self):
        r=attribution(20,min_samples=25)
        row=next(x for x in r['rows'] if x['feature']=='confirm:Feature A')
        self.assertEqual(row['label'],'UNKNOWN')

if __name__=='__main__':unittest.main()
