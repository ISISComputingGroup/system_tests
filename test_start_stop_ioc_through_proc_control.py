import unittest
from typing import List

from hamcrest import *

from utilities.utilities import g, as_seconds, start_ioc, stop_ioc, wait_for_ioc_start_stop, \
    load_config_if_not_already_loaded
from six.moves import range

import xml.etree.ElementTree as ET
import os


# The following iocs are ignored in the test which starts/stops all iocs
# This is usually because they don't build by default, or have some complex dependency,
# or are special in some way (e.g. psctrl).
IOCS_TO_IGNORE_START_STOP = [
    "PSCTRL",  # Special, controls other IOCs
    "DELFTDCMAG_01",  # Delft iocs have a weird build/run process?
    "DELFTDCMAG_02",
    'DELFTSHEAR_01',
    'ASTRIUM_01',
    'ASTRIUM_02',
    'BGRSCRPT_01',  # Won't keep running unless it has a config file
    'BGRSCRPT_02',
    'BKHOFF_02',  # Complex build
    'ECLAB_01',
    'LSICORR_01',  # Needs vendor library in correct place to keep running
    'LSICORR_02',
    'MOXA12XX_01',
    'MOXA12XX_02',
    'MOXA12XX_03',
    'MK3CHOPR_01',
    'NANODAC_01',
    'OERCONE_02',
    'REFL_01',  # Won't run correctly without a config
    'TWINCAT_01',
    'MOTORSIM',  # Simulation ioc
    'PIXELMAN',
    'CHOPPERSIM',  # Simulation ioc
]

GLOBALS_FILENAME = os.path.join(os.environ['ICPCONFIGROOT'], "globals.txt")


class TestProcControl(unittest.TestCase):
    """

    """

    def setUp(self):
        g.set_instrument(None)

        # all tests that interact with anything but genie should try to load a config to ensure that the configurations
        # in the tests are not broken, e.g. by a schema update
        load_config_if_not_already_loaded("empty_for_system_tests")

    def test_GIVEN_ioc_is_running_WHEN_call_stop_multiple_times_quickly_THEN_ioc_is_stopped(self):
        # This test is repeated 10 time to ensure a consistent failure before the code update
        for i in range(10):
            start_ioc(ioc_name="SIMPLE")

            for _ in range(5):
                g.set_pv("CS:PS:SIMPLE:STOP", 1, is_local=True, wait=False)

            g.waitfor_time(seconds=5)  # wait just in case it is starting
            wait_for_ioc_start_stop(timeout=5, is_start=False, ioc_name="SIMPLE")

    def test_GIVEN_ioc_is_stopped_WHEN_call_stop_multiple_times_quickly_THEN_ioc_is_stopped(self):
        stop_ioc(ioc_name="SIMPLE")

        for _ in range(20):
            g.set_pv("CS:PS:SIMPLE:STOP", 1, is_local=True, wait=False)

        g.waitfor_time(seconds=5)  # wait just in case it is starting
        wait_for_ioc_start_stop(timeout=30, is_start=False, ioc_name="SIMPLE")

    def test_GIVEN_ioc_is_running_WHEN_call_start_multiple_times_quickly_THEN_ioc_is_started(self):
        start_ioc(ioc_name="SIMPLE")

        for _ in range(20):
            g.set_pv("CS:PS:SIMPLE:START", 1, is_local=True, wait=True)

        g.waitfor_time(seconds=5)  # wait just in case it is starting
        wait_for_ioc_start_stop(timeout=30, is_start=True, ioc_name="SIMPLE")

    def test_GIVEN_ioc_is_stopped_WHEN_call_start_multiple_times_quickly_THEN_ioc_is_started(self):
        stop_ioc(ioc_name="SIMPLE")

        for _ in range(20):
            g.set_pv("CS:PS:SIMPLE:START", 1, is_local=True, wait=True)

        g.waitfor_time(seconds=5)  # wait just in case it is starting
        wait_for_ioc_start_stop(timeout=30, is_start=True, ioc_name="SIMPLE")

    def test_GIVEN_ioc_is_running_WHEN_call_restart_multiple_times_quickly_THEN_ioc_is_restarted(self):
        time_to_restart_and_read_uptime = 10
        start_ioc(ioc_name="SIMPLE")
        while as_seconds(g.get_pv("CS:IOC:SIMPLE:DEVIOS:UPTIME", is_local=True)) < time_to_restart_and_read_uptime:
            g.waitfor_time(seconds=1)
        for _ in range(20):
            g.set_pv("CS:PS:SIMPLE:RESTART", 1, is_local=True, wait=False)

        wait_for_ioc_start_stop(timeout=30, is_start=True, ioc_name="SIMPLE")
        assert_that(as_seconds(g.get_pv("CS:IOC:SIMPLE:DEVIOS:UPTIME", is_local=True)),
                    less_than(time_to_restart_and_read_uptime), "Uptime")

    def test_GIVEN_ioc_is_off_WHEN_call_restart_multiple_times_quickly_THEN_ioc_is_still_stopped(self):

        stop_ioc(ioc_name="SIMPLE")

        for _ in range(20):
            g.set_pv("CS:PS:SIMPLE:RESTART", 1, is_local=True, wait=False)

        wait_for_ioc_start_stop(timeout=30, is_start=False, ioc_name="SIMPLE")

    def test_WHEN_start_iocs_THEN_iocs_started_WHEN_stop_iocs_THEN_iocs_stopped(self):
        
        # temporarily disable
        return
    
        # A test to check all IOCs start and stop correctly
        # Implemented to test for the error we encountered where we met our procserv limit and some iocs didn't start

        tree = ET.parse(os.path.join("C:\\", "Instrument", "Apps", "EPICS", "iocstartup", "config.xml"))
        root = tree.getroot()

        # IOCs are listed in the above XML file under two different schemas, we need both
        schemas = (
            "{http://epics.isis.rl.ac.uk/schema/ioc_config/1.0}",
            "{http://epics.isis.rl.ac.uk/schema/ioc_configs/1.0}"
        )

        iocs = []
        for schema in schemas:
            iocs.extend([ioc_config.attrib["name"] for ioc_config in root.iter(f"{schema}ioc_config")])

        # Check parsed IOCs are a sensible length
        self.assertGreater(len(iocs), 100)
        # Check there's at least one known ioc in the list
        self.assertTrue(any(item in iocs for item in ["SIMPLE", "AMINT2L_01", "EUROTHRM_01", "INSTETC_01"]))

        errored_iocs = []

        for ioc in iocs:
            if any(iocname in ioc for iocname in IOCS_TO_IGNORE_START_STOP):
                print(f"skipping {ioc}")
                continue
            print(f"testing {ioc}")
            # Start/stop ioc also waits for the ioc to start/stop respectively or errors after a 30 second timeout
            try:
                start_ioc(ioc_name=ioc)
                stop_ioc(ioc_name=ioc)
            except IOError:
                self._retry_in_recsim(errored_iocs, ioc)

        self.assertEqual(errored_iocs, [], "IOCs failed: {}".format(errored_iocs))

    @staticmethod
    def _retry_in_recsim(errored_iocs: List[str], ioc: str):
        # open with w flag and overwrite - we don't need to
        with open(GLOBALS_FILENAME, "w") as globals_file:
            globals_file.write(f"{ioc}__RECSIM=1")
            globals_file.flush()
            try:
                start_ioc(ioc_name=ioc)
                stop_ioc(ioc_name=ioc)
            except IOError:
                errored_iocs.append(ioc)
            finally:
                globals_file.truncate(0)
