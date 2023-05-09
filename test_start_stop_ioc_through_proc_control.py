"""
System tests for starting or stopping iocs through Proc server
"""
import os
import unittest
import xml.etree.ElementTree as ET
from time import time
from typing import List

from hamcrest import assert_that, less_than
from six.moves import range

from utilities.utilities import g, as_seconds, start_ioc, stop_ioc, wait_for_ioc_start_stop, \
    load_config_if_not_already_loaded, bulk_start_ioc, bulk_stop_ioc

# The following iocs are ignored in the test which starts/stops all iocs
# This is usually because they don't build by default, or have some complex dependency,
# or are special in some way (e.g. psctrl).
# we also ignore ISISDAE, INSTETC and RUNCTRL as testing them here messed up subsequent tests
# by leaving these IOCs permanently stopped. We could re-enable testing them if this test was either
# always ran last or could re-enabel autostart on these ioc afterwards    
IOCS_TO_IGNORE_START_STOP = [
    'ASTRIUM_01',
    'ASTRIUM_02',
    'BGRSCRPT_01',  # Won't keep running unless it has a config file
    'BGRSCRPT_02',
    'CHOPPERSIM',  # Simulation ioc
    'CAENMCA',  # currently fails to start, and is not used so skip
    'DELFTDCMAG_01',  # Delft iocs have a weird build/run process?
    'DELFTDCMAG_02',
    'DELFTSHEAR_01',
    'ECLAB_01',
    'INSTETC',
    'ISISDAE',
    'LSICORR_01',  # Needs vendor library in correct place to keep running
    'LSICORR_02',
    'MOTORSIM',  # Simulation ioc
    'MOXA12XX_01',
    'MOXA12XX_02',
    'MOXA12XX_03',
    'MK3CHOPR_01',
    'NANODAC_01',
    'OERCONE_02',
    'PIXELMAN',
    'PSCTRL',  # Special, controls other IOCs
    'REFL_01',  # Won't run correctly without a config
    'RUNCTRL',
    'SECI2IBEX',  # requires labview
    'SEPRTR',  # relies on daqMX
    'TC_01',  # relies on twincat
    'ZFMAGFLD'  # relies on daqMX
]

GLOBALS_FILENAME = os.path.join(os.environ['ICPCONFIGROOT'], "globals.txt")


class TestProcControl(unittest.TestCase):
    """
    Test class for tests on proc control.
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

        # A test to check all IOCs start and stop correctly
        # Implemented to test for the error we encountered where we met our procserv limit and some iocs didn't start

        error_iocs = []
        failed_to_start = []
        failed_to_stop = []
        number_to_run = 40

        ## disable for moment
        #iocs_to_test = self._prepare_ioc_list()
        iocs_to_test = []

        # Test handles Channel access exceptions, so set us to handle it to reduce prints.
        g.toggle.exceptions_raised(True)
        for chunk in self._chunk_iocs(iocs_to_test, number_to_run):
            start_time = time()
            failed_to_start, not_in_proc_serv = bulk_start_ioc(chunk)
            failed_to_stop = bulk_stop_ioc([ioc for ioc in chunk if ioc not in failed_to_start
                                            and ioc not in not_in_proc_serv])
            for ioc in failed_to_start + failed_to_stop:
                if not self._retry_in_recsim(ioc):
                    error_iocs.append(ioc)
            count = time() - start_time
            print(f"Check from {chunk[0]} to {chunk[-1]} ({len(chunk)} iocs), in {count} seconds.")

        g.toggle.exceptions_raised(False)
        failed_to_start = [ioc for ioc in failed_to_start if ioc in error_iocs]
        failed_to_stop = [ioc for ioc in failed_to_stop if ioc in error_iocs]
        self.assertEqual(failed_to_start, [], f"IOCs failed to start: {failed_to_start}")
        self.assertEqual(failed_to_stop, [], f"IOCs failed to stop: {failed_to_stop}")
        self.assertEqual(not_in_proc_serv, [], f"IOCs not in proc serv: {not_in_proc_serv}")

    def _prepare_ioc_list(self):
        """
        Helper method to prepare the list of IOCs for testing.
        Gets all IOCs, checks the list is sensible, removes those that should be skipped.
        :return: The list of IOCs to test, sorted alphanumerically.
        """
        iocs_to_test = []
        tree = ET.parse(os.path.join("C:\\", "Instrument", "Apps", "EPICS", "iocstartup", "config.xml"))
        root = tree.getroot()

        # IOCs are listed in the above XML file under two different schemas, we need both
        schemas = (
            "{http://epics.isis.rl.ac.uk/schema/ioc_config/1.0}",
            "{http://epics.isis.rl.ac.uk/schema/ioc_configs/1.0}"
        )

        for schema in schemas:
            iocs_to_test.extend([ioc_config.attrib["name"] for ioc_config in root.iter(f"{schema}ioc_config")])

        # Check parsed IOCs are a sensible length check there's at least one known ioc in the list
        if not len(iocs_to_test) > 100:
            if not any(item in iocs_to_test for item in ["SIMPLE", "AMINT2L_01", "EUROTHRM_01", "INSTETC_01"]):
                # Fairly long test so error out early if IOCs aren't in a sensible state
                raise ValueError("List of IOCs not in a sensible state. Have you run IOC startups?")
        # Check IOC 1 and IOC2, but not other IOCs as they should follow the same format as IOC 2.
        iocs_to_test = [ioc for ioc in iocs_to_test if self._skip_high_ioc_nums(ioc) and not self._ignore_ioc(ioc)]
        iocs_to_test.sort()
        return iocs_to_test

    @staticmethod
    def _ignore_ioc(ioc: str):
        """
        Helper method to check if a given IOC should be skipped
        :param ioc: The IOC to check
        :return: true if the IOC should be skipped otherwise false
        """
        return any(ioc.startswith(ioc_name) for ioc_name in IOCS_TO_IGNORE_START_STOP)

    @staticmethod
    def _skip_high_ioc_nums(ioc: str):
        """
        Helper method to check if an IOC is of number greater than 1 or 2 to allow skipping of higher duplicates.
        :param ioc: The IOC to check.
        :return: True if the IOC is 2 or 2, otherwise False.
        """
        return "_01" in ioc or "_02" in ioc

    @staticmethod
    def _chunk_iocs(ioc_list: List[str], chunk_size: int):
        """
        Generator to break list into equally sized chunks.
        :param ioc_list:  The list to break up.
        :param chunk_size: The size of each chunk.
        :return: an iterator that gives the next chunk of the list.
        """
        for i in range(0, len(ioc_list), chunk_size):
            yield ioc_list[i:i + chunk_size]

    @staticmethod
    def _retry_in_recsim(ioc: str):
        """
        Helper method to retry starting and stopping an IOC in rec sim
        :param ioc: The IOC to test.
        :return: True if the retry succeeded, else false.
        """
        succeeded = True
        # open with w flag and overwrite - we don't need to
        with open(GLOBALS_FILENAME, "w", encoding="ascii") as globals_file:
            globals_file.write(f"{ioc}__RECSIM=1")
            globals_file.flush()
            try:
                start_ioc(ioc_name=ioc)
                stop_ioc(ioc_name=ioc)
            except IOError:
                succeeded = False
            finally:
                globals_file.truncate(0)
        return succeeded
