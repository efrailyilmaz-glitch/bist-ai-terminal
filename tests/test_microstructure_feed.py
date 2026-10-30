import os,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch,Mock
from app import microstructure_feed as f

class MicrostructureFeedTests(unittest.TestCase):
    def setUp(self):f._CACHE.clear()
    def test_unconfigured_is_unknown_not_bullish(self):
        with patch.dict(os.environ,{},clear=True):
            x=f.latest_microstructure('TEST')
        self.assertFalse(x['configured']);self.assertEqual(x['guard']['status'],'UNKNOWN')
        self.assertEqual(x['guard']['risk_multiplier'],1.0)
    def test_fresh_payload_is_evaluated(self):
        now=datetime.now(timezone.utc).isoformat()
        payload={'timestamp':now,'bids':[{'price':100,'qty':2000}],'asks':[{'price':100.1,'qty':1000}],
                 'events':[{'action':'TRADE','side':'ASK','aggressor_side':'BUY','qty':100} for _ in range(30)]}
        resp=Mock();resp.raise_for_status.return_value=None;resp.json.return_value=payload
        with patch.dict(os.environ,{'LEVEL2_API_URL':'https://feed.local/{ticker}','LEVEL2_API_TOKEN':'x'},clear=True),patch('app.microstructure_feed.requests.get',return_value=resp) as get:
            x=f.latest_microstructure('TEST')
        self.assertTrue(x['configured']);self.assertEqual(x['status'],'OK');self.assertLessEqual(x['age_seconds'],5)
        self.assertNotEqual(x['guard']['status'],'UNKNOWN');self.assertIn('Authorization',get.call_args.kwargs['headers'])
    def test_stale_payload_derisks(self):
        old=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
        payload={'timestamp':old,'bids':[{'price':100,'qty':1000}],'asks':[{'price':100.1,'qty':1000}],
                 'events':[{'action':'TRADE','side':'ASK','aggressor_side':'BUY','qty':10} for _ in range(30)]}
        resp=Mock();resp.raise_for_status.return_value=None;resp.json.return_value=payload
        with patch.dict(os.environ,{'LEVEL2_API_URL':'https://feed.local'},clear=True),patch('app.microstructure_feed.requests.get',return_value=resp):
            x=f.latest_microstructure('TEST',max_age_seconds=30)
        self.assertEqual(x['guard']['status'],'CAUTION');self.assertLess(x['guard']['risk_multiplier'],1)
        self.assertIn('LEVEL2_STALE',x['guard']['flags'])
    def test_fetch_failure_derisks(self):
        with patch.dict(os.environ,{'LEVEL2_API_URL':'https://feed.local'},clear=True),patch('app.microstructure_feed.requests.get',side_effect=RuntimeError('offline')):
            x=f.latest_microstructure('TEST')
        self.assertEqual(x['status'],'ERROR');self.assertEqual(x['guard']['status'],'CAUTION')

if __name__=='__main__':unittest.main()
