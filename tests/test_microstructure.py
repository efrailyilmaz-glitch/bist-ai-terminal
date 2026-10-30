import unittest
from app.microstructure import book_imbalance,spread_bps,normalized_order_flow,microstructure_guard

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
