import json

from time import sleep

from hamcrest import *
import unittest

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


SIMPLE_CONFIG_NAME = "rcptt_simple"


class TestBlockUtils(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)
        current_config = g.get_pv("CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS", is_local=True)
        assert_that(current_config, is_(not_none()), "Current config, is the server running?")
        self.current_config = json.loads(dehex_and_decompress(current_config))
        if self.current_config["name"] != SIMPLE_CONFIG_NAME:

            g.set_pv("CS:BLOCKSERVER:LOAD_CONFIG", value=compress_and_hex(SIMPLE_CONFIG_NAME), is_local=True)
            status_was_busy = False
            for i in range(60):
                status = g.get_pv("CS:BLOCKSERVER:SERVER_STATUS", is_local=True)
                if status is not None:
                    try:

                        as_json = json.loads(dehex_and_decompress(status))
                        if as_json["status"] == "":
                            if status_was_busy:
                                break
                        else:
                            status_was_busy = True
                    except ValueError:
                        pass
                sleep(1)
                print("Waiting for server: count {}".format(i))

            self.current_config = json.loads(
                dehex_and_decompress(g.get_pv("CS:BLOCKSERVER:GET_CURR_CONFIG_DETAILS", is_local=True)))

        assert_that(self.current_config["name"], is_(SIMPLE_CONFIG_NAME), "Current config name")

    def test_GIVE_config_with_mbbi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(self):
        mbbi_block_name = "MBBI_BLOCK"
        assert_that(mbbi_block_name, is_in(g.get_blocks()))

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.cset(mbbi_block_name, expected_val)
            g.waitfor_block(mbbi_block_name, value=expected_val, maxwait=1)
            assert_that(g.cget(mbbi_block_name)["value"], is_(expected_val))

    def test_GIVE_config_with_bi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(self):
        mbbi_block_name = "BI_BLOCK"
        assert_that(mbbi_block_name, is_in(g.get_blocks()))

        for expected_val in ["NO", "YES"]:
            g.cset(mbbi_block_name, expected_val)
            g.waitfor_block(mbbi_block_name, value=expected_val, maxwait=1)
            assert_that(g.cget(mbbi_block_name)["value"], is_(expected_val))

    def test_GIVE_config_with_mbbi_pv_WHEN_set_and_get_pv_value_THEN_value_is_set_and_read(self):
        mbbi_pv_name = "SIMPLE:MBBI"

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.set_pv(mbbi_pv_name, expected_val, is_local=True, wait=True)
            assert_that(g.get_pv(mbbi_pv_name, is_local=True), is_(expected_val))

    def test_GIVE_config_with_bi_pv_WHEN_set_and_get_pv_value_THEN_value_is_set_and_read(self):
        bi_pv_name = "SIMPLE:BI"

        for expected_val in ["NO", "YES"]:
            g.set_pv(bi_pv_name, expected_val, is_local=True, wait=True)
            assert_that(g.get_pv(bi_pv_name, is_local=True), is_(expected_val))
