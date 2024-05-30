# This file is part of the ISIS IBEX application.
# Copyright (C) 2017 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php
"""
Run system tests for genie_python. Copies across needed configs before running the tests.
"""

import os
import sys
import time
import unittest

import shutil
import xmlrunner
import argparse
from utilities import utilities
from genie_python import genie as g


SCRIPT_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DEFAULT_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'test-reports')
CONFIGS_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'configs')

NUM_RETRY_DELETION = 5

# default icp config path
default_configs_path = os.path.join("C:\\", "Instrument", "Settings", "config",
                                    os.environ.get("COMPUTERNAME", "NAME"), "configurations")
# path to ICP CONFIG ROOT
PATH_TO_ICPCONFIGROOT = os.environ.get("ICPCONFIGROOT", default_configs_path)

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', default=DEFAULT_DIRECTORY,
                        help='The directory to save the test reports')
    parser.add_argument('-t', '--tests', default=None, nargs='+',
                        help="""Dotted names of tests to run. These are of the form module.class.method.
                                    Module just runs the tests in a module. 
                                    Module.class runs the the test class in Module.
                                    Module.class.method runs a specific test.""")
    parser.add_argument('-f', '--failfast', action='store_true',
                        help="""Determines if the rest of tests are skipped after the first failure""")

    arguments = parser.parse_args()
    xml_dir = arguments.output_dir
    failfast_switch = arguments.failfast

    # Load tests from test suites
    if arguments.tests is not None:
        test_suite = unittest.TestLoader().loadTestsFromNames(arguments.tests)
    else:
        test_suite = unittest.TestLoader().discover(SCRIPT_DIRECTORY, pattern="test_*.py")

    config_dirs = [name for name in os.listdir(CONFIGS_DIRECTORY)
                   if os.path.isdir(os.path.join(CONFIGS_DIRECTORY, name))]

    for config_dir in config_dirs:
        dest = os.path.join(PATH_TO_ICPCONFIGROOT, config_dir)
        src = os.path.join(CONFIGS_DIRECTORY, config_dir)

        for file_or_dir in os.listdir(src):
            file_or_dir_dest = os.path.join(dest, file_or_dir)
            file_or_dir_src = os.path.join(src, file_or_dir)

            for _ in range(NUM_RETRY_DELETION):
                try:
                    if os.path.isdir(file_or_dir_src):
                        shutil.rmtree(file_or_dir_dest, True)
                        # If we don't break it will attempt delete what it just deleted
                        break
                    elif os.path.isfile(file_or_dir_dest):
                        os.remove(file_or_dir_dest)
                        break
                    else:
                        print(f"File {file_or_dir_dest} does not exist")
                        break
                except OSError as e:
                    print(f"Error deleting file {file_or_dir_dest} exception message is {e}")
                time.sleep(2)
            if os.path.isdir(file_or_dir_src):
                shutil.copytree(file_or_dir_src, file_or_dir_dest)
            else:
                shutil.copy(file_or_dir_src, dest)

    g.set_instrument(None)
    utilities.load_config_if_not_already_loaded("empty_for_system_tests")
    utilities.wait_for_iocs_to_be_up(["ISISDAE_01"], 300)


    print("\n\n------ BEGINNING genie_python SYSTEM TESTS ------")
    ret_vals = list()
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir, stream=sys.stdout, failfast=failfast_switch, verbosity=3).run(test_suite).wasSuccessful())
    print("------ UNIT TESTS COMPLETE ------\n\n")

    # Return failure exit code if a test failed
    sys.exit(False in ret_vals)
