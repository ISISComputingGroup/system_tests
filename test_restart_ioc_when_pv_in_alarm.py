import unittest

from general.utilities.restart_ioc_when_pv_in_alarm import restart_ioc_when_pv_in_alarm
from genie_python.genie_startup import *

from utilities.utilities import load_config_if_not_already_loaded

BLOCK_NAME = "TEST_BLOCK"


class TestRestartIocWhenPvInAlarm(unittest.TestCase):
    """
    Tests for the `restart_ioc_when_pv_in_alarm` script.
    """

    def setUp(self) -> None:
        g.set_instrument(None, import_instrument_init=False)
        load_config_if_not_already_loaded("test_restart_ioc_when_pv_in_alarm")
        self.thread = restart_ioc_when_pv_in_alarm(
            "TEST_BLOCK", ["SIMPLE"], ["GRUMPY"], wait_between_restarts=15
        )

    def tearDown(self) -> None:
        self.thread.stop()
        self.thread.join()

    def test_WHEN_ioc_in_alarm_THEN_ioc_restarted(self):
        g.cset(BLOCK_NAME, 0)
        self.assertEqual(g.cget(BLOCK_NAME)["value"], "HAPPY")

        g.cset(BLOCK_NAME, 3)
        self.assertEqual(g.cget(BLOCK_NAME)["value"], "GRUMPY")
        # Give the IOC some time to start back up.
        g.waitfor_time(seconds=30)

        self.assertEqual(g.cget(BLOCK_NAME)["value"], "HAPPY")
