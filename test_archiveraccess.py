import os
import glob
import unittest
import time

from utilities import utilities
from genie_python import genie as g


IOC_NAME = "INSTRON_01"
LOGS_PATH = os.path.join("C:\\", "logs", IOC_NAME)


class TestArchiverAccess(unittest.TestCase):
    """
    Tests for top-level functionality of Archiver Access.
    """
    def _create_logs(self, populate_wait_time=60, write_wait_time=60):
        utilities.start_ioc(IOC_NAME)
        self.assertTrue(utilities.is_ioc_up(IOC_NAME))
        g.set_pv("INSTRON_01:LOG:RECORD:SP", value=1, wait=True, is_local=True)
        time.sleep(populate_wait_time)
        g.set_pv("INSTRON_01:LOG:RECORD:SP", value=0, wait=True, is_local=True)
        time.sleep(write_wait_time)
        utilities.stop_ioc(IOC_NAME)

        logs = glob.glob(os.path.join(LOGS_PATH, "*"))
        logs = sorted(logs, key=os.path.getctime, reverse=True)

        self.assertGreaterEqual(len(logs), 2, "Logs(s) not generated.")
        
        if len(logs[0]) < len(logs[1]):
            log_full = logs[0]
            log_continuous = logs[1]
        else:
            log_full = logs[1]
            log_continuous = logs[0]

        print(f"Archiver Access Full log:\n{logs[0]}\nArchiver Access Continuous log:\n{logs[1]}")
        
        self.assertTrue(log_full.strip(".dat") in log_continuous.strip(".dat"), "Logs(s) not generated.")

        log_full_lines = open(os.path.join(LOGS_PATH, log_full)).readlines()
        log_continuous_lines = open(os.path.join(LOGS_PATH, log_continuous)).readlines()

        return (log_full_lines, log_continuous_lines)


    def setUp(self) -> None:
        g.set_instrument(None, import_instrument_init=False)


    def test_WHEN_logs_created_THEN_full_and_continuous_logs_sizes_equal(self):
        log_full, log_continuous = self._create_logs()
        self.assertEqual(len(log_full), len(log_continuous), "Logs are different sizes.")

    def test_WHEN_logs_created_THEN_no_duplicate_entries_in_logs(self):
        log_full, log_continuous = self._create_logs()
        self.assertEqual(len(log_full), len(set(log_full)), "Full log has duplicate entries.")
        self.assertEqual(len(log_continuous), len(set(log_continuous)), "Continuous log has duplicate entries.")
