import unittest
from app.bist_execution_rules import quote_guard,protective_fill,price_limits

class BISTExecutionRulesTests(unittest.TestCase):
    def q(self,open_=100,high=101,low=99,close=100,prev=100):
        return {'open':open_,'high':high,'low':low,'close':close,'previous_close':prev}
    def test_price_limit_violation_blocks(self):
        r=quote_guard(self.q(open_=111,high=112,low=110,close=111),100)
        self.assertEqual(r['status'],'BLOCK')
        self.assertIn('PRICE_LIMIT_VIOLATION_OR_CORPORATE_ACTION',r['flags'])
    def test_down_five_percent_enters_circuit_zone(self):
        r=quote_guard(self.q(open_=96,high=97,low=94.8,close=95),100)
        self.assertEqual(r['status'],'CAUTION')
        self.assertIn('CIRCUIT_BREAKER_ZONE',r['flags'])
        self.assertLess(r['risk_multiplier'],1)
    def test_adverse_lower_limit_lock_does_not_fake_stop_fill(self):
        q=self.q(open_=90,high=90.2,low=90,close=90)
        r=protective_fill(95,q,'SELL',100)
        self.assertEqual(r['status'],'NO_FILL_LIMIT_LOCK')
    def test_normal_gap_stop_fills_at_gap_open(self):
        q=self.q(open_=94,high=96,low=93,close=95)
        r=protective_fill(95,q,'SELL',100)
        self.assertEqual(r['status'],'FILL')
        self.assertAlmostEqual(r['price'],94)
        self.assertTrue(r['gap_through_stop'])
    def test_limits_are_ten_percent_for_equity_model(self):
        r=price_limits(100)
        self.assertAlmostEqual(r['lower_limit'],90)
        self.assertAlmostEqual(r['upper_limit'],110)

if __name__=='__main__':unittest.main()
