
from hamcrest import *
import unittest

from utilities.utilities import load_config_if_not_already_loaded, g

SIMPLE_CONFIG_NAME = "rcptt_simple"


class TestBlockUtils(unittest.TestCase):

    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)

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
