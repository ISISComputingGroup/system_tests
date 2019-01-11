"""
Utilities for genie python system tests.
"""

import json

from time import sleep

# import genie either from the local project in pycharm or from virtual env
try:
    from source import genie_api_setup
    from source import genie as g
except ImportError:
    from genie_python import genie as g
    from genie_python import genie_api_setup

# import genie utilities either from the local project in pycharm or from virtual env
try:
    from source.utilities import dehex_and_decompress, compress_and_hex
except ImportError:
    from genie_python.utilities import dehex_and_decompress, compress_and_hex

WAIT_FOR_SERVER_TIMEOUT = 60
"""Number of seconds to wait for a pv to become available in the config server e.g. when it starts or 
when it changed config"""


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
    for i in range(WAIT_FOR_SERVER_TIMEOUT):
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
    Returns the current config name after waiting for up to WAIT_FOR_SERVER_TIMEOUT seconds for it to be readable
    Returns: the current configs name
    Raises: AssertionError if the cv can not be read

    """
    final_exception = None
    for i in range(WAIT_FOR_SERVER_TIMEOUT):
        try:
            current_config_pv = g.get_pv("CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS", is_local=True)
            if current_config_pv is None:
                raise AssertionError("Current config is none, is the server running?")
            current_config = json.loads(dehex_and_decompress(current_config_pv))
            return current_config["name"]
        except Exception as final_exception:
            sleep(1)
            print("Waiting for config pv: count {}".format(i))

    raise final_exception


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

    except Exception:
        return None


def set_genie_python_raises_exceptions(does_throw):
    """
    Set that genie python api raises exceptions instead of just logging a message
    Args:
        does_throw: True if it should raise, False otherwise

    Returns:

    """
    genie_api_setup._exceptions_raised = does_throw
