from hamcrest import *
import unittest
import os

from utilities.utilities import load_config_if_not_already_loaded, g, setup_simulated_wiring_tables
from psutil import virtual_memory

TIMEOUT = 30
TYPICAL_CONFIG_NAME = "memory_usage"

# Contains the memory used by the machine before IBEX was started
BASE_MEMORY_USAGE = os.environ.get("BASE_MEMORY_USAGE", "0")


class TestMemoryUsage(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)

        setup_simulated_wiring_tables()

        # all tests that interact with anything but genie should try to load a config to ensure that the configurations
        # in the tests are not broken, e.g. by a schema update
        load_config_if_not_already_loaded(TYPICAL_CONFIG_NAME)

    def get_current_memory_usage(self):
        """
        Obtains the current system memory usage and returns it in gibibytes

        Returns:
            mem_usage: Float, system memory used in gibibytes (2^30 bytes)

        """
        mem_info = virtual_memory()

        total_bytes_used = float(mem_info.used) - float(BASE_MEMORY_USAGE)

        mem_usage = total_bytes_used / (2**30)

        print("Memory at start, after, diff: {}, {} {} GB".format(BASE_MEMORY_USAGE, mem_info.used, mem_usage))

        return mem_usage

    def test_GIVEN_typical_config_with_IOCs_blocks_and_LVDCOM_IOC_WHEN_dae_is_doing_a_run_THEN_memory_usage_stays_under_9point5gb(self):
        threshold = 9.5

        g.begin()

        memory_used = self.get_current_memory_usage()

        assert_that(memory_used, less_than(threshold))

    def test_GIVEN_typical_config_with_IOCs_blocks_and_LVDCOM_IOC_WHEN_dae_is_not_doing_a_run_THEN_memory_usage_stays_under_7point5gb(self):
        threshold = 7.5

        memory_used = self.get_current_memory_usage()

        assert_that(memory_used, less_than(threshold))
