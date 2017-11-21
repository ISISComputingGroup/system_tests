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
# Add root path for access to server_commons
import os
import sys
# Standard imports
import unittest

import shutil
import xmlrunner
import argparse


SCRIPT_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__)))
DEFAULT_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'test-reports')
CONFIGS_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, 'configs')

# default icp config path
default_configs_path = os.path.join("C:\\", "Instrument", "Settings", "config",
                                    os.environ.get("COMPUTERNAME", "NAME"), "configurations")
# path to ICP CONFIG ROOT
PATH_TO_ICPCONFIGROOT = os.environ.get("ICPCONFIGROOT", default_configs_path)
SETTINGS_CONFIG = os.path.join(PATH_TO_ICPCONFIGROOT, "configurations")

if __name__ == '__main__':
    # get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load tests from test suites
    test_suite = unittest.TestLoader().discover(SCRIPT_DIRECTORY, pattern="test_*.py")

    config_dirs = [name for name in os.listdir(CONFIGS_DIRECTORY)
                   if os.path.isdir(os.path.join(CONFIGS_DIRECTORY, name))]

    for config_dir in config_dirs:
        dest = os.path.join(SETTINGS_CONFIG, config_dir)
        src = os.path.join(CONFIGS_DIRECTORY, config_dir)
        try:
            shutil.rmtree(dest)
        except OSError:
            pass
        shutil.copytree(src, dest)

    print("\n\n------ BEGINNING genie_python SYSTEM TESTS ------")
    ret_vals = list()
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(test_suite))
    print("------ UNIT TESTS COMPLETE ------\n\n")

    # Return failure exit code if a test failed
    sys.exit(False in ret_vals)
