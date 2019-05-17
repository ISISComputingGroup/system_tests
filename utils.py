"""
Utilities for testing
"""
import genie as g


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
        if is_a_start:
            g.set_pv("CS:PS:{}:START".format(ioc_name), 1, is_local=True)
        else:
            g.set_pv("CS:PS:{}:STOP".format(ioc_name), 1, is_local=True)

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
        timeout:
        is_start:
        ioc_name:

    Returns:

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
    Determin if IOC is up by checking for the existence of its heartbeat PV
    Args:
        ioc_name: IOC to check

    Returns: True if IOC is up; False otherwise

    """
    return g.get_pv("AS:{}:SR_heartbeat".format(ioc_name), is_local=True) is not None
