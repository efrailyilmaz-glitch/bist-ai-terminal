import unittest
from pathlib import Path

class V41SidebarTests(unittest.TestCase):
    def test_sidebar_is_grouped_and_all_views_unique(self):
        html=Path('app/templates/index.html').read_text(encoding='utf-8')
        for label in ['01 · GÜNLÜK KARAR','02 · TARAMA & SİNYAL','03 · RİSK & İŞLEM','04 · PİYASA & HİSSE ANALİZİ','05 · ARAŞTIRMA & DOĞRULAMA','06 · SİSTEM & ARAÇLAR']:
            self.assertIn(label,html)
        import re
        views=re.findall(r'data-view="([^"]+)"',html)
        self.assertEqual(len(views),len(set(views)))
        self.assertIn('overview',views);self.assertIn('robotarena',views);self.assertIn('systemaudit',views)
        self.assertIn('V41.0.0',html)

if __name__=='__main__':unittest.main()
