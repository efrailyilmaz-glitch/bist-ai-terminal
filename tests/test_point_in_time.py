import unittest, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.point_in_time import audit_signal, audit_disclosures

TR=ZoneInfo('Europe/Istanbul')

class PointInTimeTests(unittest.TestCase):
    def test_provisional_and_future_are_blocked(self):
        now=time.time()
        future=(datetime.now(TR)+timedelta(days=1)).date().isoformat()
        x=audit_signal({'as_of':future,'fetched_at':now,'bar_provisional':True},now)
        self.assertEqual(x['status'],'BLOCK')
        self.assertIn('PROVISIONAL_BAR',x['flags'])
        self.assertIn('SOURCE_ASOF_IN_FUTURE',x['flags'])
    def test_missing_timestamp_never_passes_as_good(self):
        x=audit_signal({'as_of':datetime.now(TR).date().isoformat(),'bar_provisional':False},time.time())
        self.assertEqual(x['status'],'CAUTION')
        self.assertIn('FETCH_TIMESTAMP_MISSING',x['flags'])
    def test_future_disclosure_date_blocked(self):
        future=(datetime.now(TR)+timedelta(days=1)).strftime('%d.%m.%Y')
        x=audit_disclosures([{'date':future}],time.time())
        self.assertEqual(x['status'],'BLOCK')

if __name__=='__main__':unittest.main()
