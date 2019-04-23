import functools
import os
import subprocess

import sys
from hamcrest import *
import unittest

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
    def test_GIVE_config_with_bi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(self):
        bi_block_name = "BI_BLOCK"
        assert_that(bi_block_name, is_in(g.get_blocks()))

        for expected_val in ["NO", "YES"]:
            g.cset(bi_block_name, expected_val)
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

    def test_GIVEN_multithreaded_cget_THEN_works(self):
        # Spawns 100 threads which concurrently do cgets.
        # In some versions of IBEX, this has crashed with a segmentation fault.
        multithreaded_cget = """
import threading
from genie_python import genie as g
from genie_python.genie_startup import *
g.set_instrument(None)
    
threads = [threading.Thread(target=g.cget, args=("abc",)) for _ in range(100)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
        """

        filename = "temp_test_multithreaded_cget.py"
        try:
            with open(filename, "w") as f:
                f.write(multithreaded_cget)

            return_code = subprocess.call("{} {}".format(sys.executable, filename))
            self.assertEqual(return_code, 0)
        finally:
            os.remove(filename)
