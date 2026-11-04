import unittest
from app.portfolio_stress_lab import evaluate

class PortfolioStressLabTests(unittest.TestCase):
    def history(self,weights):
        return {'positions':[{'ticker':f'T{i}','weight':w} for i,w in enumerate(weights)]}
    def test_diversified_portfolio_passes(self):
        r=evaluate(self.history([.1]*8))
        self.assertEqual(r['status'],'PASS')
        self.assertLessEqual(r['worst_scenario']['loss_pct'],14)
    def test_concentrated_portfolio_observes(self):
        r=evaluate(self.history([.55,.15,.1]))
        self.assertIn(r['status'],{'OBSERVE','BLOCK'})
        self.assertIn('TOP3_CONCENTRATION_HIGH',r['reasons'])
    def test_empty_portfolio_observes(self):
        r=evaluate({'positions':[]})
        self.assertEqual(r['status'],'OBSERVE')
        self.assertIn('NO_ACTIVE_POSITIONS',r['reasons'])
    def test_sector_metadata_used_when_present(self):
        h={'positions':[{'ticker':'A','weight':.35,'sector':'BANK'},{'ticker':'B','weight':.30,'sector':'BANK'},{'ticker':'C','weight':.15,'sector':'IND'}]}
        r=evaluate(h)
        self.assertEqual(r['max_known_sector_weight_pct'],65.0)
        self.assertNotIn('SECTOR_METADATA_UNKNOWN',r['reasons'])

if __name__=='__main__':unittest.main()
