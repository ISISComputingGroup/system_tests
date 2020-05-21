from hamcrest import *
import unittest
import os

from utilities.utilities import load_config_if_not_already_loaded, g, setup_simulated_wiring_tables, BASE_MEMORY_USAGE
from psutil import virtual_memory

TIMEOUT = 30
TYPICAL_CONFIG_NAME = "memory_usage"

# Contains the memory used by the machine before IBEX was started
BASE_MEMORY_USAGE_IN_BYTES = os.environ.get(BASE_MEMORY_USAGE, "0")

# The assumed memory usage from the rest of the system e.g. os
ASSUMED_NON_IBEX_USAGE = 2.0


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
            mem_usage_difference_gigabytes: Float, system memory used in gibibytes (2^30 bytes)

        """
        mem_info = virtual_memory()

        total_bytes_used_difference = float(mem_info.used) - float(BASE_MEMORY_USAGE_IN_BYTES)

        mem_usage_difference_gigabytes = total_bytes_used_difference / (2 ** 30)

        base_memory_usage_gigabytes = float(BASE_MEMORY_USAGE_IN_BYTES) / (2 ** 30)
        total_memory_usage_gigabytes = float(mem_info.used) / (2 ** 30)

        print("Memory at start, after, diff: {}, {}, {} GB".format(base_memory_usage_gigabytes,
                                                                  total_memory_usage_gigabytes, mem_usage_difference_gigabytes))

        return mem_usage_difference_gigabytes

    def test_GIVEN_typical_config_with_IOCs_blocks_and_LVDCOM_IOC_WHEN_dae_is_doing_a_run_THEN_memory_usage_stays_under_9point5gb(self):
        system_threshold = 9.5

        g.begin()

        memory_used = self.get_current_memory_usage()

        assert_that(memory_used, less_than(system_threshold-ASSUMED_NON_IBEX_USAGE))

    def test_GIVEN_typical_config_with_IOCs_blocks_and_LVDCOM_IOC_WHEN_dae_is_not_doing_a_run_THEN_memory_usage_stays_under_7point5gb(self):
        system_threshold = 7.5

        memory_used = self.get_current_memory_usage()

        assert_that(memory_used, less_than(system_threshold-ASSUMED_NON_IBEX_USAGE))
