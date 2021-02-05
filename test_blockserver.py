import json
import os
import unittest
from typing import Callable

from genie_python.utilities import compress_and_hex

from utilities import utilities
import time
from genie_python import genie as g
import requests
from hamcrest import *
import socket


SECONDS_TO_WAIT_FOR_IOC_STARTS = 120


class TestBlockserver(unittest.TestCase):
    """
    Tests for top-level functionality of block server
    """
    def setUp(self) -> None:
        g.set_instrument(None, import_instrument_init=False)
        self.pvlist_file = os.path.join(r"C:\Instrument", "Settings", "gwblock.pvlist")
        self.rc_settings_file = os.path.join(
            r"C:\Instrument", "Settings", "config", socket.gethostname(), "configurations", "rc_settings.cmd"
        )
        self.config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "configs", "configurations")
        self.block_archive_blocks_url = "http://localhost:4813/group?name=BLOCKS&format=json"

    def test_GIVEN_config_changes_by_block_THEN_iocs_do_not_restart_except_for_caenv895(self):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        utilities.wait_for_iocs_to_be_up(["SIMPLE", "CAENV895_01"], SECONDS_TO_WAIT_FOR_IOC_STARTS)

        time.sleep(60)  # Time for IOCs to fully boot etc

        # Get the start time of the two IOCs
        simple_start_time_pv = "CS:IOC:SIMPLE:DEVIOS:STARTTOD"
        caen_start_time_pv = "CS:IOC:CAENV895_01:DEVIOS:STARTTOD"
        start_times = utilities.wait_for_string_pvs_to_not_be_empty(
            [simple_start_time_pv, caen_start_time_pv], SECONDS_TO_WAIT_FOR_IOC_STARTS, is_local=True
        )
        simple_start_time_before = start_times[simple_start_time_pv]
        caen_start_time_before = start_times[caen_start_time_pv]

        details = utilities.get_config_details()
        details["desc"] = "some_edited_description"
        g.set_pv("CS:BLOCKSERVER:SET_CURR_CONFIG_DETAILS", compress_and_hex(json.dumps(details)), is_local=True)

        err = None
        for _ in range(SECONDS_TO_WAIT_FOR_IOC_STARTS):
            try:
                # Get new start times
                start_times = utilities.wait_for_string_pvs_to_not_be_empty(
                    [simple_start_time_pv, caen_start_time_pv], SECONDS_TO_WAIT_FOR_IOC_STARTS, is_local=True
                )
                simple_start_time_after = start_times[simple_start_time_pv]
                caen_start_time_after = start_times[caen_start_time_pv]
                self.assertEqual(
                    simple_start_time_before, simple_start_time_after, "SIMPLE ioc should not have restarted"
                )
                self.assertNotEqual(
                    caen_start_time_before, caen_start_time_after, "CAENV895 ioc should have restarted"
                )
                break
            except (Exception, AssertionError) as e:
                err = e
                time.sleep(1)
        else:
            raise err

    def test_GIVEN_config_changes_to_empty_and_back_again_THEN_runcontrol_settings_reset_to_config_defaults(self):
        utilities.load_config_if_not_already_loaded("rcptt_simple")

        # Settings different than config default
        g.cset("FLOAT_BLOCK", runcontrol=True, lowlimit=123, highlimit=456)

        self.assertTrue(g.cget("FLOAT_BLOCK")["runcontrol"])

        utilities.load_config_if_not_already_loaded("empty_for_system_tests")
        utilities.load_config_if_not_already_loaded("rcptt_simple")

        self.assertFalse(g.cget("FLOAT_BLOCK")["runcontrol"])

    def test_GIVEN_config_explicitly_reloaded_THEN_runcontrol_settings_reset_to_config_defaults(self):
        utilities.load_config_if_not_already_loaded("rcptt_simple")

        # Settings different than config default
        g.cset("FLOAT_BLOCK", runcontrol=True, lowlimit=123, highlimit=456)

        self.assertTrue(g.cget("FLOAT_BLOCK")["runcontrol"])

        g.reload_current_config()

        # Give time for config to be fully reloaded.
        time.sleep(60)

        err = None
        for _ in range(SECONDS_TO_WAIT_FOR_IOC_STARTS):
            try:
                self.assertFalse(g.cget("FLOAT_BLOCK")["runcontrol"])
                break
            except AssertionError as e:
                err = e
                time.sleep(1)
        else:
            raise err

    def test_GIVEN_config_reloaded_THEN_alerts_username_and_pw_are_retained(self):
        utilities.load_config_if_not_already_loaded("rcptt_simple")

        url = "https://test.invalid/url/which/might/be/longer/than/40/characters"
        pw = "test_password"
        g.set_pv("CS:AC:ALERTS:URL:SP", url, is_local=True)
        g.set_pv("CS:AC:ALERTS:PW:SP", pw, is_local=True)

        # Give time for autosave to pick up the new values, in theory 30s is enough but wait a bit longer to be sure.
        time.sleep(60)

        g.reload_current_config()

        # Give time for config to be fully reloaded.
        time.sleep(60)

        err = None
        for _ in range(SECONDS_TO_WAIT_FOR_IOC_STARTS):
            try:
                self.assertEqual(g.get_pv("CS:AC:ALERTS:URL:SP", is_local=True), url)
                self.assertEqual(g.get_pv("CS:AC:ALERTS:PW:SP", is_local=True), pw)
                break
            except AssertionError as e:
                err = e
                time.sleep(1)
        else:
            raise err

    def test_GIVEN_config_contains_gw_and_archiver_files_THEN_archiver_uses_configuration_file(self):
        utilities.load_config_if_not_already_loaded("test_blockserver_with_gw_archiver")

        def assert_block_archive_blocks_group_has_one_channel():
            response = requests.get(self.block_archive_blocks_url).json()

            assert_that(len(response["Channels"]), is_(1))
            assert_that(response["Channels"][0]["Channel"], is_("PREFIX:MYTESTBLOCK"))

        utilities.retry_assert(5, assert_block_archive_blocks_group_has_one_channel)

    def test_GIVEN_config_claims_but_does_not_contain_gw_and_archiver_files_THEN_archiver_configuration_generated_by_blockserver(self):
        utilities.load_config_if_not_already_loaded("test_blockserver_without_gw_archiver")

        response = requests.get(self.block_archive_blocks_url).json()

        assert_that(len(response["Channels"]), is_(2))
        assert_that(response["Channels"][0]["Channel"], ends_with("TIZROUTOFRANGE"))
        assert_that(response["Channels"][1]["Channel"], ends_with("TIZRWARNING"))

    def test_GIVEN_config_does_not_contain_gw_and_archiver_files_THEN_archiver_configuration_generated_by_blockserver(self):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        response = requests.get(self.block_archive_blocks_url).json()

        assert_that(len(response["Channels"]), is_(1))
        assert_that(response["Channels"][0]["Channel"], ends_with("a"))

    def test_GIVEN_config_contains_gw_and_archiver_files_THEN_configuration_pvlist_used(self):
        config = "test_blockserver_with_gw_archiver"
        utilities.load_config_if_not_already_loaded(config)

        config_pvlist_file = os.path.join(self.config_dir, config, "gwblock.pvlist")
        with open(self.pvlist_file, "r") as pvlist, open(config_pvlist_file, "r") as config_pvlist:
            assert_that(pvlist.read(), is_(config_pvlist.read()))

    def test_GIVEN_config_claims_but_does_not_contain_gw_and_archiver_files_THEN_pvlist_generated(self):
        utilities.load_config_if_not_already_loaded("test_blockserver_without_gw_archiver")

        with open(self.pvlist_file, "r") as pvlist:
            file_content = pvlist.read()
            assert_that(file_content, contains_string("TIZRWARNING"))
            assert_that(file_content, contains_string("TIZROUTOFRANGE"))

    def test_GIVEN_config_does_not_contain_gw_and_archiver_files_THEN_pvlist_generated(self):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        with open(self.pvlist_file, "r") as pvlist:
            file_content = pvlist.read()
            assert_that(file_content, contains_string(g.prefix_pv_name("CS:SB:a")))

    def test_GIVEN_config_contains_rc_settings_THEN_configuration_rc_settings_used(self):
        config = "test_blockserver_with_gw_archiver"
        utilities.load_config_if_not_already_loaded(config)

        config_rc_settings_file = os.path.join(self.config_dir, config, "rc_settings.cmd")
        with open(self.rc_settings_file, "r") as rc_settings, open(config_rc_settings_file, "r") as config_rc_settings:
            assert_that(rc_settings.read(), is_(config_rc_settings.read()))

    def test_GIVEN_config_claims_but_does_not_contain_rc_settings_THEN_rc_settings_generated(self):
        utilities.load_config_if_not_already_loaded("test_blockserver_without_gw_archiver")

        with open(self.rc_settings_file, "r") as rc_settings:
            file_content = rc_settings.read()
            assert_that(file_content, contains_string("TIZRWARNING"))

    def test_GIVEN_config_does_not_contain_rc_settings_THEN_rc_settings_generated(self):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        with open(self.rc_settings_file, "r") as rc_settings:
            file_content = rc_settings.read()
            assert_that(file_content, contains_string("$(MYPVPREFIX)CS:SB:A"))
