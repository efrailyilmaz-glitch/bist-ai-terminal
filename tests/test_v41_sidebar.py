import unittest
from pathlib import Path

class V41SidebarTests(unittest.TestCase):
    def test_sidebar_is_grouped_and_all_views_unique(self):
        html=Path('app/templates/index.html').read_text(encoding='utf-8')
        for label in ['01 · KARAR & FIRSAT','02 · TARAMA & HİSSE ANALİZİ','03 · PORTFÖY, RİSK & PİYASA','04 · AI, ROBOT & ARAŞTIRMA','05 · VERİ, SİSTEM & ARAÇLAR']:
            self.assertIn(label,html)
        import re
        views=re.findall(r'data-view="([^"]+)"',html)
        self.assertEqual(len(views),len(set(views)))
        self.assertIn('overview',views);self.assertIn('robotarena',views);self.assertIn('systemaudit',views)
        self.assertRegex(html,r'BIST AI Terminal V\d+\.0\.0')

if __name__=='__main__':unittest.main()
