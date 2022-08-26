import os
import glob
import unittest
import time

from parameterized import parameterized
from utilities import utilities
from utilities.utilities import parameterized_list
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

        logs = glob.glob(os.path.join(LOGS_PATH, "*"))
        logs = sorted(logs, key=os.path.getctime, reverse=True)

        self.assertGreaterEqual(len(logs), 2, "Logs(s) not generated.")
        
        if logs[0].endswith("continuous.dat"):
            log_continuous = logs[0]
            log_full = logs[1]
        elif logs[1].endswith("continuous.dat"):
            log_continuous = logs[1]
            log_full = logs[0]
        else:
            self.fail("Continuos Log not generated.")

        print(f"Archiver Access Full Log: {logs[0]}\nArchiver Access Continuous Log: {logs[1]}")

        self.assertTrue(log_full.strip(".dat") in log_continuous.strip(".dat"), "Logs(s) not generated.")

        log_full_lines = open(os.path.join(LOGS_PATH, log_full)).readlines()
        log_continuous_lines = open(os.path.join(LOGS_PATH, log_continuous)).readlines()

        return (log_full_lines, log_continuous_lines)


    def setUp(self) -> None:
        g.set_instrument(None, import_instrument_init=False)


    @parameterized.expand(parameterized_list([5, 30, 60]))
    def test_WHEN_logs_created_THEN_full_and_continuous_logs_sizes_equal(self, _, wait_time):
        log_full, log_continuous = self._create_logs(populate_wait_time=wait_time)
        self.assertEqual(len(log_full), len(log_continuous), "Logs are different sizes.")

    @parameterized.expand(parameterized_list([5, 30, 60]))
    def test_WHEN_logs_created_THEN_no_duplicate_entries_in_logs(self, _, wait_time):
        log_full, log_continuous = self._create_logs(populate_wait_time=wait_time)
        self.assertEqual(len(log_full), len(set(log_full)), "Full Log has duplicate entries.")
        self.assertEqual(len(log_continuous), len(set(log_continuous)), "Continuous Log has duplicate entries.")

    @parameterized.expand(parameterized_list([5, 30, 60]))
    def test_WHEN_logs_created_THEN_no_missing_values(self, _, wait_time):
        NUM_HEADER_LINES = 5
        log_full, log_continuous = self._create_logs(populate_wait_time=wait_time)

        log_full_entries = log_full[NUM_HEADER_LINES:]
        log_continuous_entries = log_continuous[NUM_HEADER_LINES:]

        log_full_num_measurements_per_entry = [len(x.split()) for x in log_full_entries]
        log_continuous_num_measurements_per_entry = [len(x.split()) for x in log_continuous_entries]

        self.assertEqual(len(set(log_full_num_measurements_per_entry)), 1)
        self.assertEqual(len(set(log_continuous_num_measurements_per_entry)), 1)
