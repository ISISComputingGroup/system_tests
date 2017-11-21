"""
Utilities for genie python system tests.
"""

import json

from time import sleep

# import genie either from the local project in pycharm or from virtual env
try:
    from source import genie as g
except ImportError:
    from genie_python import genie as g

# import genie utilities either from the local project in pycharm or from virtual env
try:
    from source.utilities import dehex_and_decompress, compress_and_hex
except ImportError:
    from genie_python.utilities import dehex_and_decompress, compress_and_hex


def load_config_if_not_already_loaded(config_name):
    """
    Load a config be name if it has not already been loaded.

    Args:
        config_name: config to load

    Raises:
        AssertionError if there is something wrong

    """
    current_config = _get_config_name()

    if current_config == config_name:
        return

    g.set_pv("CS:BLOCKSERVER:LOAD_CONFIG", value=compress_and_hex(config_name), is_local=True)
    status_was_busy = False
    for i in range(60):
        status = get_server_status()
        if status_was_busy and status == "":
            break
        elif status is not None and status != "":
            status_was_busy = True
        sleep(1)
        print("Waiting for server: count {}".format(i))

    current_config = _get_config_name()
    if current_config != config_name:
        raise AssertionError("Couldn't change config to {} it is '{}'".format(config_name, current_config))


def _get_config_name():
    """

    Returns: the current configs name
    Raises: AssertionError if the cv can not be read

    """
    current_config_pv = g.get_pv("CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS", is_local=True)
    if current_config_pv is None:
        raise AssertionError("Current config is none, is the server running?")
    current_config = json.loads(dehex_and_decompress(current_config_pv))
    return current_config["name"]


def get_server_status():
    """
    Get the servers current status

    Returns: server status; None if status can not be read from the PV

    """
    status_as_pv = g.get_pv("CS:BLOCKSERVER:SERVER_STATUS", is_local=True)
    if status_as_pv is None:
        return None

    try:
        as_json = json.loads(dehex_and_decompress(status_as_pv))
        return as_json["status"]

    except ValueError:
        return None
