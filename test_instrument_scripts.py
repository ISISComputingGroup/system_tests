import unittest
import os, sys

from utilities import utilities
from genie_python import genie as g

sys.path.append(os.path.join("C:\\", "Instrument", "scripts"))


def assert_tables(cls : unittest.TestCase, detector : str, wiring : str, spectra : str) -> None:
    """
    Utility function for asserting that all of the tables are correct.
    
    Args:
        cls (unittest.TestCase): test class instance
        detector (str): detector table file name
        wiring (str): wiring table file name
        spectra (str): spectra table file name
    """
    cls.assertIn(detector, g.get_detector_table())
    cls.assertIn(wiring, g.get_wiring_table())
    cls.assertIn(spectra, g.get_spectra_table())


# Tests for the scanning instrument scripts. They are mainly testing
# the do_sans and do_trans methods and each of their parameters. For
# each instrument we are testing that it can go into sans mode, trans
# mode and switch between them. Testing each parameter is spread
# out over each instrument depending on what the simulation allows.

# All the tables for this are copies of _ibextest.dat renamed for
# the tables needed in the script.

# Test Sans2d more thorougher than other instruments as it is best
# simulated and functionality tested does not need repeated per
# instrument
class TestInstrumentScriptsSans2d(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        g.set_instrument(None)
        utilities.load_config_if_not_already_loaded("instrument_scripts_sans2d")

        from instrument.sans2d.sans import Sans2d
        cls.instr = Sans2d()

        g.set_pv("CAEN:hv0:1:SIM", 1, is_local=True)
        for i in range(10):
            g.set_pv(f"CAEN:hv0:1:SIM:{i}:status", "On", is_local=True)

        g.set_pv("MOT:SAMP:X:MTR.VMAX", 15, is_local=True)
        g.set_pv("MOT:SAMP:X:MTR.VELO", 15, is_local=True)
        g.set_pv("MOT:SAMP:Y:MTR.VMAX", 15, is_local=True)
        g.set_pv("MOT:SAMP:Y:MTR.VELO", 15, is_local=True)

    def test_WHEN_do_sans_is_called_instrument_is_in_sans_mode(self):
        self.instr.do_sans()
        utilities.assert_with_timeout(lambda: self.assertEqual("OUT", g.get_pv("FINS_VAC:MONITOR3:STATUS:SP", is_local=True)), timeout=30)
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector_gastubes_01.dat", "wiring_gastubes_01_event.dat", "spectrum_gastubes_01.dat")

    def test_WHEN_do_trans_is_called_instrument_is_in_trans_mode(self):
        self.instr.do_trans()
        utilities.assert_with_timeout(lambda: self.assertEqual("IN", g.get_pv("FINS_VAC:MONITOR3:STATUS:SP", is_local=True)), timeout=30)
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector_trans8.dat", "wiring_trans8.dat", "spectra_trans8.dat")

    def test_WHEN_after_calling_do_trans_calling_do_sans_puts_instrument_is_in_sans_mode(self):
        self.instr.do_trans()

        self.instr.do_sans()
        utilities.assert_with_timeout(lambda: self.assertEqual("OUT", g.get_pv("FINS_VAC:MONITOR3:STATUS:SP", is_local=True)), timeout=30)
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector_gastubes_01.dat", "wiring_gastubes_01_event.dat", "spectrum_gastubes_01.dat")

    def test_WHEN_after_calling_do_sans_calling_do_trans_puts_instrument_is_in_trans_mode(self):
        self.instr.do_sans()

        self.instr.do_trans()
        utilities.assert_with_timeout(lambda: self.assertEqual("IN", g.get_pv("FINS_VAC:MONITOR3:STATUS:SP", is_local=True)), timeout=30)
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector_trans8.dat", "wiring_trans8.dat", "spectra_trans8.dat")

    def test_WHEN_do_sans_large_is_called_instrument_is_in_sans_mode_with_correct_aperture(self):
        self.instr.do_sans_large()
        utilities.assert_with_timeout(lambda: self.assertEqual("OUT", g.get_pv("FINS_VAC:MONITOR3:STATUS:SP", is_local=True)), timeout=30)
        self.assertEqual("sans", self.instr.measurement_type)
        utilities.assert_with_timeout(lambda: self.assertEqual("LARGE", g.get_pv("LKUP:SCRAPER:POSN:SP", is_local=True)), timeout=30)
        assert_tables(self, "detector_gastubes_01.dat", "wiring_gastubes_01_event.dat", "spectrum_gastubes_01.dat")

    def test_WHEN_calling_do_sans_trans_with_all_valid_time_parameters_THEN_run_starts(self):
        initial_run_num = g.get_runnumber()
        self.instr.do_sans(title="TEST_RUN", time=10)
        g.waitfor_runstate("SETUP", maxwaitsecs=30)
        self.assertEqual(g.get_runstate(), "SETUP")
        self.assertEqual(int(initial_run_num) + 1, int(g.get_runnumber()))

        self.instr.do_sans(title="TEST_RUN", seconds=10)
        g.waitfor_runstate("SETUP", maxwaitsecs=30)
        self.assertEqual(g.get_runstate(), "SETUP")
        self.assertEqual(int(initial_run_num) + 2, int(g.get_runnumber()))

        self.instr.do_trans(title="TEST_RUN", uamps=1)
        g.waitfor_runstate("SETUP", maxwaitsecs=30)
        self.assertEqual(g.get_runstate(), "SETUP")
        self.assertEqual(int(initial_run_num) + 3, int(g.get_runnumber()))

    def test_WHEN_calling_do_sans_do_trans_sets_title_correctly(self):
        self.instr.do_sans(title="SANS_TEST")
        utilities.assert_with_timeout(lambda: self.assertEqual(g.get_title(), "SANS_TEST_SANS"), timeout=30)
        self.instr.do_trans(title="TRANS_TEST")
        utilities.assert_with_timeout(lambda: self.assertEqual(g.get_title(), "TRANS_TEST_TRANS"), timeout=30)

    def test_WHEN_calling_do_sans_with_position_sets_position_correctly(self):
        self.instr.do_sans(position="BT")
        utilities.assert_with_timeout(lambda: self.assertEqual(self.instr.changer_pos, "BT"), timeout=30)

        with self.assertRaises(RuntimeError):
            self.instr.do_sans(position="BAD_POSITION")
        utilities.assert_with_timeout(lambda: self.assertEqual(self.instr.changer_pos, "BT"), timeout=30)

    def test_WHEN_calling_do_sans_with_thickness_set_thickness_correctly(self):
        self.instr.do_sans(thickness=2.0)
        self.assertEqual(2.0, g.get_sample_pars()['THICK'])

    def test_WHEN_calling_do_sans_with_dls_sample_changer_sets_position_correctly(self):
        self.instr.do_sans(position="DLS2", dls_sample_changer=True)
        utilities.assert_with_timeout(lambda: self.assertEqual(self.instr.changer_pos_dls, "DLS2"), timeout=30)
        with self.assertRaises(RuntimeError):
            self.instr.do_sans(position="BAD_POSITION", dls_sample_changer=True)
        utilities.assert_with_timeout(lambda: self.assertEqual(self.instr.changer_pos_dls, "DLS2"), timeout=30)

    def test_WHEN_do_sans_with_aperture_sets_aperture_correctly(self):
        self.instr.do_sans(aperture="LARGE")
        utilities.assert_with_timeout(lambda: self.assertEqual(g.get_pv("LKUP:SCRAPER:POSN:SP", is_local=True).upper(), "LARGE"), timeout=30)

    def test_WHEN_do_sans_with_period_sets_period_correctly(self):
        self.instr.do_sans(period=1)
        self.assertEqual(1, g.get_period())


# Test zoom but don't need to test parts of the instrument base class done in sans2d
class TestInstrumentScriptsZOOM(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        g.set_instrument(None)
        utilities.load_config_if_not_already_loaded("instrument_scripts_zoom")

        from instrument.zoom.sans import Zoom
        cls.instr = Zoom()

        g.set_pv("CAEN:hv0:4:SIM", 1, is_local=True)
        for i in range(8):
            g.set_pv(f"CAEN:hv0:4:SIM:{i}:status", "On", is_local=True)

    def test_WHEN_do_sans_is_called_instrument_is_in_sans_mode(self):
        self.instr.do_sans()
        utilities.assert_with_timeout(lambda: self.assertEqual("EXTRACTED", g.get_pv("VACUUM:MONITOR:4:SP", is_local=True)), timeout=30)
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector_1det_1dae3card.dat", "wiring1det_event_200218.dat", "spec2det_280318_to_test_18_1.txt")

    def test_WHEN_do_trans_is_called_instrument_is_in_trans_mode(self):
        self.instr.do_trans()
        utilities.assert_with_timeout(lambda: self.assertEqual("INSERTED", g.get_pv("VACUUM:MONITOR:4:SP", is_local=True)), timeout=30)
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector_8mon_1dae3card_00.dat", "wiring_8mon_1dae3card_00_hist.dat", "spectrum_8mon_1dae3card_00.dat")

    def test_WHEN_after_calling_do_trans_calling_do_sans_puts_instrument_is_in_sans_mode(self):
        self.instr.do_trans()

        self.instr.do_sans()
        utilities.assert_with_timeout(lambda: self.assertEqual("EXTRACTED", g.get_pv("VACUUM:MONITOR:4:SP", is_local=True)), timeout=30)
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector_1det_1dae3card.dat", "wiring1det_event_200218.dat", "spec2det_280318_to_test_18_1.txt")

    def test_WHEN_after_calling_do_sans_calling_do_trans_puts_instrument_is_in_trans_mode(self):
        self.instr.do_sans()

        self.instr.do_trans()
        utilities.assert_with_timeout(lambda: self.assertEqual("INSERTED", g.get_pv("VACUUM:MONITOR:4:SP", is_local=True)), timeout=30)
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector_8mon_1dae3card_00.dat", "wiring_8mon_1dae3card_00_hist.dat", "spectrum_8mon_1dae3card_00.dat")

    def test_WHEN_calling_do_sans_with_custom_daes_THEN_daes_are_set_correctly(self):
        self.instr.do_sans(dae="histogram")
        assert_tables(self, "detector_1det_1dae3card.dat", "wiring1det_histogram_200218.dat", "spec2det_130218.txt")

        self.instr.do_trans()
        self.instr.do_sans()
        assert_tables(self, "detector_1det_1dae3card.dat", "wiring1det_histogram_200218.dat", "spec2det_130218.txt")

        self.instr.set_default_dae(mode="event")
        self.instr.do_sans()
        assert_tables(self, "detector_1det_1dae3card.dat", "wiring1det_event_200218.dat", "spec2det_280318_to_test_18_1.txt")


class TestInstrumentScriptsLOQ(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        g.set_instrument(None)
        utilities.load_config_if_not_already_loaded("instrument_scripts_loq")

        from instrument.loq.sans import LOQ
        cls.instr = LOQ()

        cls.instr.detector_lock(True)

        g.set_pv("MOT:MTR0104.VMAX", 5, is_local=True)
        g.set_pv("MOT:MTR0104.VELO", 5, is_local=True)

    def test_WHEN_do_sans_is_called_instrument_is_in_sans_mode(self):
        # No recsim for loq detector
        self.instr.detector_lock(True)
        self.instr.do_sans()
        self.assertEqual("OUT", g.cget("Tx_Mon")["value"])
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector35576_M4.dat", "wiring35576_M4.dat", "spectra35576_M4.dat")

    def test_WHEN_do_trans_is_called_instrument_is_in_trans_mode(self):
        self.instr.detector_lock(True)
        self.instr.do_trans()
        self.assertEqual("IN", g.cget("Tx_Mon")["value"])
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector8.dat", "wiring8.dat", "spectra8.dat")

    def test_WHEN_after_calling_do_trans_calling_do_sans_puts_instrument_is_in_sans_mode(self):
        self.instr.do_trans()

        self.instr.do_sans()
        self.assertEqual("OUT", g.cget("Tx_Mon")["value"])
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector35576_M4.dat", "wiring35576_M4.dat", "spectra35576_M4.dat")

    def test_WHEN_after_calling_do_sans_calling_do_trans_puts_instrument_is_in_trans_mode(self):
        self.instr.do_sans()

        self.instr.do_trans()
        self.assertEqual("IN", g.cget("Tx_Mon")["value"])
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector8.dat", "wiring8.dat", "spectra8.dat")

    def test_WHEN_calling_do_sans_with_a_custom_block_sets_block_correctly(self):
        # Use monitor block in absence of other block
        self.instr.do_sans(Tx_Mon="IN")
        g.waitfor_move(blocks="Tx_Mon")
        self.assertEqual("IN", g.cget("Tx_Mon")["value"])


class TestInstrumentScriptsLarmor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        g.set_instrument(None)
        utilities.load_config_if_not_already_loaded("instrument_scripts_larmor")

        from instrument.larmor.sans import Larmor
        cls.instr = Larmor()

        g.set_pv("CAEN:hv0:0:SIM", 1, is_local=True)
        for i in range(8, 12):
            g.set_pv(f"CAEN:hv0:0:SIM:{i}:status", "On", is_local=True)

        g.set_pv("MOT:MTR0602.VMAX", 5, is_local=True)
        g.set_pv("MOT:MTR0602.VELO", 5, is_local=True)
        g.set_pv("MOT:MTR0507.VMAX", 5, is_local=True)
        g.set_pv("MOT:MTR0507.VELO", 5, is_local=True)

    def test_WHEN_do_sans_is_called_instrument_is_in_sans_mode(self):
        self.instr.do_sans()
        self.assertEqual(200.0, g.cget("m4trans")["value"])
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector.dat", "wiring_dae3_event.dat", "spectra_1To1.dat")

    def test_WHEN_do_trans_is_called_instrument_is_in_trans_mode(self):
        self.instr.do_trans()
        self.assertEqual(0.0, g.cget("m4trans")["value"])
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector_monitors_only.dat", "wiring_dae3_monitors_only.dat", "spectra_monitors_only.dat")

    def test_WHEN_after_calling_do_trans_calling_do_sans_puts_instrument_is_in_sans_mode(self):
        self.instr.do_trans()

        self.instr.do_sans()
        self.assertEqual(200.0, g.cget("m4trans")["value"])
        self.assertEqual("sans", self.instr.measurement_type)
        assert_tables(self, "detector.dat", "wiring_dae3_event.dat", "spectra_1To1.dat")

    def test_WHEN_after_calling_do_sans_calling_do_trans_puts_instrument_is_in_trans_mode(self):
        self.instr.do_sans()

        self.instr.do_trans()
        self.assertEqual(0.0, g.cget("m4trans")["value"])
        self.assertEqual("transmission", self.instr.measurement_type)
        assert_tables(self, "detector_monitors_only.dat", "wiring_dae3_monitors_only.dat", "spectra_monitors_only.dat")
