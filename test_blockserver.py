import json
import os
import socket
import time
import unittest

import requests
from genie_python import genie as g
from genie_python.channel_access_exceptions import UnableToConnectToPVException
from genie_python.utilities import compress_and_hex
from hamcrest import assert_that, contains_string, ends_with, is_
from parameterized import parameterized

from utilities import utilities
from utilities.utilities import assert_with_timeout, parameterized_list

SECONDS_TO_WAIT_FOR_IOC_STARTS = 120


def wait_for_server():
    status_was_busy = False
    for _ in range(utilities.WAIT_FOR_SERVER_TIMEOUT):
        status = utilities.get_server_status()
        if status_was_busy and status == "":
            break
        if status is not None and status != "":
            status_was_busy = True
        time.sleep(1)


def test_pv_with_macro_value(macro_value, pv, test_case):
    if macro_value == "":
        test_case.assertRaises(UnableToConnectToPVException, g.get_pv, pv, is_local=True)
    else:
        test_case.assertEqual(
            g.get_pv(
                pv,
                is_local=True,
            ),
            macro_value,
        )


def test_config_macros(
    use_default, config_macro, default_value, macro_value, macro_name, test_case
):
    if use_default:
        test_case.assertNotIn(macro_name, config_macro)
        return default_value
    else:
        test_case.assertIn(macro_name, config_macro)
        test_case.assertEqual(macro_value, config_macro[macro_name]["value"])
        test_case.assertNotIn("useDefault", config_macro[macro_name])
        if macro_value == "":
            return default_value
        return macro_value


class TestBlockserver(unittest.TestCase):
    """
    Tests for top-level functionality of block server
    """

    def setUp(self) -> None:
        g.set_instrument(None, import_instrument_init=False)
        self.pvlist_file = os.path.join(r"C:\Instrument", "Settings", "gwblock.pvlist")
        self.rc_settings_file = os.path.join(
            r"C:\Instrument",
            "Settings",
            "config",
            socket.gethostname(),
            "configurations",
            "rc_settings.cmd",
        )
        self.config_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "configs", "configurations"
        )
        self.block_archive_blocks_url = "http://localhost:4813/group?name=BLOCKS&format=json"

    def test_GIVEN_config_changes_THEN_dae_and_instetc_come_back_with_autorestart_reapplied(
        self,
    ):
        g.reload_current_config()
        iocs_to_check = ["ISISDAE_01", "INSTETC_01"]
        utilities.wait_for_iocs_to_be_up(iocs_to_check, SECONDS_TO_WAIT_FOR_IOC_STARTS)

        # give the blockserver some time to reapply autorestart
        time.sleep(10)

        for ioc in iocs_to_check:
            status = g.get_pv(f"CS:PS:{ioc}:STATUS", is_local=True)
            autorestart = g.get_pv(f"CS:PS:{ioc}:AUTORESTART", is_local=True)
            self.assertEqual(status.lower(), "running")
            self.assertEqual(autorestart.lower(), "on")

    def test_GIVEN_config_changes_by_block_THEN_iocs_do_not_restart_except_for_caenv895(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        utilities.wait_for_iocs_to_be_up(["SIMPLE", "CAENV895_01"], SECONDS_TO_WAIT_FOR_IOC_STARTS)

        time.sleep(60)  # Time for IOCs to fully boot etc

        # Get the start time of the two IOCs
        simple_start_time_pv = "CS:IOC:SIMPLE:DEVIOS:STARTTOD"
        caen_start_time_pv = "CS:IOC:CAENV895_01:DEVIOS:STARTTOD"
        start_times = utilities.wait_for_string_pvs_to_not_be_empty(
            [simple_start_time_pv, caen_start_time_pv],
            SECONDS_TO_WAIT_FOR_IOC_STARTS,
            is_local=True,
        )
        simple_start_time_before = start_times[simple_start_time_pv]
        caen_start_time_before = start_times[caen_start_time_pv]

        details = utilities.get_config_details()
        details["desc"] = "some_edited_description"
        g.set_pv(
            "CS:BLOCKSERVER:SET_CURR_CONFIG_DETAILS",
            compress_and_hex(json.dumps(details)),
            is_local=True,
        )

        err = None
        for _ in range(SECONDS_TO_WAIT_FOR_IOC_STARTS):
            try:
                # Get new start times
                start_times = utilities.wait_for_string_pvs_to_not_be_empty(
                    [simple_start_time_pv, caen_start_time_pv],
                    SECONDS_TO_WAIT_FOR_IOC_STARTS,
                    is_local=True,
                )
                simple_start_time_after = start_times[simple_start_time_pv]
                caen_start_time_after = start_times[caen_start_time_pv]
                self.assertEqual(
                    simple_start_time_before,
                    simple_start_time_after,
                    "SIMPLE ioc should not have restarted",
                )
                self.assertNotEqual(
                    caen_start_time_before,
                    caen_start_time_after,
                    "CAENV895 ioc should have restarted",
                )
                break
            except (Exception, AssertionError) as e:
                err = e
                time.sleep(1)
        else:
            if err is not None:
                raise err

    @parameterized.expand(
        parameterized_list(
            [
                ("simple1", "simple2"),  # Move IOC between 2 configs
                (
                    "simple_comp_macros",
                    "simple_comp_macros_2",
                ),  # Move IOC between two components
                (
                    "simple_with_macros",
                    "simple_comp_macros",
                ),  # Move IOC between config and component
            ]
        )
    )
    def test_GIVEN_config_changes_by_ioc_and_ioc_has_same_settings_in_old_and_new_WHEN_changing_configs_THEN_ioc_not_restarted(
        self, _, old_config, new_config
    ):
        utilities.load_config_if_not_already_loaded(old_config)

        utilities.wait_for_iocs_to_be_up(["SIMPLE"], SECONDS_TO_WAIT_FOR_IOC_STARTS)
        time.sleep(30)  # Time for IOCs to fully boot etc

        simple_start_time_pv = "CS:IOC:SIMPLE:DEVIOS:STARTTOD"
        simple_start_time = utilities.wait_for_string_pvs_to_not_be_empty(
            [simple_start_time_pv], SECONDS_TO_WAIT_FOR_IOC_STARTS, is_local=True
        )[simple_start_time_pv]

        # Load a config containing a different IOC, but still containing SIMPLE (with the same settings as before)
        utilities.load_config_if_not_already_loaded(new_config)
        utilities.wait_for_iocs_to_be_up(["SIMPLE"], SECONDS_TO_WAIT_FOR_IOC_STARTS)
        time.sleep(30)  # Time for IOCs to fully boot etc

        new_simple_start_time = utilities.wait_for_string_pvs_to_not_be_empty(
            [simple_start_time_pv], SECONDS_TO_WAIT_FOR_IOC_STARTS, is_local=True
        )[simple_start_time_pv]

        # Assert that SIMPLE start time has not changed, i.e. SIMPLE didn't restart as a result of the config change.
        self.assertEqual(simple_start_time, new_simple_start_time)

    @parameterized.expand(
        parameterized_list(
            [
                ("simple1", "simple_with_macros"),  # Config -> config
                (
                    "simple_comp_no_macros",
                    "simple_comp_macros",
                ),  # Component -> component
                ("simple1", "simple_comp_macros"),  # Config -> Component
                ("simple_comp_macros", "simple1"),  # Component -> Config
            ]
        )
    )
    def test_GIVEN_config_changes_by_ioc_and_ioc_has_different_settings_in_old_and_new_WHEN_changing_configs_THEN_ioc_is_restarted(
        self, _, old_config, new_config
    ):
        utilities.load_config_if_not_already_loaded(old_config)

        utilities.wait_for_iocs_to_be_up(["SIMPLE"], SECONDS_TO_WAIT_FOR_IOC_STARTS)
        time.sleep(30)  # Time for IOCs to fully boot etc

        simple_start_time_pv = "CS:IOC:SIMPLE:DEVIOS:STARTTOD"
        simple_start_time = utilities.wait_for_string_pvs_to_not_be_empty(
            [simple_start_time_pv], SECONDS_TO_WAIT_FOR_IOC_STARTS, is_local=True
        )[simple_start_time_pv]

        # Load a config containing a different IOC, but still containing SIMPLE (with the same settings as before)
        utilities.load_config_if_not_already_loaded(new_config)
        utilities.wait_for_iocs_to_be_up(["SIMPLE"], SECONDS_TO_WAIT_FOR_IOC_STARTS)
        time.sleep(30)  # Time for IOCs to fully boot etc

        new_simple_start_time = utilities.wait_for_string_pvs_to_not_be_empty(
            [simple_start_time_pv], SECONDS_TO_WAIT_FOR_IOC_STARTS, is_local=True
        )[simple_start_time_pv]

        # Assert that SIMPLE start time has changed, as the IOC has different settings in the new config
        self.assertNotEqual(simple_start_time, new_simple_start_time)

    def test_GIVEN_manually_started_ioc_WHEN_changing_to_config_containing_ioc_but_without_autostart_THEN_ioc_stopped(
        self,
    ):
        utilities.load_config_if_not_already_loaded("empty_for_system_tests")

        assert_with_timeout(
            lambda: self.assertEqual(utilities.is_ioc_up("SIMPLE"), False), timeout=30
        )

        utilities.start_ioc("SIMPLE")

        assert_with_timeout(
            lambda: self.assertEqual(utilities.is_ioc_up("SIMPLE"), True), timeout=30
        )

        utilities.load_config_if_not_already_loaded("simple_without_autostart")

        assert_with_timeout(
            lambda: self.assertEqual(utilities.is_ioc_up("SIMPLE"), False), timeout=30
        )

    ## comment out now as need to check expected behaviour, this may have chanegd when
    #    def test_GIVEN_config_changes_to_empty_and_back_again_THEN_runcontrol_settings_reset_to_config_defaults(self):
    #        utilities.load_config_if_not_already_loaded("rcptt_simple")
    #        time.sleep(60)
    #        self.assertFalse(g.cget("FLOAT_BLOCK")["runcontrol"])
    #
    #        # Settings different than config default
    #        g.cset("FLOAT_BLOCK", runcontrol=True, lowlimit=123, highlimit=456)
    #
    #        self.assertTrue(g.cget("FLOAT_BLOCK")["runcontrol"])
    #
    #        utilities.load_config_if_not_already_loaded("empty_for_system_tests")
    #        time.sleep(60)
    #        utilities.load_config_if_not_already_loaded("rcptt_simple")
    #        time.sleep(60)
    #
    #        self.assertFalse(g.cget("FLOAT_BLOCK")["runcontrol"])

    ## comment out now as need to check expected behaviour, this may have chanegd when
    ## configuration loading was optimised
    #    def test_GIVEN_config_explicitly_reloaded_THEN_runcontrol_settings_reset_to_config_defaults(self):
    #        utilities.load_config_if_not_already_loaded("rcptt_simple")
    #        time.sleep(60)
    #        assert_with_timeout(assertion=lambda: self.assertFalse(g.cget("FLOAT_BLOCK")["runcontrol"]), timeout=60)
    #
    #        # Settings different than config default
    #        g.cset("FLOAT_BLOCK", runcontrol=True, lowlimit=123, highlimit=456)
    #        assert_with_timeout(assertion=lambda: self.assertTrue(g.cget("FLOAT_BLOCK")["runcontrol"]), timeout=60)
    #
    #        g.reload_current_config()
    #
    #        assert_with_timeout(assertion=lambda: self.assertFalse(g.cget("FLOAT_BLOCK")["runcontrol"]), timeout=120)

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

        assert_with_timeout(
            assertion=lambda: self.assertEqual(g.get_pv("CS:AC:ALERTS:URL:SP", is_local=True), url),
            timeout=SECONDS_TO_WAIT_FOR_IOC_STARTS,
        )
        assert_with_timeout(
            assertion=lambda: self.assertEqual(g.get_pv("CS:AC:ALERTS:PW:SP", is_local=True), pw),
            timeout=SECONDS_TO_WAIT_FOR_IOC_STARTS,
        )

    def test_GIVEN_config_contains_gw_and_archiver_files_THEN_archiver_uses_configuration_file(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver_with_gw_archiver")
        time.sleep(30)

        def assert_block_archive_blocks_group_has_one_channel():
            response = requests.get(self.block_archive_blocks_url).json()

            assert_that(len(response["Channels"]), is_(1))
            assert_that(response["Channels"][0]["Channel"], is_("PREFIX:MYTESTBLOCK"))

        utilities.retry_assert(5, assert_block_archive_blocks_group_has_one_channel, 3.0)

    def test_GIVEN_config_claims_but_does_not_contain_gw_and_archiver_files_THEN_archiver_configuration_generated_by_blockserver(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver_without_gw_archiver")
        time.sleep(30)

        response = requests.get(self.block_archive_blocks_url).json()

        assert_that(len(response["Channels"]), is_(2))
        assert_that(response["Channels"][0]["Channel"], ends_with("TIZROUTOFRANGE"))
        assert_that(response["Channels"][1]["Channel"], ends_with("TIZRWARNING"))

    def test_GIVEN_config_does_not_contain_gw_and_archiver_files_THEN_archiver_configuration_generated_by_blockserver(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        response = requests.get(self.block_archive_blocks_url).json()

        assert_that(len(response["Channels"]), is_(1))
        assert_that(response["Channels"][0]["Channel"], ends_with("a"))

    def test_GIVEN_config_contains_gw_and_archiver_files_THEN_configuration_pvlist_used(
        self,
    ):
        config = "test_blockserver_with_gw_archiver"
        utilities.load_config_if_not_already_loaded(config)

        config_pvlist_file = os.path.join(self.config_dir, config, "gwblock.pvlist")
        with (
            open(self.pvlist_file, "r") as pvlist,
            open(config_pvlist_file, "r") as config_pvlist,
        ):
            assert_that(pvlist.read(), is_(config_pvlist.read()))

    def test_GIVEN_config_claims_but_does_not_contain_gw_and_archiver_files_THEN_pvlist_generated(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver_without_gw_archiver")

        with open(self.pvlist_file, "r") as pvlist:
            file_content = pvlist.read()
            assert_that(file_content, contains_string("TIZRWARNING"))
            assert_that(file_content, contains_string("TIZROUTOFRANGE"))

    def test_GIVEN_config_does_not_contain_gw_and_archiver_files_THEN_pvlist_generated(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        with open(self.pvlist_file, "r") as pvlist:
            file_content = pvlist.read()
            assert_that(file_content, contains_string(g.prefix_pv_name("CS:SB:a")))

    def test_GIVEN_config_contains_rc_settings_THEN_configuration_rc_settings_used(
        self,
    ):
        config = "test_blockserver_with_gw_archiver"
        utilities.load_config_if_not_already_loaded(config)

        config_rc_settings_file = os.path.join(self.config_dir, config, "rc_settings.cmd")
        with (
            open(self.rc_settings_file, "r") as rc_settings,
            open(config_rc_settings_file, "r") as config_rc_settings,
        ):
            assert_that(rc_settings.read(), is_(config_rc_settings.read()))

    def test_GIVEN_config_claims_but_does_not_contain_rc_settings_THEN_rc_settings_generated(
        self,
    ):
        utilities.load_config_if_not_already_loaded("test_blockserver_without_gw_archiver")

        with open(self.rc_settings_file, "r") as rc_settings:
            file_content = rc_settings.read()
            assert_that(file_content, contains_string("TIZRWARNING"))

    def test_GIVEN_config_does_not_contain_rc_settings_THEN_rc_settings_generated(self):
        utilities.load_config_if_not_already_loaded("test_blockserver")

        with open(self.rc_settings_file, "r") as rc_settings:
            file_content = rc_settings.read()
            assert_that(file_content, contains_string("$(MYPVPREFIX)CS:SB:A"))

    def test_WHEN_block_is_added_to_active_config_via_save_new_config_pv_THEN_block_added(
        self,
    ):
        configuration_name = "test_blockserver_save_active_config"
        block_name = "TEST_BLOCK"
        utilities.load_config_if_not_already_loaded(configuration_name)

        data = {}
        data["name"] = configuration_name
        data["blocks"] = [
            {
                "name": block_name,
                "pv": "TEST_PV",
            }
        ]

        g.set_pv(
            "CS:BLOCKSERVER:SAVE_NEW_CONFIG",
            compress_and_hex(json.dumps(data)),
            wait=True,
            is_local=True,
        )
        wait_for_server()
        self.assertTrue(utilities.check_block_exists(block_name))

    @parameterized.expand(
        parameterized_list(
            [
                ("_No_Vals_All_Default", "", True, "", True, "", True),
                ("_No_Vals_No_Default", "", False, "", False, "", False),
                ("_Required_Vals_Else_Default", "1", False, "", True, "3", False),
                ("_set_Vals_All_Default", "1", True, "2", True, "3", True),
                ("_set_Vals_No_Default", "1", False, "2", False, "3", False),
            ]
        )
    )
    def test_WHEN_ioc_has_macros_THEN_defaults_handled_correctly(
        self,
        _,
        name,
        macro_1_val,
        macro_1_use_default,
        macro_2_val,
        macro_2_use_default,
        macro_3_val,
        macro_3_use_default,
    ):
        configuration_name = "test_blockserver_save_active_config"
        utilities.load_config_if_not_already_loaded(configuration_name)
        data = {}
        data["name"] = configuration_name
        data["iocs"] = [
            {
                "name": "SIMPLE",
                "autostart": "true",
                "restart": "true",
                "macros": [
                    {
                        "name": "MACRO1",
                        "value": f"{macro_1_val}",
                        "description": "A macro without a default",
                        "pattern": "",
                        "defaultValue": "",
                        "useDefault": f"{macro_1_use_default}",
                        "hasDefault": "NO",
                    },
                    {
                        "name": "MACRO2",
                        "value": f"{macro_2_val}",
                        "description": "A macro with a default of 5",
                        "pattern": "",
                        "defaultValue": "",
                        "useDefault": f"{macro_2_use_default}",
                        "hasDefault": "YES",
                    },
                    {
                        "name": "MACRO3",
                        "value": f"{macro_3_val}",
                        "description": "A macro with a default of ''",
                        "pattern": "",
                        "defaultValue": "",
                        "useDefault": f"{macro_3_use_default}",
                        "hasDefault": "YES",
                    },
                ],
            }
        ]

        g.set_pv(
            "CS:BLOCKSERVER:SAVE_NEW_CONFIG",
            compress_and_hex(json.dumps(data)),
            wait=True,
            is_local=True,
        )
        wait_for_server()
        macros_in_config = utilities.get_config_details()["iocs"][0]["macros"]
        macros_in_config = {macro["name"]: macro for macro in macros_in_config}
        expected_1 = test_config_macros(
            macro_1_use_default, macros_in_config, "", macro_1_val, "MACRO1", self
        )
        expected_2 = test_config_macros(
            macro_2_use_default, macros_in_config, "5", macro_2_val, "MACRO2", self
        )
        expected_3 = test_config_macros(
            macro_3_use_default, macros_in_config, "", macro_3_val, "MACRO3", self
        )

        assert_with_timeout(
            lambda: self.assertTrue(utilities.is_ioc_up("SIMPLE")),
            timeout=SECONDS_TO_WAIT_FOR_IOC_STARTS,
        )
        test_pv_with_macro_value(expected_1, "SIMPLE:MACROTEST1", self)
        test_pv_with_macro_value(expected_2, "SIMPLE:MACROTEST2", self)
        test_pv_with_macro_value(expected_3, "SIMPLE:MACROTEST3", self)
