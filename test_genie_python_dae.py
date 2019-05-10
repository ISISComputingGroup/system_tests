import unittest
import h5py
import random
import os
from time import sleep

from utilities.utilities import g, genie_dae, set_genie_python_raises_exceptions, setup_simulated_wiring_tables, \
                            set_wait_for_complete_callback_dae_settings, temporarily_kill_icp


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
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")

        g.set_dae_simulation_mode(False)
        self._wait_for_and_assert_dae_simulation_mode(False)

        g.set_dae_simulation_mode(True)
        self._wait_for_and_assert_dae_simulation_mode(True)

    def test_GIVEN_running_instrument_WHEN_pars_changed_THEN_pars_saved_in_file(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")
        set_genie_python_raises_exceptions(True)
        g.begin()
        title = "title{}".format(random.randint(1,1000))
        geometry = "geometry{}".format(random.randint(1,1000))
        width = float(random.randint(1,1000))
        height = float(random.randint(1,1000))
        l1 = float(random.randint(1,1000))
        beamstop = random.choice(['OUT','IN'])
        filename = "c:/windows/temp/test{}.nxs".format(random.randint(1,1000))
        g.change_title(title)
        g.change_sample_par("width", width)
        g.change_sample_par("height", height)
        g.change_sample_par("geometry", geometry)
        g.change_beamline_par("l1", l1)
        g.change_beamline_par("beamstop:pos", beamstop)
        sleep(5)
        g.snapshot_crpt(filename)
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

    def test_GIVEN_wait_for_complete_callback_dae_settings_is_false_and_valid_tables_given_THEN_dae_does_not_wait_and_xml_values_are_not_initially_correct(self):

        set_wait_for_complete_callback_dae_settings(False)

        table_path_template = r"{}\tables\{}".format(os.environ["ICPCONFIGROOT"], "{}")
        wiring = table_path_template.format("f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format("det_corr_184_process_5.dat")
        spectra = table_path_template.format("f_spectra_doors_all_process_2to1_5.dat")
        self.assertRaises(ValueError, g.change_tables(wiring, detector, spectra))

    def test_GIVEN_wait_for_complete_callback_dae_settings_is_true_and_valid_tables_given_THEN_dae_waits_and_xml_values_are_confirmed_correct(self):

        set_wait_for_complete_callback_dae_settings(True)
        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = r"{}\tables\{}".format(os.environ["ICPCONFIGROOT"], "{}")
        wiring = table_path_template.format("f_wiring_doors_all_event_process_5.dat")
        detector = table_path_template.format("det_corr_184_process_5.dat")
        spectra = table_path_template.format("f_spectra_doors_all_process_2to1_5.dat")
        g.change_tables(wiring, detector, spectra)

    def test_GIVEN_valid_spectra_table_to_change_tables_THEN_get_spectra_table_returns_correct_file_path(self):

        set_wait_for_complete_callback_dae_settings(True)
        g.change_tcb(0, 10000, 100, regime=2)
        spectra = r"{}/tables/RCPTT_{}128.dat".format(os.environ["ICPCONFIGROOT"], "Spectra")

        g.change_tables(
            spectra=spectra
        )

        self.assertEqual(g.get_spectra_table(), spectra)

    def test_GIVEN_valid_wiring_table_to_change_tables_THEN_get_wiring_table_returns_correct_file_path(self):

        set_wait_for_complete_callback_dae_settings(True)
        g.change_tcb(0, 10000, 100, regime=2)
        wiring = r"{}/tables/RCPTT_{}128.dat".format(os.environ["ICPCONFIGROOT"], "Wiring")

        g.change_tables(
            wiring=wiring
        )

        self.assertEqual(g.get_wiring_table(), wiring)

    def test_GIVEN_valid_detector_table_to_change_tables_THEN_get_detector_table_returns_correct_file_path(self):

        set_wait_for_complete_callback_dae_settings(True)
        g.change_tcb(0, 10000, 100, regime=2)
        detector = r"{}/tables/RCPTT_{}128.dat".format(os.environ["ICPCONFIGROOT"], "Detector")

        g.change_tables(
            detector=detector
        )
        self.assertEqual(g.get_detector_table(), detector)


    def test_GIVEN_valid_tables_to_change_tables_but_ISISDAE_killed_THEN_get_tables_raises_exception(self):

        set_wait_for_complete_callback_dae_settings(True)

        g.change_tcb(0, 10000, 100, regime=2)

        table_path_template = r"{}\tables\RCPTT_{}128.dat".format(os.environ["ICPCONFIGROOT"], "{}")
        g.change_tables(
            wiring=table_path_template.format("wiring"),
            detector=table_path_template.format("detector"),
            spectra=table_path_template.format("spectra"))

        with temporarily_kill_icp():
            self.assertRaises(Exception, g.get_detector_table())
            self.assertRaises(Exception, g.get_spectra_table())
            self.assertRaises(Exception, g.get_wiring_table())


    def _wait_for_and_assert_dae_simulation_mode(self, mode):
        for _ in range(self.TIMEOUT):
            if g.get_dae_simulation_mode() == mode:
                return
            sleep(1)
        else:
            self.assertEqual(g.get_dae_simulation_mode(), mode)

