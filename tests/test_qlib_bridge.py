import unittest
from app.qlib_bridge import feature_frame_from_rows,causality_check_rows,adapter_status,FEATURES

def rows(n=320):
    out=[];px=100.0
    for i in range(n):
        px*=1+(0.0005 if i%7 else -0.0003)
        out.append({'time':f'2026-01-{(i%28)+1:02d}-{i//28:02d}','open':px*.998,'high':px*1.01,'low':px*.99,'close':px,'volume':100000+i*100})
    return out

class QlibBridgeTests(unittest.TestCase):
    def test_feature_frame_shape(self):
        f=feature_frame_from_rows(rows())
        for x in FEATURES:self.assertIn(x,f.columns)
        self.assertIn('label_5d',f.columns)
    def test_prefix_causality(self):
        r=causality_check_rows(rows())
        self.assertEqual(r['status'],'PASS')
    def test_optional_adapter_never_required(self):
        s=adapter_status()
        self.assertIn(s['status'],{'READY','ADAPTER_UNAVAILABLE'})

if __name__=='__main__':unittest.main()
