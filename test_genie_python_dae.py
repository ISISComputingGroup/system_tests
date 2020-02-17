import unittest
from unittest import skip

import h5py
import random
import os
from time import sleep

from utilities.utilities import g, genie_dae, set_genie_python_raises_exceptions, setup_simulated_wiring_tables, \
    set_wait_for_complete_callback_dae_settings, temporarily_kill_icp, \
    load_config_if_not_already_loaded, _wait_for_and_assert_dae_simulation_mode, parameterized_list

from parameterized import parameterized
from contextlib import contextmanager

EXTREMELY_LARGE_NO_OF_PERIODS = 1000000

BLOCK_FORMAT_PATTERN = "@{block_name}@"

class TestDae(unittest.TestCase):
    """
    Tests to test the DAE commands.
    """

    TIMEOUT = 300

    def setUp(self):
        g.set_instrument(None)
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
        filename = "c:/windows/temp/test{}.nxs".format(random.randint(1, 1000))
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
            saved_title = f['/raw_data_1/title'][0]
            saved_width = f['/raw_data_1/sample/width'][0]
            saved_height = f['/raw_data_1/sample/height'][0]
            saved_geometry = f['/raw_data_1/sample/shape'][0]
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
            inst = g.get_instrument()
            g.end()

            g.waitfor_runstate("SETUP", maxwaitsecs=self.TIMEOUT)

            with h5py.File("C:/data/{instrument}{run}.nxs".format(instrument=inst, run=runnumber), "r") as f:
                saved_title = f['/raw_data_1/title'][0]

            self.assertEqual(expected_title, saved_title)

    @parameterized.expand([
        ("FLOAT_BLOCK", 12.345, 12.345),
        ("LONG_BLOCK", 512, 512),
        ("STRING_BLOCK", "Test string", "Test string"),

        # BI/MBBI can only save integer representation to title
        ("BI_BLOCK", "YES", 1),
        ("MBBI_BLOCK", "CHEERFUL", 2)
    ])
    @skip("Skip this test until ticket 4828")
    def test_GIVEN_run_with_block_in_title_WHEN_run_finished_THEN_run_title_has_value_of_block_in_it(self, block_to_test, block_test_value, expected_title_value):
        self.fail_if_not_in_setup()
        load_config_if_not_already_loaded("block_in_title")

        formatted_block_name = BLOCK_FORMAT_PATTERN.format(block_name=block_to_test)

        test_title = "Test block value {block}"

        title = test_title.format(block=formatted_block_name)

        with self._assert_title_correct(title, test_title.format(block=expected_title_value)):
            g.cset(block_to_test, block_test_value, wait=True)

    @skip("Skip this test until ticket 4828")
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

        self.assertEqual(g.get_detector_table(), detector)
        self.assertEqual(g.get_wiring_table(), wiring)
        self.assertEqual(g.get_spectra_table(), spectra)

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

        self.assertEqual(g.get_detector_table(), r"{}/tables/{}".format(os.environ["ICPCONFIGROOT"], detector))
        self.assertEqual(g.get_wiring_table(), r"{}/tables/{}".format(os.environ["ICPCONFIGROOT"], wiring))
        self.assertEqual(g.get_spectra_table(), r"{}/tables/{}".format(os.environ["ICPCONFIGROOT"], spectra))

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

        table_path_template = "{}\tables\{}"
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
        sleep(10)
        self.assertEqual(g.get_number_periods(), 30)

        set_genie_python_raises_exceptions(False)

    def test_GIVEN_change_number_soft_periods_called_WHEN_new_value_too_big_for_DAE_hardware_THEN_raise_exception_to_console(self):
        set_genie_python_raises_exceptions(True)

        g.change_number_soft_periods(30)
        sleep(10)
        self.assertEqual(g.get_number_periods(), 30)

        self.assertRaises(IOError, g.change_number_soft_periods, EXTREMELY_LARGE_NO_OF_PERIODS)
        self.assertEqual(g.get_number_periods(), 30)

        set_genie_python_raises_exceptions(False)

    @parameterized.expand(parameterized_list([1, 2, 6, 9, 10]))
    def test_GIVEN_change_period_called_WHEN_valid_argument_THEN_change_successful(self, _, new_period):
        set_genie_python_raises_exceptions(True)
        g.change_number_soft_periods(10)
        sleep(10)
        self.assertEqual(g.get_number_periods(), 10)

        g.change_period(new_period)
        self.assertEqual(g.get_period(), new_period)

        set_genie_python_raises_exceptions(False)

    @parameterized.expand(parameterized_list([-1, 0, 11, 12]))
    def test_GIVEN_change_period_called_WHEN_invalid_argument_THEN_raise_exception_to_console(self, _, new_period):
        set_genie_python_raises_exceptions(True)
        g.change_number_soft_periods(10)
        sleep(10)
        self.assertEqual(g.get_number_periods(), 10)
        g.change_period(1)
        self.assertEqual(g.get_period(), 1)

        self.assertRaises(IOError, g.change_period, new_period)
        self.assertEqual(g.get_period(), 1)

        set_genie_python_raises_exceptions(False)

    def _wait_for_sample_pars(self):
        for _ in range(self.TIMEOUT):
            try:
                g.get_sample_pars()
                return
            except Exception:
                sleep(1)
        self.fail("sample pars did not return")
