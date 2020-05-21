from psutil import virtual_memory
import os
from utilities.utilities import BASE_MEMORY_USAGE
from configobj import ConfigObj

ICP_BINARIES = os.path.join(os.environ.get("EPICS_ROOT"), "ICP_Binaries")


def measure_memory_usage():
    os.environ[BASE_MEMORY_USAGE] = str(virtual_memory().used)


def turn_on_datastreaming():
    icp_config_file_path = os.path.join(ICP_BINARIES, "isisicp.properties")
    config = ConfigObj(icp_config_file_path)
    config["isisicp.kafkastream"] = True
    config["isisicp.kafkastream.topicprefix"] = "TEST"
    config["isisicp.kafkastream.broker"] = "localhost:9092"
    config["isisicp.incrementaleventnexus"] = True
    config.write()


if __name__ == "__main__":
    measure_memory_usage()
    turn_on_datastreaming()
