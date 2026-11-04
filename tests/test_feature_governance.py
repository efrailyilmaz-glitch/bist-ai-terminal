import unittest
from unittest.mock import patch
from app import feature_governance as fg
import app.protected_feature_governance as pfg
import app.experience_engine as ex
import tempfile, json, time
from pathlib import Path

class FeatureGovernanceTests(unittest.TestCase):
    def setUp(self):
        fg._CACHE={'at':0.0,'report':None}
        self.govtmp=tempfile.TemporaryDirectory();self.govdb=Path(self.govtmp.name)/'feature_governance.db'
        self.govpatch=patch.object(pfg,'_db',return_value=self.govdb);self.govpatch.start()
    def tearDown(self):
        self.govpatch.stop();self.govtmp.cleanup()
    def fake_attr(self,h,min_samples=12):
        rows=[]
        if h in (20,60):
            rows.append({'feature':'confirm:Bad','with_n':90,'without_n':100,'label':'NEGATIVE','delta_mean_excess_pct':-1.6})
        else:
            rows.append({'feature':'confirm:Bad','with_n':40,'without_n':50,'label':'POSSIBLE','delta_mean_excess_pct':-0.5})
        rows.append({'feature':'confirm:Good','with_n':60,'without_n':70,'label':'CONSISTENT','delta_mean_excess_pct':1.4})
        return {'rows':rows}
    def test_persistent_negative_requires_hysteresis_before_penalty(self):
        with patch('app.feature_governance.attribution',side_effect=self.fake_attr):
            r=fg.governance_report(force=True)
        bad=next(x for x in r['rows'] if x['feature']=='confirm:Bad')
        self.assertEqual(bad['raw_state'],'CHALLENGER_DISABLE')
        self.assertEqual(bad['state'],'OBSERVE')
        self.assertEqual(bad['challenger_multiplier'],1.0)
        self.assertIn('Protected safety/integrity features',r['policy'])
    def test_supported_feature_never_gets_risk_boost(self):
        with patch('app.feature_governance.attribution',side_effect=self.fake_attr):
            r=fg.governance_report(force=True)
        good=next(x for x in r['rows'] if x['feature']=='confirm:Good')
        self.assertEqual(good['state'],'SUPPORTED')
        self.assertEqual(good['challenger_multiplier'],1.0)
    def test_shadow_ab_requires_forward_evidence(self):
        tmp=tempfile.TemporaryDirectory();db=Path(tmp.name)/'experience.db'
        with patch.object(ex,'_db',return_value=db):
            con=ex._conn();now=time.time()
            for i in range(50):
                champ=82;chall=82 if i<25 else 70
                setup={'governance_challenger_score':chall}
                excess=1.2 if i<25 else -1.0
                con.execute('''INSERT INTO signals(created_epoch,created_at,ticker,grade,opportunity_score,entry_price,benchmark_price,setup_json,settled_20,excess_20)
                               VALUES(?,?,?,?,?,?,?,?,1,?)''',(now+i,str(i),f'T{i}','STRONG',champ,100,10000,json.dumps(setup),excess))
            con.commit();con.close()
            r=fg.ab_report(20,threshold=78,min_samples=20)
        tmp.cleanup()
        self.assertEqual(r['status'],'OK')
        self.assertEqual(r['recommendation'],'CHALLENGER_ELIGIBLE_FOR_PROMOTION_REVIEW')
        self.assertLess(r['champion_only_rejected_by_challenger']['mean_excess_pct'],0)

    def test_challenger_adjustment_never_positive(self):
        with patch('app.feature_governance.governance_report',return_value={'rows':[{'feature':'confirm:Bad','challenger_multiplier':0.0}]}):
            x=fg.challenger_adjustment(['Bad'],{})
        self.assertLessEqual(x['score_delta'],0)

if __name__=='__main__':unittest.main()
