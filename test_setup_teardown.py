import argparse
import os

from configobj import ConfigObj
from psutil import virtual_memory

ICP_BINARIES = os.path.join(os.environ.get("EPICS_ROOT"), "ICP_Binaries")
CONFIG_FILE = "isisicp.properties"
CONFIG_BACKUP = "{}.backup".format(CONFIG_FILE)

icp_config_file_path = os.path.join(ICP_BINARIES, CONFIG_FILE)
icp_config_backup_file_path = os.path.join(ICP_BINARIES, CONFIG_BACKUP)


def measure_memory_usage():
    print(virtual_memory().used)


def restore_isisicp_config():
    config = ConfigObj(icp_config_backup_file_path)
    config.filename = icp_config_file_path
    config.write()


def turn_on_datastreaming():
    config_backup = ConfigObj(icp_config_file_path)
    config_backup.filename = icp_config_backup_file_path
    config_backup.write()

    config = ConfigObj(icp_config_file_path)
    config["isisicp.kafkastream"] = True
    config["isisicp.kafkastream.topicprefix"] = "TEST"
    config["isisicp.kafkastream.broker"] = "localhost:9092"
    config["isisicp.incrementaleventnexus"] = True
    config.write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set up and tear down tests (run whilst the server not started).')
    parser.add_argument('--tear_down', action='store_const', const=True, default=False,
                        help='run the tearDown of the tests, default is false so will run set up')
    args = parser.parse_args()

    if not args.tear_down:
        measure_memory_usage()
        turn_on_datastreaming()
    else:
        restore_isisicp_config()