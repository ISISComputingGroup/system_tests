"""
Utilities for genie python system tests.
"""

import json
import os
import six
import unittest

from time import sleep, time

# import genie either from the local project in pycharm or from virtual env
from mock import patch

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
DAE_MODE_TIMEOUT = 120


def parameterized_list(cases):
    """
    Creates a list of cases for parameterized to use to run tests.

    E.g.
    parameterized_list([1.3435, 12321, 1.0])
        = [("1.3435", 1.3435),("12321", 12321), ("1.0", 1.0)]

    Args:
         cases: List of cases to use in tests.

    Returns:
        list: list of tuples of where the first item is str(case).
    """

    return_list = []

    for case in cases:
        test_case = (str(case),)
        try:
            return_list.append(test_case + case)
        except TypeError:
            return_list.append(test_case + (case,))

    return return_list


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
        raise AssertionError("Couldn't change config to '{}' it is '{}'."
                             "(Is this because that configs schema is invalid?)".format(config_name, current_config))


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
    if not g.get_dae_simulation_mode():
        g.set_dae_simulation_mode(True, skip_required_runstates=True)
        _wait_for_and_assert_dae_simulation_mode(True)

    if g.get_runstate() != "SETUP":
        g.abort()
        g.waitfor_runstate("SETUP", maxwaitsecs=DAE_MODE_TIMEOUT)

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
    Waits for specified DAE simulation mode in the DAE

    Args:
        mode: Boolean, True if the DAE is in simulation mode

    Returns:
        None

    Raises:
        AssertionError if the simulation mode cannot be written

    """
    start_time = time()
    while time() - start_time < DAE_MODE_TIMEOUT:
        if g.get_dae_simulation_mode() == mode:
            return
        sleep(1.0)
    if g.get_dae_simulation_mode() != mode:
        sim_val = g.get_pv("DAE:SIM_MODE", is_local=True)
        raise AssertionError("Could not set DAE simulation mode to {} - current SIM_MODE PV value is {}".format(mode,sim_val))


def set_wait_for_complete_callback_dae_settings(wait):
    """ Sets the wait for completion callback attribute of the DAE

    @param wait: Boolean value, True if you want the DAE to wait for the operation 
    to complete before returning
    """
    genie_api_setup.__api.dae.wait_for_completion_callback_dae_settings = wait


def temporarily_kill_icp():
    # Temporarily kills the ISIS ICP (ISIS DAE)

    return genie_api_setup.__api.dae.temporarily_kill_icp()
  
def as_seconds(time):
    """
    Convert a up time to seconds
    Args:
        time: in format HH:MM:SS

    Returns: time in seconds

    """
    bits = time.split(":")
    seconds = 0
    for bit in bits:
        seconds *= 60
        seconds += int(bit)

    return seconds


def _start_stop_ioc_is_a_start(is_a_start, ioc_name):
    """
    Start or stop and ioc dependent on whether it "is_a_start"
    Args:
        is_a_start: True start the ioc; False stop the ioc
        ioc_name: name of the ioc

    Raises:
        IOError error if IOC does not start/stop after 30 seconds

    """
    if is_ioc_up(ioc_name) != is_a_start:
        g.set_pv("CS:PS:{}:{}".format(ioc_name, "START" if is_a_start else "STOP"), 1, is_local=True)

    wait_for_ioc_start_stop(timeout=30, is_start=is_a_start, ioc_name=ioc_name)


def start_ioc(ioc_name):
    """
    Start the ioc
    Args:
        ioc_name: name of the ioc to start

    Raises:
        IOError error if IOC does not start after 30 seconds
    """
    _start_stop_ioc_is_a_start(True, ioc_name)


def stop_ioc(ioc_name):
    """
    Stop the ioc
    Args:
        ioc_name: name of the ioc to stop

    Raises:
        IOError error if IOC does not stop after 30 seconds
    """
    _start_stop_ioc_is_a_start(False, ioc_name)


def wait_for_ioc_start_stop(timeout, is_start, ioc_name):
    """
    Wait for an ioc to start or stop, if timeout raise a timeout error
    Args:
        timeout: time to wait before there is a timeout error
        is_start: True to wait for ioc to be started; False to wait for stop
        ioc_name: name of the ioc to wait for

    Raises:
        IOError error if IOC does not start/stop after timeout
    """
    for count in range(timeout):
        g.waitfor_time(seconds=1)
        print("Waited {}s for IOC to {}".format(count, "start" if is_start else "stop"))
        if is_ioc_up(ioc_name) == is_start:
            break
    else:
        raise IOError("IOC is not {}".format("started" if is_start else "stopped"))


def is_ioc_up(ioc_name):
    """
    Determine if IOC is up by checking for the existence of its heartbeat PV
    Args:
        ioc_name: IOC to check

    Returns: True if IOC is up; False otherwise
    """
    return g.get_pv("AS:{}:SR_heartbeat".format(ioc_name), is_local=True) is not None


def retry_on_failure(max_times):
    """
    Decorator that will retry running a test if it failed.
    :param max_times: Maximum number of times to retry running the test
    :return: the decorator
    """
    def decorator(func):
        @six.wraps(func)
        def wrapper(*args, **kwargs):
            err = None
            for attempt in range(max_times):
                try:
                    func(*args, **kwargs)
                    return
                except unittest.SkipTest:
                    raise
                except Exception as e:
                    print("\nTest failed (attempt {} of {}). Retrying...".format(attempt+1, max_times))
                    err = e
            if err is not None:
                raise err
        return wrapper
    return decorator

def check_block_exists(block_name):
    blocks = g.get_blocks()
    return block_name in blocks
