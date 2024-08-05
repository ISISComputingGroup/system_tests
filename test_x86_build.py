import os
import subprocess
import unittest

from genie_python import genie as g

from utilities import utilities

BLOCK_NAME = "SIMPLE_BLOCK_1"
BLOCK_PV = "SIMPLE:HELLO"
CAGET_EXE = "caget.exe"

class Testx86Builds(unittest.TestCase):
    """
    Tests to test the 32 bit builds
    """
        
    def _get_local_caget_path(self):
        """
        Helper function to get the caget path from the current build
        """
        BIN_PATH = os.path.join(r"C:\\", "Instrument", "Apps", "EPICS", "base", "master", "bin")
        # give a default EPICS build of windows 64 bit
        host_arch = "windows-x64" 

        if 'EPICS_HOST_ARCH' in os.environ:
            host_arch = os.environ['EPICS_HOST_ARCH']
        else:
            print(f"Warning: EPICS_HOST_ARCH not set. Using default value of '{host_arch}'")
        
        return os.path.join(BIN_PATH, host_arch, CAGET_EXE)

    def _parse_caget_output(self, out_string):
        """
        Helper function to the parse output of a caget to get just the value
        """ 
        index = 0
        flag = False

        # search string backwards for two consecutive spaces then return the string before them
        # (otherwise return whole string)
        for i in range(2, len(out_string)+1):
            if out_string[-i] == " " and out_string[-i-1] == " ":
                flag == True
                index = i - 1
                break
        
        return out_string[-index:]

    # This test will run on both build architectures but is implemented to check x86 IOCs can communicate with a x64 client
    def test_GIVEN_a_local_IOC_and_gateway_THEN_a_x64_client_can_read_from_them(self):
        utilities.load_config_if_not_already_loaded("test_x86_build")

        result = ""

        # get and parse value from x64 caget
        try:
            result = subprocess.run([CAGET_EXE, g.prefix_pv_name(BLOCK_PV)], capture_output=True)
            result = self._parse_caget_output(result.stdout.decode())
        except Exception as e:
            print(f"The command {os.path.join(os.getcwd(), CAGET_EXE)} {g.prefix_pv_name(BLOCK_PV)} failed to execute.")
            print(e)
        
        self.assertEqual(result.strip(), g.cget(BLOCK_NAME)["value"])

    # This test will run on both build architectures but is implemented to check x86 IOCs can communicate with a x86 client
    def test_GIVEN_a_local_IOC_and_gateway_THEN_the_local_client_can_read_from_them(self):
        utilities.load_config_if_not_already_loaded("test_x86_build")

        LOCAL_CAGET = self._get_local_caget_path()
        result = ""

        # get and parse value from local caget
        try:
            result = subprocess.run([LOCAL_CAGET, g.prefix_pv_name(BLOCK_PV)], capture_output=True)
            result = self._parse_caget_output(result.stdout.decode())
        except Exception as e:
            print(f"The command {LOCAL_CAGET} {g.prefix_pv_name(BLOCK_PV)} failed to execute.")
            print(e)
            
        self.assertEqual(result.strip(), g.cget(BLOCK_NAME)["value"])
