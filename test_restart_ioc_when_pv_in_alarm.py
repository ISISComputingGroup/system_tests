import unittest

from genie_python.genie_startup import *
from general.utilities.restart_ioc_when_pv_in_alarm import restart_ioc_when_pv_in_alarm
from utilities.utilities import load_config_if_not_already_loaded


class TestRestartIocWhenPvInAlarm(unittest.TestCase):
    """
    Tests for the `restart_ioc_when_pv_in_alarm` script.
    """
    def setUp(self) -> None:
        g.set_instrument(None, import_instrument_init=False)
        load_config_if_not_already_loaded("test_restart_ioc_when_pv_in_alarm")
        

    def test_WHEN_ioc_in_alarm_THEN_ioc_restarted(self):
        self.assertEqual(g.get_pv("SIMPLE:MBBI", is_local=True), "HAPPY")
        restart_ioc_when_pv_in_alarm("TEST_BLOCK", ["SIMPLE"], ["GRUMPY"], wait_between_restarts=15)

        g.set_pv("SIMPLE:MBBI", value=3, wait=True, is_local=True)
        self.assertEqual(g.get_pv("SIMPLE:MBBI", is_local=True), "GRUMPY")
        # Give the IOC some time to start back up.
        g.waitfor_time(seconds=30)

        self.assertEqual(g.get_pv("SIMPLE:MBBI", is_local=True), "HAPPY")
