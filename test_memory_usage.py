import os
import unittest

from hamcrest import *
from psutil import AccessDenied, process_iter, virtual_memory

from utilities.utilities import (
    BASE_MEMORY_USAGE,
    g,
    load_config_if_not_already_loaded,
    setup_simulated_wiring_tables,
)

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

        mem_usage_difference_gigabytes = total_bytes_used_difference / (2**30)

        base_memory_usage_gigabytes = float(BASE_MEMORY_USAGE_IN_BYTES) / (2**30)
        total_memory_usage_gigabytes = float(mem_info.used) / (2**30)

        print(
            "Memory at start, after, diff: {}, {}, {} GB".format(
                base_memory_usage_gigabytes,
                total_memory_usage_gigabytes,
                mem_usage_difference_gigabytes,
            )
        )

        return mem_usage_difference_gigabytes

    def test_GIVEN_typical_config_with_IOCs_blocks_and_LVDCOM_IOC_WHEN_dae_is_doing_a_run_THEN_memory_usage_stays_under_9point5gb(
        self,
    ):
        system_threshold = 9.5

        g.begin()

        memory_used = self.get_current_memory_usage()

        assert_that(memory_used, less_than(system_threshold - ASSUMED_NON_IBEX_USAGE))

    def test_GIVEN_typical_config_with_IOCs_blocks_and_LVDCOM_IOC_WHEN_dae_is_not_doing_a_run_THEN_memory_usage_stays_under_7point5gb(
        self,
    ):
        system_threshold = 8.5

        memory_used = self.get_current_memory_usage()

        assert_that(memory_used, less_than(system_threshold - ASSUMED_NON_IBEX_USAGE))

    def get_matching_process_cmdline_substring_from_process_or_none(
        self, process, process_cmdline_substrings
    ):
        """
        Get the first substring from process_cmdline_substrings that is contained in the cmdline call for the process
         or None if no substrings match.
        """
        cmdline = " ".join(process.cmdline())
        for process_cmdline_substring in process_cmdline_substrings:
            if process_cmdline_substring in cmdline:
                return process_cmdline_substring

    def get_commit_sizes_in_kb(self, process_cmdline_substrings):
        """
        Get the commit sizes of the processes that contain the given substrings in their command line call.
        """
        commit_sizes_kb = {}
        for process in process_iter():
            try:
                process_cmdline_found = (
                    self.get_matching_process_cmdline_substring_from_process_or_none(
                        process, process_cmdline_substrings
                    )
                )
                if process_cmdline_found is not None:
                    commit_size_kb = process.memory_info().private / 1000
                    commit_sizes_kb[process_cmdline_found] = commit_size_kb
            except AccessDenied:
                continue
        return commit_sizes_kb

    def assert_commit_sizes_are_less_than_expected_max_commit_size(
        self, process_cmdline_substrings_and_expected_max_commit_size, commit_sizes_in_kb
    ):
        assertion_error_occurred = False
        for process_cmdline_substring, commit_size_in_kb in commit_sizes_in_kb.items():
            try:
                assert_that(
                    commit_size_in_kb,
                    less_than(
                        process_cmdline_substrings_and_expected_max_commit_size[
                            process_cmdline_substring
                        ]
                    ),
                )
            except AssertionError:
                assertion_error_occurred = True
        if assertion_error_occurred:
            raise AssertionError(
                f"Expected commit size to be less than values: {process_cmdline_substrings_and_expected_max_commit_size}. Actually got: {commit_sizes_in_kb}"
            )

    def test_GIVEN_standard_setup_THEN_commit_size_of_python_processes_are_reasonable(self):
        process_cmdline_substrings_and_expected_max_commit_size = {
            "block_server.py": 950000,
            "database_server.py": 950000,
        }
        commit_sizes_in_kb = self.get_commit_sizes_in_kb(
            process_cmdline_substrings_and_expected_max_commit_size.keys()
        )
        # Assert all substrings have been found
        assert_that(
            len(commit_sizes_in_kb),
            is_(len(process_cmdline_substrings_and_expected_max_commit_size)),
        )
        self.assert_commit_sizes_are_less_than_expected_max_commit_size(
            process_cmdline_substrings_and_expected_max_commit_size, commit_sizes_in_kb
        )
