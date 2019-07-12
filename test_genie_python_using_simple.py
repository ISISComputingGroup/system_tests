import functools

from hamcrest import *

import threading
import unittest
import time

from genie_python.channel_access_exceptions import UnableToConnectToPVException
from utilities.utilities import load_config_if_not_already_loaded, check_block_exists, g


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
    time.sleep(wait_before_set)
    g.set_pv(pv, value_to_set)
    time.sleep(wait_after_set)


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
        g.set_pv(pv_name, 0, wait=True)
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
        g.set_pv(pv_name, 0, wait=True)
        value_to_wait_for = 2
        wrong_value = 3
        wait_before = 1
        wait_after = 5
        max_wait = (wait_before + wait_after) * 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(wait_before, wait_after, pv_name, wrong_value))
        set_pv_thread.start()
        g.adv.wait_for_pv(pv_name, value_to_wait_for, maxwait=max_wait)

        assert_that(set_pv_thread.is_alive(), is_(False), "SetPV thread should have finished before maxwait has passed.")

class TestWaitforBlock(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)
        self.pv_name = g.prefix_pv_name("SIMPLE:VALUE1:SP")
        self.block_name = "FLOAT_BLOCK"
        self.wait_before = 1
        self.wait_after = 2
        self.max_wait = (self.wait_before + self.wait_after) * 2
        g.cset(self.block_name, 0)
        assert_that(check_block_exists(self.block_name), is_(True))

    def test_GIVEN_waiting_for_exact_value_on_block_WHEN_block_reaches_value_THEN_waitfor_completes(self):
        value_to_wait_for = 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, value_to_wait_for))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, value=value_to_wait_for, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because block has changed to correct value")

    def test_GIVEN_waiting_for_exact_value_on_block_WHEN_block_wrong_value_THEN_timeout(self):
        value_to_wait_for = 2
        wrong_value = 3

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, wrong_value))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, value=value_to_wait_for, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(False), "Waitfor should have timed out because value is wrong")

    def test_GIVEN_waiting_for_value_in_limits_on_block_WHEN_block_enters_range_THEN_waitfor_completes(self):
        value_in_range = 2
        low_limit = 1
        high_limit = 3

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, value_in_range))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because block has changed to value in range")

    def test_GIVEN_waiting_for_value_in_limits_on_block_WHEN_block_wrong_value_THEN_timeout(self):
        wrong_value = 4
        low_limit = 1
        high_limit = 3

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, wrong_value))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(False), "Waitfor should have timed out because value is not in range")

    def test_GIVEN_waiting_for_value_below_high_limit_on_block_WHEN_block_enters_range_THEN_waitfor_completes(self):
        value_in_range = -2
        high_limit = -1

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, value_in_range))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because block has changed to value below limit")

    def test_GIVEN_waiting_for_value_below_high_limit_on_block_WHEN_block_above_limit_THEN_timeout(self):
        wrong_value = 1
        high_limit = -1

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, wrong_value))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(False), "Waitfor should have timed out because block above limit")

    def test_GIVEN_waiting_for_value_above_low_limit_on_block_WHEN_block_enters_range_THEN_waitfor_completes(self):
        value_in_range = 3
        low_limit = 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, value_in_range))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because block has changed to value above limit")

    def test_GIVEN_waiting_for_value_above_low_limit_on_block_WHEN_block_below_limit_THEN_timeout(self):
        wrong_value = 1
        low_limit = 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, wrong_value))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(False), "Waitfor should have timed out because block below limit")

    # Testing cases where the block is directly on the limit - the highlimit is a maximum value so waitfor should complete

    def test_GIVEN_waiting_for_value_below_high_limit_on_block_WHEN_block_reaches_limit_boundary_THEN_waitfor_completes(self):
        high_limit = -1

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, high_limit))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because block has changed to the limit")

    def test_GIVEN_waiting_for_value_above_low_limit_on_block_WHEN_block_reaches_limit_boundary_THEN_waitfor_completes(self):
        low_limit = 2

        set_pv_thread = threading.Thread(target=delayed_set_pv, args=(self.wait_before, self.wait_after, self.pv_name, low_limit))
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, maxwait=self.max_wait)

        assert_that(set_pv_thread.is_alive(), is_(True), "Waitfor should have finished because block has changed to the limit")

class TestRunControl(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)
        self.block_name = "FLOAT_BLOCK"
        self.wait_before = 1
        self.wait_after = 2
        self.max_wait = (self.wait_before + self.wait_after) * 2
        assert_that(check_block_exists(self.block_name), is_(True))
        g.cset(self.block_name, 0)
        g.cset(self.block_name, runcontrol=False)
        self.block_pv = g.prefix_pv_name("CS:SB:") + self.block_name
        g.set_pv(self.block_pv + ":AC:ENABLE", 0)
        self._waitfor_runstate("SETUP")

    def tearDown(self):
        g.abort()

    def test_GIVEN_out_of_range_block_WHEN_start_run_THEN_dae_waiting(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")
        g.cset(self.block_name, runcontrol=True, lowlimit=1, highlimit=2)
        g.begin()
        self._waitfor_runstate("WAITING")

    def test_GIVEN_dae_waiting_WHEN_block_goes_into_range_THEN_dae_running(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")
        g.begin()
        self._waitfor_runstate("RUNNING")
        g.cset(self.block_name, runcontrol=True, lowlimit=1, highlimit=2)
        self._waitfor_runstate("WAITING")
        g.cset(self.block_name, runcontrol=True, lowlimit=-1, highlimit=1)
        self._waitfor_runstate("RUNNING")

    def test_GIVEN_dae_waiting_WHEN_runcontrol_disabled_THEN_dae_running(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")
        g.begin()
        self._waitfor_runstate("RUNNING")
        g.cset(self.block_name, runcontrol=True, lowlimit=1, highlimit=2)
        self._waitfor_runstate("WAITING")
        g.cset(self.block_name, runcontrol=False)
        self._waitfor_runstate("RUNNING")

    def test_GIVEN_alert_range_WHEN_parameter_out_of_range_THEN_alert_sent(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")
        g.begin()
        self._waitfor_runstate("RUNNING")
        mobiles_pv = g.prefix_pv_name("CS:AC:ALERTS:MOBILES:SP")
        emails_pv = g.prefix_pv_name("CS:AC:ALERTS:EMAILS:SP")
        pw_pv = g.prefix_pv_name("CS:AC:ALERTS:PW:SP")
        inst_pv = g.prefix_pv_name("CS:AC:ALERTS:INST:SP")
        url_pv = g.prefix_pv_name("CS:AC:ALERTS:URL:SP")
        out_pv = g.prefix_pv_name("CS:AC:OUT:CNT")
        assert_that(g.get_pv(out_pv), is_(0))
        g.set_pv(mobiles_pv, "123456;789")
        g.set_pv(emails_pv, "a@b;c@d")
        g.set_pv(pw_pv, "dummy")
        g.set_pv(inst_pv, "TESTINST")
        g.set_pv(url_pv, "test") # this needs to be "test"
        g.set_pv(self.block_pv + ":AC:LOW", 1)
        g.set_pv(self.block_pv + ":AC:HIGH", 2)
        g.set_pv(self.block_pv + ":AC:ENABLE", 1)
        time.sleep(5)
        assert_that(g.get_pv(out_pv), is_(1))

    def _waitfor_runstate(self, state):
        for _ in range(TIMEOUT):
            if g.get_runstate() == state:
                return
            time.sleep(5)
        self.assertEqual(g.get_runstate(), state)
