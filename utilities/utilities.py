"""
Utilities for genie python system tests.
"""

import json
import os

from time import sleep

# import genie either from the local project in pycharm or from virtual env
try:
    from source import genie_api_setup
    from source import genie as g
    from source import genie_dae
except ImportError:
    from genie_python import genie as g
    from genie_python import genie_dae
    from genie_python import genie_api_setup

# import genie utilities either from the local project in pycharm or from virtual env
try:
    from source.utilities import dehex_and_decompress, compress_and_hex
except ImportError:
    from genie_python.utilities import dehex_and_decompress, compress_and_hex

WAIT_FOR_SERVER_TIMEOUT = 60
"""Number of seconds to wait for a pv to become available in the config server e.g. when it starts or 
when it changed config"""

# Number of seconds to wait for the DAE settings to update
DAE_MODE_TIMEOUT = 300


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


def setup_simulated_wiring_tables():
    """
    Configures the DAE's wiring tables and sets the DAE to simulation mode

    Returns:
        None

    """
    if g.get_runstate() != "SETUP":
        g.abort()
        g.waitfor_runstate("SETUP")

    if not g.get_dae_simulation_mode():
        g.set_dae_simulation_mode(True)
        _wait_for_and_assert_dae_simulation_mode(True)

    table_path_template = r"{}\tables\RCPTT_{}128.dat".format(os.environ["ICPCONFIGROOT"], "{}")
    set_wait_for_complete_callback_dae_settings(True)

    g.change_start()
    g.change_tables(
        wiring=table_path_template.format("wiring"),
        detector=table_path_template.format("detector"),
        spectra=table_path_template.format("spectra"))
    g.change_tcb(0, 10000, 100)
    g.change_finish()
    set_genie_python_raises_exceptions(False)


def _wait_for_and_assert_dae_simulation_mode(mode):
    """
    Writes the DAE simulation mode to the DAE

    Args:
        mode: Boolean, True if the DAE is in simulation mode

    Returns:
        None

    Raises:
        AssertionError if the simulation mode cannot be written

    """
    for _ in range(DAE_MODE_TIMEOUT):
        if g.get_dae_simulation_mode() == mode:
            return
        sleep(1)
    else:
        if g.get_dae_simulation_mode() != mode:
            raise AssertionError("Could not set DAE simulation mode to {}".format(mode))


def set_wait_for_complete_callback_dae_settings(wait):
    """ Sets the wait for completion callback attribute of the DAE

    @param wait: Boolean value, True if you want the DAE to wait for the operation 
    to complete before returning
    """
    genie_api_setup.__api.dae.wait_for_completion_callback_dae_settings = wait


def temporarily_kill_icp():
    # Temporarily kills the ISIS ICP (ISIS DAE)

    return genie_api_setup.__api.dae.temporarily_kill_icp()
