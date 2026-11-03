import unittest
from app.cross_sectional_ml import _basket_turnover,cost_turnover_reality_from_ranked

class XSCostRealityTests(unittest.TestCase):
    def test_turnover(self):
        self.assertEqual(_basket_turnover([],['A','B']),1.0)
        self.assertAlmostEqual(_basket_turnover(['A','B'],['A','C']),0.5)
    def test_cost_only_reduces_edge(self):
        days=[]
        for i in range(10):
            rows=[]
            for j in range(20):
                rows.append({'ticker':f'T{j}','score':j,'label_excess_5d':(j-10)/1000,'value_turnover':50_000_000})
            days.append({'date':str(i),'rows':rows})
        low=cost_turnover_reality_from_ranked(days,one_way_cost_bps=5,rebalance_every=1)
        high=cost_turnover_reality_from_ranked(days,one_way_cost_bps=50,rebalance_every=1)
        self.assertGreaterEqual(low['gross_mean_spread_5d'],low['net_mean_spread_5d'])
        self.assertGreater(low['net_mean_spread_5d'],high['net_mean_spread_5d'])
    def test_capacity_flag(self):
        rows=[{'ticker':f'T{j}','score':j,'label_excess_5d':0.01*j,'value_turnover':10000} for j in range(20)]
        r=cost_turnover_reality_from_ranked([{'date':'x','rows':rows}],portfolio_value=1_000_000,adv_limit_pct=1)
        self.assertGreater(r['capacity_flagged_rebalances'],0)

if __name__=='__main__':unittest.main()
