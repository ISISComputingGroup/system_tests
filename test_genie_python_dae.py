import unittest
import h5py
import random
import os
from time import sleep

from utilities.utilities import g, genie_dae, set_genie_python_raises_exceptions, setup_simulated_wiring_tables, \
                            set_wait_for_complete_callback_dae_settings, temporarily_kill_icp, \
                            load_config_if_not_already_loaded, _get_config_name

from parameterized import parameterized

TEST_TITLE = "Test block value {block}"
BLOCK_FORMAT_PATTERN = "@{block_name}@"

class TestDae(unittest.TestCase):
    """
    Tests to test the DAE commands.
    """

    TIMEOUT = 300

    def setUp(self):
        g.set_instrument(None)

        setup_simulated_wiring_tables()

    def tearDown(self):
        set_genie_python_raises_exceptions(False)

    def wait_for_setup_run_state(self):
        for _ in range(self.TIMEOUT):
            if g.get_runstate() == "SETUP":
                return
            sleep(1.0)

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
        self._wait_for_and_assert_dae_simulation_mode(False)

        g.set_dae_simulation_mode(True)
        self._wait_for_and_assert_dae_simulation_mode(True)

    def test_GIVEN_running_instrument_WHEN_pars_changed_THEN_pars_saved_in_file(self):
        self.fail_if_not_in_setup()

        set_genie_python_raises_exceptions(True)
        g.begin()
        title = "title{}".format(random.randint(1,1000))
        geometry = "geometry{}".format(random.randint(1,1000))
        width = float(random.randint(1,1000))
        height = float(random.randint(1,1000))
        l1 = float(random.randint(1,1000))
        beamstop = random.choice(['OUT','IN'])
        filename = "c:/windows/temp/test{}.nxs".format(random.randint(1,1000))
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

    @parameterized.expand([
        ("FLOAT_BLOCK", 12.3),
        ("LONG_BLOCK", 512),
        ("STRING_BLOCK", "Test string")
    ])
    def test_GIVEN_run_with_block_in_title_WHEN_run_finished_THEN_run_title_has_value_of_block_in_it(self, block_to_test, block_test_value):

        formatted_block_name = BLOCK_FORMAT_PATTERN.format(block_name=block_to_test)

        title = TEST_TITLE.format(block=formatted_block_name)

        self.fail_if_not_in_setup()

        load_config_if_not_already_loaded("block_in_title")

        self._wait_for_sample_pars()
        g.change_title(title)

        set_genie_python_raises_exceptions(True)
        g.begin()

        g.cset(block_to_test, block_test_value, wait=True)

        runnumber = g.get_runnumber()
        inst = g.get_instrument()

        g.end()

        self.wait_for_setup_run_state()

        # Obtain saved title from output nexus file
        with h5py.File("C:/data/{instrument}{run}.nxs".format(instrument=inst, run=runnumber), "r") as f:
            saved_title = f['/raw_data_1/title'][0]

        self.assertEqual(TEST_TITLE.format(block=block_test_value), saved_title)

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

    def _wait_for_and_assert_dae_simulation_mode(self, mode):
        for _ in range(self.TIMEOUT):
            if g.get_dae_simulation_mode() == mode:
                return
            sleep(1)
        else:
            self.assertEqual(g.get_dae_simulation_mode(), mode)

    def _wait_for_sample_pars(self):
        for _ in range(self.TIMEOUT):
            try:
                g.get_sample_pars()
                return
            except:
                sleep(1)
        self.assertEqual(0, 1)
