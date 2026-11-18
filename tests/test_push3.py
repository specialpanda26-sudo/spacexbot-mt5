import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from unittest.mock import patch
from backend import push, accounts

class TestPushSectionN2(unittest.TestCase):
    def setUp(self):
        self.default_notif = accounts.DEF_NOTIF.copy()

    def test_daily_cap_default(self):
        self.assertEqual(push.MAX_PER_DAY, 30)

    def test_quiet_hours_trade_results_bypass(self):
        for kind in [2, 3, 4]:
            self.assertFalse(push.quiet_now(self.default_notif, kind=kind))

    @patch('backend.push.dt.datetime')
    def test_quiet_hours_standard_check(self, mock_dt):
        mock_now = mock_dt.fromtimestamp.return_value
        mock_now.hour = 23
        self.assertTrue(push.quiet_now(self.default_notif, kind=1))

        mock_now.hour = 14
        self.assertFalse(push.quiet_now(self.default_notif, kind=1))

if __name__ == '__main__':
    unittest.main()
