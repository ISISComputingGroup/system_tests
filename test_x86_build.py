import unittest
import subprocess
import os 
import shutil
from genie_python import genie as g

from utilities import utilities



BLOCK_NAME = "SIMPLE_BLOCK_1"
BLOCK_PV = "SIMPLE:HELLO"
LOCAL_CAGET_EXE = "caget.exe"
LOCAL_x86_CAGET = os.path.join(r"C:\\", "Instrument", "Apps", "EPICS", "base", "master", "bin", "win32-x86", "caget.exe")

class Testx86Builds(unittest.TestCase):
    """
    Tests to test the 32 bit builds
    """
    
    def _get_latest_static_build(self):
        """
        Helper function to get the path of caget from the latest static x64 EPICS build
        """
        INST_SHARE_AREA = os.path.join(r"\\isis.cclrc.ac.uk", "inst$", "Kits$", "CompGroup", "ICP", "EPICS", 
                "EPICS_STATIC_CLEAN_win7_x64")
        CAGET_PATH = os.path.join("EPICS", "base", "master", "bin", "windows-x64-static", "caget.exe")
        BUILD_DIR = "BUILD-"

        latest_build = os.path.join(INST_SHARE_AREA, "LATEST_BUILD.txt")
        with open(latest_build, 'r') as file:
            content = file.read().strip()
        
        return os.path.join(INST_SHARE_AREA, BUILD_DIR + content, CAGET_PATH)
        
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

    def test_GIVEN_a_x86_IOC_and_gateway_THEN_a_x64_client_can_read_from_them(self):
        utilities.load_config_if_not_already_loaded("test_x86_build")

        result = ""

        # copy the x64 caget file locally
        CAGET_PATH = self._get_latest_static_build()
        try:
            shutil.copyfile(CAGET_PATH, LOCAL_CAGET_EXE)
        except Exception as e:
            print("Failed to copy x64 caget file from share")
            raise e
        
        # get and parse value from x64 caget
        try:
            result = subprocess.run([LOCAL_CAGET_EXE, g.prefix_pv_name(BLOCK_PV)], capture_output=True)
            result = self._parse_caget_output(result.stdout.decode())
        except Exception as e:
            print(f"A local copy of the command {CAGET_PATH} {g.prefix_pv_name(BLOCK_PV)} failed to execute: {e}")
        
        # remove the local x64 caget file
        os.remove(LOCAL_CAGET_EXE)

        self.assertEqual(result.strip(), g.cget(BLOCK_NAME)["value"])

    def test_GIVEN_a_x86_IOC_and_gateway_THEN_a_x86_client_can_read_from_them(self):
        utilities.load_config_if_not_already_loaded("test_x86_build")

        result = ""

        # get and parse value from x32 caget
        try:
            result = subprocess.run([LOCAL_x86_CAGET, g.prefix_pv_name(BLOCK_PV)], capture_output=True)
            result = self._parse_caget_output(result.stdout.decode())
        except Exception as e:
            print(f"The command {LOCAL_x86_CAGET} {g.prefix_pv_name(BLOCK_PV)} failed to execute: {e}")
            
        self.assertEqual(result.strip(), g.cget(BLOCK_NAME)["value"])