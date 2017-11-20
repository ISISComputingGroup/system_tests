import shutil
import os
import re
import sys
import subprocess

#KITS_ROOT = r'p:\Kits$\CompGroup\ICP'
KITS_ROOT = r'q:'
EPICS_KITS_DIR = KITS_ROOT + r'\EPICS\EPICS_win7_x64'
GUI_KITS_DIR = KITS_ROOT + r'\Client'
PYTHON_KITS_DIR = KITS_ROOT + r'\genie_python'

EPICS_BUILD_FOLDER_PATTERN = "BUILD-(\d+)"
PYTHON_BUILD_FOLDER_PATTERN = "BUILD-(\d+)"
GUI_BUILD_FOLDER_PATTERN = "BUILD(\d+)"

def get_folder(kits_root, build_pattern):
    """locate latest kit from the build folder pattern"""
    version = 0
    folder = None
    for x in os.listdir(kits_root):
        m = re.match(build_pattern, x)
        if m is not None:
            if os.path.isfile(os.path.join(kits_root, x, 'COPY_COMPLETE.txt')):
                d = int(m.groups()[0])
                if d > version:
                    version = d
                    folder = x
    return (folder, version)
# Find the latest version of EPICS
(folder, version) = get_folder(EPICS_KITS_DIR, EPICS_BUILD_FOLDER_PATTERN)

if folder is not None:
    print "Copying EPICS build %d from %s, please wait..." % (version, folder)
    shutil.copytree(os.path.join(EPICS_KITS_DIR, folder, 'EPICS'), "C:\\Instrument\\Apps\\EPICS")
else:
    print "Cannot find EPICS"
    sys.exit(1)

# Find the latest version of the GUI
(folder, version) = get_folder(GUI_KITS_DIR, GUI_BUILD_FOLDER_PATTERN)

if folder is not None:
    print "Copying GUI build %d from %s, please wait..." % (version, folder)
    shutil.copytree(os.path.join(GUI_KITS_DIR, folder), "ibex_gui")
else:
    print "Cannot find GUI"
    sys.exit(1)

# Find the latest version of genie_python
(folder, version) = get_folder(PYTHON_KITS_DIR, PYTHON_BUILD_FOLDER_PATTERN)

if folder is not None:
    print "Installing Python build %d from %s, please wait..." % (version, folder)
    subprocess.check_call([os.path.join(PYTHON_KITS_DIR, folder, "genie_python_install.bat")], shell=True)
else:
    print "Cannot find Python"
    sys.exit(1)
