import functools

from hamcrest import *

import threading
import unittest

from genie_python.channel_access_exceptions import UnableToConnectToPVException
from utilities.utilities import load_config_if_not_already_loaded, g


TIMEOUT = 30
SIMPLE_CONFIG_NAME = "rcptt_simple"


def retry_on_failure(max_times):
    """
    Decorator that will retry running a test if it failed.
    :param max_times: Maximum number of times to retry running the test
    :return: the decorator
    """
    def decorator(func):
        @functools.wraps(func)
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


def delayed_set_pv(wait_before_set, wait_after_set, pv, value_to_set):
    """
    Sets a PV value with a given wait in seconds before and after.

    Params:
        wait_before_set(int): Number of seconds to wait before setting the PV value
        wait_after_set(int): Number of seconds to wait after setting the PV value
        pv(string): The PV to set
        value_to_set: The value to set on the target PV
    """
    g.waitfor_time(seconds=wait_before_set)
    g.set_pv(pv, value_to_set)
    g.waitfor_time(seconds=wait_after_set)


class TestBlockUtils(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)

    @retry_on_failure(3)
    def test_GIVE_config_with_mbbi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(self):
        mbbi_block_name = "MBBI_BLOCK"
        assert_that(mbbi_block_name, is_in(g.get_blocks()))

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.cset(mbbi_block_name, expected_val)
            g.waitfor_block(mbbi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(mbbi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_mbbi_block_WHEN_set_and_get_block_value_using_kwarg_syntax_THEN_value_is_set_and_read(self):
        mbbi_block_name = "MBBI_BLOCK"
        assert_that(mbbi_block_name, is_in(g.get_blocks()))

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.cset(**{mbbi_block_name: expected_val})
            g.waitfor_block(mbbi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(mbbi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_bi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(self):
        bi_block_name = "BI_BLOCK"
        assert_that(bi_block_name, is_in(g.get_blocks()))

        for expected_val in ["NO", "YES"]:
            g.cset(bi_block_name, expected_val)
            g.waitfor_block(bi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(bi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_bi_block_WHEN_set_and_get_block_value_using_kwarg_syntax_THEN_value_is_set_and_read(self):
        bi_block_name = "BI_BLOCK"
        assert_that(bi_block_name, is_in(g.get_blocks()))

        for expected_val in ["NO", "YES"]:
            g.cset(**{bi_block_name: expected_val})
            g.waitfor_block(bi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(bi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_mbbi_pv_WHEN_set_and_get_pv_value_THEN_value_is_set_and_read(self):
        mbbi_pv_name = "SIMPLE:MBBI"

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.set_pv(mbbi_pv_name, expected_val, is_local=True, wait=True)
            assert_that(g.get_pv(mbbi_pv_name, is_local=True), is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_bi_pv_WHEN_set_and_get_pv_value_THEN_value_is_set_and_read(self):
        bi_pv_name = "SIMPLE:BI"

        for expected_val in ["NO", "YES"]:
            g.set_pv(bi_pv_name, expected_val, is_local=True, wait=True)
            assert_that(g.get_pv(bi_pv_name, is_local=True), is_(expected_val))


class TestWaitforPV(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)

    def test_GIVEN_pv_does_not_exist_WHEN_waiting_for_pv_THEN_error_is_returned(self):
        pv_name = g.prefix_pv_name("NONSENSE:PV")

        with self.assertRaises(UnableToConnectToPVException):
            g.adv.wait_for_pv(pv_name, 0, maxwait=10)

    def test_GIVEN_pv_reaches_correct_value_WHEN_waiting_for_pv_THEN_waitfor_returns_before_timeout(self):
        pv_name = g.prefix_pv_name("SIMPLE:VALUE1:SP")
        g.set_pv(pv_name, 0)
        wait_before = 1
        wait_after = 5
        max_wait = (wait_before + wait_after) * 2
        value_to_wait_for = 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(wait_before, wait_after, pv_name, value_to_wait_for))
        set_pv_thread.start()
        g.adv.wait_for_pv(pv_name, value_to_wait_for, maxwait=max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because pv has changed")

    def test_GIVEN_pv_change_but_not_to_correct_value_WHEN_waiting_for_pv_THEN_timeout(self):
        pv_name = g.prefix_pv_name("SIMPLE:VALUE1:SP")
        g.set_pv(pv_name, 0)
        value_to_wait_for = 2
        wrong_value = 3
        wait_before = 1
        wait_after = 5
        max_wait = (wait_before + wait_after) * 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(wait_before, wait_after, pv_name, wrong_value))
        set_pv_thread.start()
        g.adv.wait_for_pv(pv_name, value_to_wait_for, maxwait=max_wait)

        assert_that(set_pv_thread.is_alive(), is_(False), "SetPV thread should have finished before maxwait has passed.")
