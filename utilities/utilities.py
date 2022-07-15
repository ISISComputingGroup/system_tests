"""
Utilities for genie python system tests.
"""

import json
import os
import timeit
import unittest
from time import sleep, time
from typing import Callable

import six
# import genie either from the local project in pycharm or from virtual env
from genie_python.channel_access_exceptions import UnableToConnectToPVException

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

WAIT_FOR_SERVER_TIMEOUT = 200
"""Number of seconds to wait for a pv to become available in the config server e.g. when it starts or
when it changed config"""

# Number of seconds to wait for the DAE settings to update
DAE_MODE_TIMEOUT = 120

# Number of seconds to wait for IOC to start/stop
IOCS_START_STOP_TIMEOUT = 60

# The environment variable used to store the baseline memory usage
BASE_MEMORY_USAGE = "BASE_MEMORY_USAGE"


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
    Load a config by name if it has not already been loaded.

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
        if status is not None and status != "":
            status_was_busy = True
        sleep(1)
        print(f"Waiting for server: count {i}")

    current_config = _get_config_name()
    if current_config != config_name:
        raise AssertionError(f"Couldn't change config to '{config_name}' it is '{current_config}'."
                             "(Is this because that configs schema is invalid?)")


def _get_config_name():
    """
    Returns the current config name after waiting for up to WAIT_FOR_SERVER_TIMEOUT seconds for it to be readable
    Returns: the current configs name
    Raises: AssertionError if the cv can not be read

    """
    return get_config_details()["name"]


def get_config_details():
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
            return current_config
        except Exception as ex:
            sleep(1)
            print(f"Waiting for config pv: count {i}")
            final_exception = ex

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


def setup_simulated_wiring_tables(event_data=False):
    """
    Configures the DAE's wiring tables and sets the DAE to simulation mode

    Args:
        event_data (bool): true if event data wiring tables should be loaded.

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
    wiring_table = table_path_template.format("wiring_events" if event_data else "wiring")

    set_wait_for_complete_callback_dae_settings(True)

    g.change_start()
    g.change_tables(
        wiring=wiring_table,
        detector=table_path_template.format("detector"),
        spectra=table_path_template.format("spectra"))
    g.change_tcb(0, 10000, 100)
    if event_data:
        g.change_tcb(0, 10000, 100, regime=2)
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
        raise AssertionError(f"Could not set DAE simulation mode to {mode} - current SIM_MODE PV value is {sim_val}")


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
        IOError error if IOC does not start/stop after IOCS_START_STOP_TIMEOUT seconds

    """
    if is_ioc_up(ioc_name) != is_a_start:
        g.set_pv(f"CS:PS:{ioc_name}:{'START' if is_a_start else 'STOP'}", 1, is_local=True)

    wait_for_ioc_start_stop(timeout=IOCS_START_STOP_TIMEOUT, is_start=is_a_start, ioc_name=ioc_name)


def bulk_start_ioc(ioc_list):
    """
    start a list of IOCs in bulk
    :param ioc_list: a list of the names of the IOCs to start
    :return: a list of IOCs that failed to start after IOCS_START_STOP_TIMEOUT seconds
    """
    failed_to_start = []

    for ioc_name in ioc_list:
        if quick_is_ioc_down(ioc_name):
            g.set_pv(f"CS:PS:{ioc_name}:START", 1, is_local=True)
    for ioc_name in ioc_list:
        try:
            wait_for_ioc_start_stop(timeout=IOCS_START_STOP_TIMEOUT, is_start=True, ioc_name=ioc_name)
        except IOError:
            failed_to_start.append(ioc_name)
    return failed_to_start


def bulk_stop_ioc(ioc_list):
    """
    Stops a list of IOCs in bulk
    :param ioc_list: a list of the names of the IOCs to stop
    :raises: IOError if IOC does not stop after IOCS_START_STOP_TIMEOUT seconds
    """
    failed_to_stop = []
    for ioc_name in ioc_list:
        if not quick_is_ioc_down(ioc_name):
            g.set_pv(f"CS:PS:{ioc_name}:STOP", 1, is_local=True)
    for ioc_name in ioc_list:
        try:
            wait_for_ioc_start_stop(timeout=IOCS_START_STOP_TIMEOUT, is_start=False, ioc_name=ioc_name)
        except IOError:
            failed_to_stop.append(ioc_name)
    return failed_to_stop


def start_ioc(ioc_name):
    """
    Start the ioc
    Args:
        ioc_name: name of the ioc to start

    Raises:
        IOError error if IOC does not start after IOCS_START_STOP_TIMEOUT seconds
    """
    _start_stop_ioc_is_a_start(True, ioc_name)


def stop_ioc(ioc_name):
    """
    Stop the ioc
    Args:
        ioc_name: name of the ioc to stop

    Raises:
        IOError error if IOC does not stop after IOCS_START_STOP_TIMEOUT seconds
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
    start_time = time()
    count = 0
    while count < timeout:
        count = time() - start_time
        if is_ioc_up(ioc_name) == is_start:
            if count > 0:
                print(f"Waited {count}s for {ioc_name} to {'start' if is_start else 'stop'}")
            break
        sleep(1.0)
    else:
        raise IOError(f"IOC {ioc_name} is not {'started' if is_start else 'stopped'}")


def quick_is_ioc_down(ioc_name):
    """
    Determine if IOC is up by checking proc serv, cannot be used to make sure a PV has been started, but is
    good enough for checks before attempting to start/stop
    :param ioc_name:  The IOC to check
    :return:  True if IOC is up; False otherwise
    """
    running = g.get_pv(f"CS:PS:{ioc_name}:STATUS", is_local=True)
    return running == "Shutdown"


def is_ioc_up(ioc_name):
    """
    Determine if IOC is up by checking for the existence of its heartbeat PV
    Args:
        ioc_name: IOC to check

    Returns: True if IOC is up; False otherwise
    """
    try:
        heartbeat = g.get_pv(f"CS:IOC:{ioc_name}:DEVIOS:HEARTBEAT", is_local=True)
    except UnableToConnectToPVException:
        return False
    return heartbeat is not None


def wait_for_iocs_to_be_up(ioc_names, seconds_to_wait):
    """
    Wait for a number of iocs to be up by checking for existence of heartbeat PVs for each ioc.

    Args:
        ioc_names: A list of IOC names to wait for.
        seconds_to_wait: The number of seconds to wait for iocs to be up.

    Returns:
        None

    Raises:
        AssertionError: raised when at least one IOC hasn't started.
    """
    start_time = time()
    while time() - start_time < seconds_to_wait:
        if all(is_ioc_up(ioc_name) for ioc_name in ioc_names):
            break
        sleep(1)
    else:
        raise AssertionError(
            f"IOCs: {[ioc_name for ioc_name in ioc_names if not is_ioc_up(ioc_name)]} could not be started."
        )


def wait_for_string_pvs_to_not_be_empty(pvs, seconds_to_wait, is_local=True):
    """
    Wait for a number of string pvs to be non-empty and return their values.
    Raises an assertion error if at least one is not found.

    Args:
        pvs: The pvs to wait and get values for.
        seconds_to_wait: The seconds to wait for pvs.
        is_local: Whether the pvs are local or not.

    Returns:
        A dictionary of values, where the key is the pv and the value is the returned pv value.

    Raises:
        AssertionError: If at least one pv is empty by the end.
    """
    pv_values = {pv: "" for pv in pvs}
    start_time = time()
    while time() - start_time < seconds_to_wait:
        for pv, value in pv_values.items():
            if not value:  # String is falsy if empty
                new_value = g.get_pv(pv, is_local=is_local)
                pv_values[pv] = new_value
        if all(pv_values.values()):
            break
        sleep(1)
    else:
        raise AssertionError(f"{[pv for pv, value in pv_values.items() if not value]} not available")
    return pv_values


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
                except Exception as exception:
                    print(f"\nTest failed (attempt {attempt + 1} of {max_times}). Retrying...")
                    err = exception
            if err is not None:
                raise err

        return wrapper

    return decorator


def check_block_exists(block_name):
    """
    Check that the given block name is in the current blocks.

    Args:
        block_name (str): The name of the block to check for

    Returns:
        bool: true if block is in current blocks, false if not.
    """
    blocks = g.get_blocks()
    return block_name in blocks


def retry_assert(retry_limit: int, func: Callable[[], None]):
    """
    Take a function (func) that makes assertions. Try to call the function and catch any AssertionErrors if raised.
    Repeat this until either the function does not raise an AssertionError or the retry_limit is reached.
    If the retry limit is reach reraise the last error.

    Args:
        retry_limit (int): The limit of times to retry.
        func (Callable): A callable that makes assertions.

    Raises:
        AssertionError: If the function fails in every retry.
    """
    error = None
    for _ in range(retry_limit):
        try:
            func()
            break
        except AssertionError as new_error:
            error = new_error
        sleep(1)
    else:
        raise error


def get_execution_time(method):
    """
    Takes a method and calculates its execution time.
    Useful for tests that are time sensitive
    (e.g. testing get_time_since_start, begin() and end() are adding extra time
    to the time elapsed from the point of start)

    :param method: the method which execution time is being calculated
    :return: execution time of the method
    """
    start = timeit.default_timer()
    method()
    stop = timeit.default_timer()

    execution_time = stop - start

    return execution_time
