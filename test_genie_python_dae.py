import time
import unittest
from datetime import datetime

import h5py
import random
import os
from time import sleep

from utilities.utilities import g, stop_ioc, start_ioc, wait_for_ioc_start_stop, \
    set_genie_python_raises_exceptions, setup_simulated_wiring_tables, \
    set_wait_for_complete_callback_dae_settings, temporarily_kill_icp, \
    load_config_if_not_already_loaded, _wait_for_and_assert_dae_simulation_mode, parameterized_list

from parameterized import parameterized
from contextlib import contextmanager

EXTREMELY_LARGE_NO_OF_PERIODS = 1000000

DAE_PERIOD_TIMEOUT_SECONDS = 15

BLOCK_FORMAT_PATTERN = "@{block_name}@"


def nexus_file_with_retry(instrument, run_number, test_func):
    # isisicp writes files asynchronously, so need to retry file read
    # in case file not completed and still locked
    nexus_file = "C:/data/{instrument}{run}.nxs".format(instrument=instrument, run=run_number)
    num_of_tries = 5
    sleep_between_file_checks = 5
    for i in range(num_of_tries):
        try:
            with h5py.File(nexus_file, "r") as f:
                test_func(f)
        except IOError:
            if i == num_of_tries - 1:
                print("{} not found, giving up".format(nexus_file))
                raise
            else:
                print("{} not found, retrying".format(nexus_file))
                sleep(sleep_between_file_checks)
        except KeyError as e:
            if i == num_of_tries - 1:
                print("{} found but {} occurred, giving up".format(nexus_file, e))
                raise
            else:
                print("{} found but {} occurred, retrying".format(nexus_file, e))
                sleep(sleep_between_file_checks)


class TestDae(unittest.TestCase):
    """
    Tests to test the DAE commands.
    """

    TIMEOUT = 300

    def setUp(self):
        g.set_instrument(None)
        self._adjust_icp_begin_delay(0)

        # all tests that interact with anything but genie should try to load a config to ensure that the configurations
        # in the tests are not broken, e.g. by a schema update
        load_config_if_not_already_loaded("empty_for_system_tests")

        setup_simulated_wiring_tables()

    def tearDown(self):
        set_genie_python_raises_exceptions(False)

    def fail_if_not_in_setup(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")

    def test_GIVEN_run_state_is_running_WHEN_attempt_to_change_simulation_mode_THEN_error(self):
        set_genie_python_raises_exceptions(True)
        g.begin()
        for _ in range(self.TIMEOUT):
            if g.get_runstate() == "RUNNING":
                break
        else:
            self.fail("Could not start run")

        with self.assertRaises(ValueError):
            g.set_dae_simulation_mode(False)

    def test_GIVEN_run_state_is_setup_WHEN_attempt_to_change_simulation_mode_THEN_simulation_mode_changes(self):
        self.fail_if_not_in_setup()

        g.set_dae_simulation_mode(False)
        _wait_for_and_assert_dae_simulation_mode(False)

        g.set_dae_simulation_mode(True, skip_required_runstates=True)
        _wait_for_and_assert_dae_simulation_mode(True)

    def test_GIVEN_running_instrument_WHEN_pars_changed_THEN_pars_saved_in_file(self):
        self.fail_if_not_in_setup()

        set_genie_python_raises_exceptions(True)
        g.begin()
        title = "title{}".format(random.randint(1, 1000))
        geometry = "geometry{}".format(random.randint(1, 1000))
        width = float(random.randint(1, 1000))
        height = float(random.randint(1, 1000))
        l1 = float(random.randint(1, 1000))
        beamstop = random.choice(['OUT','IN'])
        filename = "{}\\test{}.nxs".format(os.getenv("TEMP"),random.randint(1, 1000))
        self._wait_for_sample_pars()
        g.change_title(title)
        g.change_sample_par("width", width)
        g.change_sample_par("height", height)
        g.change_sample_par("geometry", geometry)
        g.change_beamline_par("l1", l1)
        g.change_beamline_par("beamstop:pos", beamstop)
        sleep(5)
        g.snapshot_crpt(filename)
        sleep(5)
        with h5py.File(filename,  "r") as f:
            saved_title = f['/raw_data_1/title'][0].decode()
            saved_width = f['/raw_data_1/sample/width'][0]
            saved_height = f['/raw_data_1/sample/height'][0]
            saved_geometry = f['/raw_data_1/sample/shape'][0].decode()
            saved_l1 = -f['/raw_data_1/instrument/moderator/distance'][0]
            saved_beamstop = f['/raw_data_1/isis_vms_compat/IVPB'][30]
        os.remove(filename)
        self.assertEqual(title, saved_title)
        self.assertEqual(width, saved_width)
        self.assertEqual(height, saved_height)
        self.assertEqual(geometry, saved_geometry)
        self.assertEqual(l1, saved_l1)
        if beamstop == 'OUT':
            self.assertEqual(1, saved_beamstop)
        else:
            self.assertEqual(0, saved_beamstop)

    def test_GIVEN_running_instrument_WHEN_block_logging_THEN_block_saved_in_file(self):
        load_config_if_not_already_loaded("rcptt_simple")
        self.fail_if_not_in_setup()

        set_genie_python_raises_exceptions(True)
        test_block_name = "FLOAT_BLOCK"
        test_values = [10, 5, 1]
        sleep_between_sets = 5

        g.begin()
        sleep(sleep_between_sets)
        for value in test_values:
            g.cset(test_block_name, value)
            sleep(sleep_between_sets)

        # Restarting the IOC will make it invalid
        stop_ioc("SIMPLE")
        start_ioc("SIMPLE")
        wait_for_ioc_start_stop(30, True, "SIMPLE")

        # Wait for alarm
        for _ in range(5):
            in_alarm = g.cget(test_block_name)["alarm"] == "INVALID"
            if in_alarm:
                break
            sleep(1)
        self.assertTrue(in_alarm, "Block never went invalid when IOC stopped")

        # blocks are on a 5 second flush write from archive
        sleep(15)

        run_number = g.get_runnumber()
        g.end()

        g.waitfor_runstate("SETUP", maxwaitsecs=self.TIMEOUT)

        nexus_path = r'/raw_data_1/selog/{}/value_log'.format(test_block_name)

        def test_function(f):
            is_valid = [sample == 1 for sample in f[nexus_path + r'/value_valid'][:]]
            values = [int(val) for val in f[nexus_path + r'/value'][:]]
            alarm_severity = [str(sample[0], 'utf-8').strip() for sample in f[nexus_path + r'/alarm_severity'][:]]
            alarm_status = [str(sample[0], 'utf-8').strip() for sample in f[nexus_path + r'/alarm_status'][:]]
            alarm_time = [int(time) for time in f[nexus_path + r'/alarm_time'][:]]

            # There could be some samples at the beginning/end but we only care about the ones we've set
            first_value_index = values.index(test_values[0])

            # Only care about test values and the final invalid one
            is_valid = is_valid[first_value_index:first_value_index + len(test_values) + 1]
            values = values[first_value_index:first_value_index + len(test_values) + 1]

            # find first occurrence of NONE after the start of the run, which is start of our values
            first_positive_alarm_timestamp = next(k for k, val in enumerate(alarm_time) if val > 0)
            first_alarm_index = alarm_severity.index("NONE", first_positive_alarm_timestamp)
            final_alarm_index = first_alarm_index + len(test_values) + 1
            alarm_severity = alarm_severity[first_alarm_index:final_alarm_index]
            alarm_status = alarm_status[first_alarm_index:final_alarm_index]
            alarm_time = alarm_time[first_alarm_index:final_alarm_index]

            self.assertTrue(len(is_valid) == len(test_values) + 1, "Not enough values/value_valid items logged to file")
            self.assertTrue(len(alarm_severity) == len(test_values) + 1, "Not enough alarm status/severity items logged to file")

            self.assertListEqual(is_valid, [True, True, True, False])
            # [0] is the value logged by ISISICP when SIMPLE IOC is restarted above
            self.assertListEqual(values, test_values + [0])
            self.assertListEqual(alarm_severity, ["NONE", "MINOR", "MAJOR", "INVALID"])
            self.assertListEqual(alarm_status, ["NO_ALARM", "LOW_ALARM", "LOLO_ALARM", "UDF_ALARM"])

            self.assertAlmostEqual(alarm_time[1] - alarm_time[0], sleep_between_sets, delta=1)
            self.assertAlmostEqual(alarm_time[2] - alarm_time[1], sleep_between_sets, delta=1)

        nexus_file_with_retry(g.adv.get_instrument(), run_number, test_function)

    @contextmanager
    def _assert_title_correct(self, test_title, expected_title):
        """
        Sets the title to test title, performs a run (yielding during the run)
        and confirms that the saved title is expected_title.
        """
        self._wait_for_sample_pars()
        g.change_title(test_title)
        set_genie_python_raises_exceptions(True)
        g.begin()
        try:
            yield
        finally:
            runnumber = g.get_runnumber()
            inst = g.adv.get_instrument()
            g.end()

            g.waitfor_runstate("SETUP", maxwaitsecs=self.TIMEOUT)

            def test_func(f):
                saved_title = f['/raw_data_1/title'][0].decode()
                self.assertEqual(expected_title, saved_title)

            nexus_file_with_retry(inst, runnumber, test_func)

    def test_GIVEN_run_with_block_in_title_WHEN_run_finished_THEN_run_title_has_value_of_block_in_it(self):
        # This is done in one go rather than as a parameterized list as each test needs to quite a long wait
        self.fail_if_not_in_setup()
        load_config_if_not_already_loaded("block_in_title")

        test_blocks = [("FLOAT_BLOCK", 12.345, 12.345),
                       ("LONG_BLOCK", 512, 512),
                       ("STRING_BLOCK", "Test string", "Test string"),

                       # BI/MBBI can only save integer representation to title
                       ("BI_BLOCK", "YES", 1),
                       ("MBBI_BLOCK", "CHEERFUL", 2)]

        test_title = "Test block value " + ("{} and " * len(test_blocks))
        formatted_block_names = [BLOCK_FORMAT_PATTERN.format(block_name=block[0]) for block in test_blocks]
        title = test_title.format(*formatted_block_names)

        expected_title = test_title.format(*[block[2] for block in test_blocks])

        with self._assert_title_correct(title, expected_title):
            [g.cset(block[0], block[1], wait=True) for block in test_blocks]
            sleep(10)

    def test_GIVEN_run_with_multiple_blocks_in_title_WHEN_run_finished_THEN_title_has_all_block_values_in_it(self):
        self.fail_if_not_in_setup()
        load_config_if_not_already_loaded("block_in_title")

        test_title = "Run with two blocks in {block1} and {block2}"

        float_test_val = 12.345
        long_test_val = 512

        formatted_block_name_1 = BLOCK_FORMAT_PATTERN.format(block_name="FLOAT_BLOCK")
        formatted_block_name_2 = BLOCK_FORMAT_PATTERN.format(block_name="LONG_BLOCK")

        title = test_title.format(block1=formatted_block_name_1, block2=formatted_block_name_2)

        with self._assert_title_correct(title, test_title.format(block1=float_test_val, block2=long_test_val)):
            g.cset("FLOAT_BLOCK", float_test_val, wait=True)
            g.cset("LONG_BLOCK", long_test_val, wait=True)
            sleep(10)

    def test_GIVEN_wait_for_complete_callback_dae_settings_is_false_and_valid_tables_given_THEN_dae_does_not_wait_and_xml_values_are_not_initially_correct(self):
        set_wait_for_complete_callback_dae_settings(False)
        set_genie_python_raises_exceptions(True)

        table_path_template = r"{}\tables\{}"
        wiring = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format(os.environ["ICPCONFIGROOT"], "det_corr_184_process_5.dat")
        spectra = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_spectra_doors_all_process_2to1_5.dat")

        with self.assertRaises(ValueError):
            g.change_tables(wiring, detector, spectra)

        set_genie_python_raises_exceptions(False)

    def test_GIVEN_wait_for_complete_callback_dae_settings_is_true_and_valid_tables_given_THEN_dae_waits_and_xml_values_are_confirmed_correct(self):
        set_wait_for_complete_callback_dae_settings(True)
        set_genie_python_raises_exceptions(True)
        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = r"{}\tables\{}"
        wiring = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format(os.environ["ICPCONFIGROOT"], "det_corr_184_process_5.dat")
        spectra = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_spectra_doors_all_process_2to1_5.dat")
        g.change_tables(wiring, detector, spectra)

        set_genie_python_raises_exceptions(False)

    def test_GIVEN_valid_tables_to_change_tables_THEN_get_tables_returns_correct_tables(self):
        set_wait_for_complete_callback_dae_settings(True)
        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = r"{}/tables/{}"
        wiring = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format(os.environ["ICPCONFIGROOT"], "det_corr_184_process_5.dat")
        spectra = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_spectra_doors_all_process_2to1_5.dat")

        g.change_tables(
            wiring=wiring,
            detector=detector,
            spectra=spectra
        )

        self.assertEqual(g.get_detector_table().lower(), detector.lower())
        self.assertEqual(g.get_wiring_table().lower(), wiring.lower())
        self.assertEqual(g.get_spectra_table().lower(), spectra.lower())

    def test_GIVEN_valid_tables_to_change_tables_but_ISISDAE_killed_THEN_get_tables_raises_exception(self):
        set_wait_for_complete_callback_dae_settings(True)
        set_genie_python_raises_exceptions(True)
        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = r"{}\tables\{}"
        wiring = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format(os.environ["ICPCONFIGROOT"], "det_corr_184_process_5.dat")
        spectra = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_spectra_doors_all_process_2to1_5.dat")

        g.change_tables(
            wiring=wiring,
            detector=detector,
            spectra=spectra
        )

        with temporarily_kill_icp():
            self.assertRaises(Exception, g.get_detector_table)
            self.assertRaises(Exception, g.get_spectra_table)
            self.assertRaises(Exception, g.get_wiring_table)

        set_genie_python_raises_exceptions(False)

    def test_WHEN_change_tables_is_called_with_invalid_file_path_THEN_exception_thrown(self):
        set_genie_python_raises_exceptions(True)
        self.assertRaises(Exception, g.change_tables, r"C:\Nonsense\Wibble\Wobble\jelly.txt")
        set_genie_python_raises_exceptions(False)


    def test_GIVEN_change_tables_called_WHEN_existing_filenames_provided_not_absolute_paths_THEN_files_found_and_tables_set(self):
        set_wait_for_complete_callback_dae_settings(True)
        set_genie_python_raises_exceptions(True)
        g.change_tcb(0, 10000, 100, regime=2)

        wiring = r"f_wiring_doors_all_event_process_5.dat"
        detector = r"det_corr_184_process_5.dat"
        spectra = r"f_spectra_doors_all_process_2to1_5.dat"

        g.change_tables(
            wiring=wiring,
            detector=detector,
            spectra=spectra
        )

        self.assertEqual(g.get_detector_table().lower(), r"{}/tables/{}".format(os.environ["ICPCONFIGROOT"], detector).lower())
        self.assertEqual(g.get_wiring_table().lower(), r"{}/tables/{}".format(os.environ["ICPCONFIGROOT"], wiring).lower())
        self.assertEqual(g.get_spectra_table().lower(), r"{}/tables/{}".format(os.environ["ICPCONFIGROOT"], spectra).lower())

        set_genie_python_raises_exceptions(False)

    def test_GIVEN_change_tables_called_WHEN_nonexisting_filenames_provided_not_absolute_paths_THEN_files_found_and_tables_set(self):
        set_wait_for_complete_callback_dae_settings(True)
        set_genie_python_raises_exceptions(True)
        g.change_tcb(0, 10000, 100, regime=2)

        wiring = r"f_wiring_doors_all_process_5.dat"
        detector = r"det_corr_184_5.dat"
        spectra = r"f_spectra_doors_all_2to1_5.dat"

        with self.assertRaises(Exception):
            g.change_tables(
                wiring=wiring,
                detector=detector,
                spectra=spectra
            )

        set_genie_python_raises_exceptions(False)

    def test_GIVEN_change_tables_called_WHEN_filenames_are_not_raw_strings_THEN_filepath_is_accepted(self):
        set_wait_for_complete_callback_dae_settings(True)
        set_genie_python_raises_exceptions(True)
        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = r"{}\tables\{}"
        wiring = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format(os.environ["ICPCONFIGROOT"], "det_corr_184_process_5.dat")
        spectra = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_spectra_doors_all_process_2to1_5.dat")

        g.change_tables(
            wiring=wiring,
            detector=detector,
            spectra=spectra
        )

    def test_GIVEN_change_tables_called_WHEN_filenames_are_not_raw_strings_and_with_forward_slashes_THEN_filepath_is_accepted(self):
        set_wait_for_complete_callback_dae_settings(True)
        set_genie_python_raises_exceptions(True)
        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = "{}/tables/{}"
        wiring = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format(os.environ["ICPCONFIGROOT"], "det_corr_184_process_5.dat")
        spectra = table_path_template.format(os.environ["ICPCONFIGROOT"], "f_spectra_doors_all_process_2to1_5.dat")

        g.change_tables(
            wiring=wiring,
            detector=detector,
            spectra=spectra
        )

    def test_GIVEN_change_number_soft_periods_called_WHEN_new_value_normal_THEN_change_successful(self):
        set_genie_python_raises_exceptions(True)

        g.change_number_soft_periods(30)
        self._wait_for_dae_period_change(30, g.get_number_periods)

        set_genie_python_raises_exceptions(False)

    def test_GIVEN_change_number_soft_periods_called_WHEN_new_value_too_big_for_DAE_hardware_THEN_raise_exception_to_console(self):
        set_genie_python_raises_exceptions(True)

        g.change_number_soft_periods(30)
        self._wait_for_dae_period_change(30, g.get_number_periods)

        self.assertRaises(IOError, g.change_number_soft_periods, EXTREMELY_LARGE_NO_OF_PERIODS)
        self._wait_for_dae_period_change(30, g.get_number_periods)

        set_genie_python_raises_exceptions(False)

    @parameterized.expand(parameterized_list([1, 2, 6, 9, 10]))
    def test_GIVEN_change_period_called_WHEN_valid_argument_THEN_change_successful(self, _, new_period):
        set_genie_python_raises_exceptions(True)
        g.change_number_soft_periods(10)
        self._wait_for_dae_period_change(10, g.get_number_periods)

        g.change_period(new_period)
        self._wait_for_dae_period_change(new_period, g.get_period)

        set_genie_python_raises_exceptions(False)

    @parameterized.expand(parameterized_list([-1, 0, 11, 12]))
    def test_GIVEN_change_period_called_WHEN_invalid_argument_THEN_raise_exception_to_console(self, _, new_period):
        set_genie_python_raises_exceptions(True)
        g.change_number_soft_periods(10)
        self._wait_for_dae_period_change(10, g.get_number_periods)

        g.change_period(1)
        self._wait_for_dae_period_change(1, g.get_period)

        self.assertRaises(IOError, g.change_period, new_period)
        self._wait_for_dae_period_change(1, g.get_period)

        set_genie_python_raises_exceptions(False)

    def _adjust_icp_begin_delay(self, delay_seconds):

        icp_properties_files = [
            r"C:\Labview modules\dae\isisicp.properties",
            r"C:\Instrument\Apps\EPICS\ICP_Binaries\isisicp.properties",
        ]

        begindelay_property = "isisicp.begindelay"
        config_line = "{} = {}\r\n".format(begindelay_property, delay_seconds)
        if g.get_runstate() != "SETUP":
            g.abort() # make sure not left in a funny state from e.g. previous aborted test
        with temporarily_kill_icp():
            config_found = False

            for filepath in icp_properties_files:
                if os.path.exists(filepath):
                    config_found = True
                    with open(filepath) as f:
                        lines = f.readlines()

                    for index, line in enumerate(lines):
                        if begindelay_property in line:
                            lines[index] = config_line
                            break
                    else:
                        lines.append(config_line)

                    with open(filepath, "w") as f:
                        f.writelines(lines)

            if not config_found:
                raise IOError("Could not find at least one icp config file (looked in {})".format(icp_properties_files))

        # Give time for ICP to restart
        time.sleep(15)
        g.waitfor_runstate("SETUP")

    def test_GIVEN_begin_in_progress_WHEN_runcontrol_changes_quickly_in_and_out_of_range_THEN_correct_state_is_eventually_used(self):

        load_config_if_not_already_loaded("rcptt_simple")

        # needs to be long enough so the various cset() commands below can exectute prior to begin completion
        # the test is to move in and out of range multiple times during the begin and get the correct final state
        # it needs to be several times as we widh to test both asyn queueing and any channel access RPRO
        self._adjust_icp_begin_delay(15)

        low_limit = 0
        high_limit = 2

        in_range = (low_limit + high_limit) / 2
        out_of_range = high_limit + 1

        try:
            g.cset("FLOAT_BLOCK", in_range)
            g.cset("FLOAT_BLOCK", lowlimit=low_limit, highlimit=high_limit, runcontrol=True)

            number_of_attempts = 100

            for attempt in range(number_of_attempts):
                print("runcontrol race condition check1 attempt {} / {}".format(attempt + 1, number_of_attempts))

                # Start with block out of range
                g.cset("FLOAT_BLOCK", out_of_range, wait=True)
                time.sleep(2)

                # Use a low-level begin directly as g.begin() would wait for the begin to complete, making the test meaningless
                # we should begin in a waiting state due to above out of range
                g.set_pv("DAE:BEGINRUNEX", 0, wait=False, is_local=True)
                time.sleep(1)

                # now queue various in and out of range movements
                g.cset("FLOAT_BLOCK", in_range, wait=False)
                time.sleep(2)

                g.cset("FLOAT_BLOCK", out_of_range, wait=False)
                time.sleep(2)

                g.cset("FLOAT_BLOCK", in_range, wait=False)
                time.sleep(2)

                g.cset("FLOAT_BLOCK", out_of_range, wait=False)
                time.sleep(2)

                g.cset("FLOAT_BLOCK", in_range, wait=False)
                time.sleep(2)

                # check we are running
                g.waitfor_runstate("RUNNING", maxwaitsecs=30)
                time.sleep(5)

                # check we are still running
                g.waitfor_runstate("RUNNING", maxwaitsecs=30)

                if g.get_runstate() != "RUNNING":
                    self.fail("Should be in RUNNING")

                g.abort()
                g.waitfor_runstate("SETUP")
        finally:
            self._adjust_icp_begin_delay(0)

    def _wait_for_sample_pars(self):
        for _ in range(self.TIMEOUT):
            try:
                g.get_sample_pars()
                return
            except Exception:
                sleep(1)
        self.fail("sample pars did not return")

    def _wait_for_dae_period_change(self, expected_value, get_function):
        """
        Checks if the value returned by the given function is th same as the expected values. If not, it tries again
        after a couple seconds anf repeats the process up to a number of times equal to the DAE_PERIOD_TIMEOUT_SECONDS
        constant of this module. This method is meant to be used for checking the result of changing the number of period
        or the period. Therefore, the function is meant to be either g.get_period() or g.get_number_periods. This method is
        needed since those functions do not return the new values immediately after they are changed, so for the tests
        to pass we need to wait a bit.

        Args:
        expected_value (int): the expected value returned by the function
        get_function (() -> int): the function for which we check that it will return a certain value.
        """
        for _ in range(DAE_PERIOD_TIMEOUT_SECONDS):
            current_value = get_function()

            if current_value == expected_value:
                return expected_value
            else:
                sleep(1)
        self.fail("dae period or number of periods read timed out")


    def test_GIVEN_x_seconds_have_elapsed_since_start_WHEN_getting_time_since_start_without_pause_THEN_seconds_returned_is_correct(self):
        """
        Checks if the seconds elapsed since the start is the same as the expected elapsed seconds.
        :return:
        """
        # Arrange
        expected = 5
        g.begin()
        sleep(expected)

        # Act

        actual = g.get_time_since_start()

        # Assert
        self.assertEqual(expected, actual)

    def test_GIVEN_x_seconds_have_elapsed_since_start_WHEN_getting_time_since_start_with_pause_THEN_seconds_returned_is_correct(self):
        """
        Checks if the seconds elapsed since the start, including paused time period, is the same as the expected elapsed second with the pause.
        :return:
        """
        # Arrange
        sleep_time = 5
        expected = sleep_time*3

        g.begin()
        sleep(sleep_time)
        g.pause()
        sleep(sleep_time)
        g.resume()
        sleep(sleep_time)
        g.end()

        # Act
        actual = g.get_time_since_start()

        # Assert
        self.assertEqual(expected, actual)

    def test_GIVEN_time_have_elapsed_since_start_WHEN_getting_time_since_start_with_pause_THEN_datetime_returned_is_correct(self):
        """
        Checks if the time elapsed since the start is the same as the expected elapsed time. Time is returned in optional choice, as a datetime object.
        :return:
        """
        # Arrange
        sleep_time = 5

        # Adding time it took since start to the current datetime
        expected = (sleep_time*3) + datetime.utcnow()

        g.begin()
        sleep(sleep_time)
        g.pause()
        sleep(sleep_time)
        g.resume()
        sleep(sleep_time)
        g.end()

        # Act
        actual = g.get_time_since_start(True)
        #Assert
        self.assertEqual(expected,actual)









