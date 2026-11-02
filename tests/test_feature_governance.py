import unittest
from unittest.mock import patch
from app import feature_governance as fg

class FeatureGovernanceTests(unittest.TestCase):
    def setUp(self):
        fg._CACHE={'at':0.0,'report':None}
    def fake_attr(self,h,min_samples=12):
        rows=[]
        if h in (20,60):
            rows.append({'feature':'confirm:Bad','with_n':90,'without_n':100,'label':'NEGATIVE','delta_mean_excess_pct':-1.6})
        else:
            rows.append({'feature':'confirm:Bad','with_n':40,'without_n':50,'label':'POSSIBLE','delta_mean_excess_pct':-0.5})
        rows.append({'feature':'confirm:Good','with_n':60,'without_n':70,'label':'CONSISTENT','delta_mean_excess_pct':1.4})
        return {'rows':rows}
    def test_persistent_negative_disables_only_challenger(self):
        with patch('app.feature_governance.attribution',side_effect=self.fake_attr):
            r=fg.governance_report(force=True)
        bad=next(x for x in r['rows'] if x['feature']=='confirm:Bad')
        self.assertEqual(bad['state'],'CHALLENGER_DISABLE')
        self.assertEqual(bad['challenger_multiplier'],0.0)
        self.assertIn('Champion remains unchanged',r['policy'])
    def test_supported_feature_never_gets_risk_boost(self):
        with patch('app.feature_governance.attribution',side_effect=self.fake_attr):
            r=fg.governance_report(force=True)
        good=next(x for x in r['rows'] if x['feature']=='confirm:Good')
        self.assertEqual(good['state'],'SUPPORTED')
        self.assertEqual(good['challenger_multiplier'],1.0)
    def test_challenger_adjustment_never_positive(self):
        with patch('app.feature_governance.governance_report',return_value={'rows':[{'feature':'confirm:Bad','challenger_multiplier':0.0}]}):
            x=fg.challenger_adjustment(['Bad'],{})
        self.assertLessEqual(x['score_delta'],0)

if __name__=='__main__':unittest.main()
