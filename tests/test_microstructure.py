import unittest
from app.microstructure import book_imbalance,spread_bps,normalized_order_flow,microstructure_guard,footprint_features

class MicrostructureTests(unittest.TestCase):
    def test_balanced_book(self):
        bids=[{'price':100,'qty':1000},{'price':99.9,'qty':500}]
        asks=[{'price':100.1,'qty':1000},{'price':100.2,'qty':500}]
        self.assertAlmostEqual(book_imbalance(bids,asks),0.0)
        self.assertGreater(spread_bps(bids,asks),0)
    def test_negative_flow_can_veto(self):
        s={'bids':[{'price':100,'qty':2000}],'asks':[{'price':100.1,'qty':2000}],
           'events':[{'action':'TRADE','aggressor_side':'SELL','qty':100,'side':'BID'} for _ in range(30)]}
        g=microstructure_guard(s)
        self.assertEqual(g['status'],'BAD');self.assertLess(g['risk_multiplier'],1)
        self.assertIn('NEGATIVE_ORDER_FLOW',g['flags'])
    def test_absorption_pattern_detected(self):
        events=[{'action':'TRADE','aggressor_side':'BUY','side':'ASK','qty':100,'price':100.00+(i%2)*0.01} for i in range(24)]
        s={'bids':[{'price':99.99,'qty':5000}],'asks':[{'price':100.01,'qty':5000}],'events':events}
        f=footprint_features(s)
        self.assertGreaterEqual(f['absorption_score'],70)
        self.assertIn('ABSORPTION_PATTERN',f['flags'])
    def test_sweep_and_vacuum_can_raise_risk(self):
        events=[]
        for i,p in enumerate([100.0,100.1,100.2,100.3,100.4,100.5]):
            events.append({'action':'TRADE','aggressor_side':'BUY','side':'ASK','qty':200,'price':p})
        events += [{'action':'CANCEL','side':'BID','qty':5000,'price':99.0+i*.01} for i in range(20)]
        s={'bids':[{'price':99.0,'qty':20}],'asks':[{'price':101.0,'qty':20}],'events':events}
        f=footprint_features(s)
        self.assertGreaterEqual(f['sweep_score'],70)
        self.assertGreaterEqual(f['liquidity_vacuum_score'],65)
        g=microstructure_guard(s)
        self.assertIn(g['status'],{'BAD','CAUTION'})
        self.assertLess(g['risk_multiplier'],1)
    def test_spoof_like_is_symptom_not_intent(self):
        events=[]
        for _ in range(30):
            events += [{'action':'ADD','side':'ASK','qty':1000,'price':100.2},{'action':'CANCEL','side':'ASK','qty':1000,'price':100.2}]
        s={'bids':[{'price':100,'qty':1000}],'asks':[{'price':100.1,'qty':1000}],'events':events}
        f=footprint_features(s)
        self.assertGreaterEqual(f['spoof_like_risk_score'],65)
        self.assertIn('SPOOF_LIKE_CHURN_RISK',f['flags'])
        self.assertIn('not manipulation intent',f['note'])
    def test_missing_data_never_bullish(self):
        g=microstructure_guard(None)
        self.assertEqual(g['status'],'UNKNOWN');self.assertEqual(g['risk_multiplier'],1.0)
    def test_order_flow_direction(self):
        x=normalized_order_flow([
          {'action':'ADD','side':'BID','qty':100},
          {'action':'CANCEL','side':'ASK','qty':50},
          {'action':'TRADE','aggressor_side':'BUY','side':'ASK','qty':50}])
        self.assertGreater(x['ofi'],0)

if __name__=='__main__':unittest.main()
