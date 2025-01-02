import os
import threading
import time
import unittest

from genie_python.channel_access_exceptions import (
    UnableToConnectToPVException,
    WriteAccessException,
)
from genie_python.genie_script_checker import ScriptChecker
from genie_python.testing_utils.script_checker import CreateTempScriptAndReturnErrors
from hamcrest import assert_that, is_, is_in

from utilities.utilities import (
    check_block_exists,
    g,  # type: ignore
    load_config_if_not_already_loaded,
    retry_on_failure,
    set_genie_python_raises_exceptions,
)

TIMEOUT = 30
SIMPLE_CONFIG_NAME = "rcptt_simple"


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

        # all tests that interact with anything but genie should try to load a config to ensure that the configurations
        # in the tests are not broken, e.g. by a schema update
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)

    @retry_on_failure(3)
    def test_GIVE_config_with_mbbi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(
        self,
    ):
        mbbi_block_name = "MBBI_BLOCK"
        assert_that(mbbi_block_name, is_in(g.get_blocks()))

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.cset(mbbi_block_name, expected_val)
            g.waitfor_block(mbbi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(mbbi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_mbbi_block_WHEN_set_and_get_block_value_using_kwarg_syntax_THEN_value_is_set_and_read(
        self,
    ):
        mbbi_block_name = "MBBI_BLOCK"
        assert_that(mbbi_block_name, is_in(g.get_blocks()))

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.cset(**{mbbi_block_name: expected_val})
            g.waitfor_block(mbbi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(mbbi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_bi_block_WHEN_set_and_get_block_value_THEN_value_is_set_and_read(
        self,
    ):
        bi_block_name = "BI_BLOCK"
        assert_that(bi_block_name, is_in(g.get_blocks()))

        for expected_val in ["NO", "YES"]:
            g.cset(bi_block_name, expected_val)
            g.waitfor_block(bi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(bi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_bi_block_WHEN_set_and_get_block_value_using_kwarg_syntax_THEN_value_is_set_and_read(
        self,
    ):
        bi_block_name = "BI_BLOCK"
        assert_that(bi_block_name, is_in(g.get_blocks()))

        for expected_val in ["NO", "YES"]:
            g.cset(**{bi_block_name: expected_val})
            g.waitfor_block(bi_block_name, value=expected_val, maxwait=TIMEOUT)
            assert_that(g.cget(bi_block_name)["value"], is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_mbbi_pv_WHEN_set_and_get_pv_value_with_not_is_local_THEN_value_is_set_and_read(
        self,
    ):
        mbbi_pv_name = g.prefix_pv_name("SIMPLE:MBBI")

        for expected_val in ["CHEERFUL", "HAPPY"]:
            g.set_pv(mbbi_pv_name, expected_val, wait=True)
            assert_that(g.get_pv(mbbi_pv_name), is_(expected_val))

    @retry_on_failure(3)
    def test_GIVE_config_with_bi_pv_WHEN_set_and_get_pv_value_with_is_local_THEN_value_is_set_and_read(
        self,
    ):
        bi_pv_name = "SIMPLE:BI"

        for expected_val in ["NO", "YES"]:
            g.set_pv(bi_pv_name, expected_val, is_local=True, wait=True)
            assert_that(g.get_pv(bi_pv_name, is_local=True), is_(expected_val))


class TestWaitforPV(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)
        set_genie_python_raises_exceptions(True)

    def tearDown(self):
        set_genie_python_raises_exceptions(False)

    def test_GIVEN_pv_does_not_exist_WHEN_waiting_for_pv_THEN_error_is_returned(self):
        pv_name = g.prefix_pv_name("NONSENSE:PV")

        with self.assertRaises(UnableToConnectToPVException):
            g.adv.wait_for_pv(pv_name, 0, maxwait=10)

    def test_GIVEN_pv_reaches_correct_value_WHEN_waiting_for_pv_THEN_waitfor_returns_before_timeout(
        self,
    ):
        pv_name = g.prefix_pv_name("SIMPLE:VALUE1:SP")
        g.set_pv(pv_name, 0, wait=True)
        wait_before = 1
        wait_after = 5
        max_wait = (wait_before + wait_after) * 2
        value_to_wait_for = 2

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(wait_before, wait_after, pv_name, value_to_wait_for),
        )
        set_pv_thread.start()
        g.adv.wait_for_pv(pv_name, value_to_wait_for, maxwait=max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because pv has changed",
        )

    def test_GIVEN_pv_change_but_not_to_correct_value_WHEN_waiting_for_pv_THEN_timeout(
        self,
    ):
        pv_name = g.prefix_pv_name("SIMPLE:VALUE1:SP")
        g.set_pv(pv_name, 0, wait=True)
        value_to_wait_for = 2
        wrong_value = 3
        wait_before = 1
        wait_after = 5
        max_wait = (wait_before + wait_after) * 2

        set_pv_thread = threading.Thread(
            target=delayed_set_pv, args=(wait_before, wait_after, pv_name, wrong_value)
        )
        set_pv_thread.start()
        g.adv.wait_for_pv(pv_name, value_to_wait_for, maxwait=max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(False),
            "SetPV thread should have finished before maxwait has passed.",
        )


class TestDispSetOnBlock(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)
        set_genie_python_raises_exceptions(True)
        self._pv_name = g.prefix_pv_name("SIMPLE:VALUE1:SP")

    def tearDown(self):
        g.set_pv(self._pv_name + ".DISP", 0)

    def test_GIVEN_disp_set_on_block_WHEN_setting_pv_value_THEN_exception_is_raised(
        self,
    ):
        g.set_pv(self._pv_name + ".DISP", 1)
        with self.assertRaises(WriteAccessException):
            g.set_pv(self._pv_name, "test")

    def test_GIVEN_disp_not_set_on_block_WHEN_setting_pv_value_THEN_pv_value_is_set(
        self,
    ):
        g.set_pv(self._pv_name + ".DISP", 0)
        test_value = 123
        time.sleep(2)
        g.set_pv(self._pv_name, test_value)
        assert g.get_pv(self._pv_name) == test_value

    def test_GIVEN_field_WHEN_setting_pv_value_THEN_field_is_set_and_disp_is_not_checked(
        self,
    ):
        test_value = "m"
        g.set_pv(self._pv_name + ".EGU", test_value)
        assert g.get_pv(self._pv_name + ".EGU") == test_value

    def test_GIVEN_disp_is_set_on_pv_WHEN_setting_field_value_THEN_exception_is_raised(
        self,
    ):
        g.set_pv(self._pv_name + ".DISP", 1)
        with self.assertRaises(WriteAccessException):
            g.set_pv(self._pv_name + ".EGU", "test")


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

    def test_GIVEN_waiting_for_exact_value_on_block_WHEN_block_reaches_value_THEN_waitfor_completes(
        self,
    ):
        value_to_wait_for = 2

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, value_to_wait_for),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, value=value_to_wait_for, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because block has changed to correct value",
        )

    def test_GIVEN_waiting_for_exact_value_on_block_WHEN_block_wrong_value_THEN_timeout(
        self,
    ):
        value_to_wait_for = 2
        wrong_value = 3

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, wrong_value),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, value=value_to_wait_for, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(False),
            "Waitfor should have timed out because value is wrong",
        )

    def test_GIVEN_waiting_for_value_in_limits_on_block_WHEN_block_enters_range_THEN_waitfor_completes(
        self,
    ):
        value_in_range = 2
        low_limit = 1
        high_limit = 3

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, value_in_range),
        )
        set_pv_thread.start()
        g.waitfor_block(
            block=self.block_name,
            lowlimit=low_limit,
            highlimit=high_limit,
            maxwait=self.max_wait,
        )

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because block has changed to value in range",
        )

    def test_GIVEN_waiting_for_value_in_limits_on_block_WHEN_block_wrong_value_THEN_timeout(
        self,
    ):
        wrong_value = 4
        low_limit = 1
        high_limit = 3

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, wrong_value),
        )
        set_pv_thread.start()
        g.waitfor_block(
            block=self.block_name,
            lowlimit=low_limit,
            highlimit=high_limit,
            maxwait=self.max_wait,
        )

        assert_that(
            set_pv_thread.is_alive(),
            is_(False),
            "Waitfor should have timed out because value is not in range",
        )

    def test_GIVEN_waiting_for_value_below_high_limit_on_block_WHEN_block_enters_range_THEN_waitfor_completes(
        self,
    ):
        value_in_range = -2
        high_limit = -1

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, value_in_range),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because block has changed to value below limit",
        )

    def test_GIVEN_waiting_for_value_below_high_limit_on_block_WHEN_block_above_limit_THEN_timeout(
        self,
    ):
        wrong_value = 1
        high_limit = -1

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, wrong_value),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(False),
            "Waitfor should have timed out because block above limit",
        )

    def test_GIVEN_waiting_for_value_above_low_limit_on_block_WHEN_block_enters_range_THEN_waitfor_completes(
        self,
    ):
        value_in_range = 3
        low_limit = 2

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, value_in_range),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because block has changed to value above limit",
        )

    def test_GIVEN_waiting_for_value_above_low_limit_on_block_WHEN_block_below_limit_THEN_timeout(
        self,
    ):
        wrong_value = 1
        low_limit = 2

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, wrong_value),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(False),
            "Waitfor should have timed out because block below limit",
        )

    # Testing cases where the block is directly on the limit - the highlimit is a maximum value so waitfor should complete

    def test_GIVEN_waiting_for_value_below_high_limit_on_block_WHEN_block_reaches_limit_boundary_THEN_waitfor_completes(
        self,
    ):
        high_limit = -1

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, high_limit),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, highlimit=high_limit, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because block has changed to the limit",
        )

    def test_GIVEN_waiting_for_value_above_low_limit_on_block_WHEN_block_reaches_limit_boundary_THEN_waitfor_completes(
        self,
    ):
        low_limit = 2

        set_pv_thread = threading.Thread(
            target=delayed_set_pv,
            args=(self.wait_before, self.wait_after, self.pv_name, low_limit),
        )
        set_pv_thread.start()
        g.waitfor_block(block=self.block_name, lowlimit=low_limit, maxwait=self.max_wait)

        assert_that(
            set_pv_thread.is_alive(),
            is_(True),
            "Waitfor should have finished because block has changed to the limit",
        )


class TestRunControl(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)
        self.block_name = "FLOAT_BLOCK"
        assert_that(check_block_exists(self.block_name), is_(True))
        g.cset(self.block_name, 0)
        g.cset(self.block_name, runcontrol=False)
        self._waitfor_runstate("SETUP")

    def tearDown(self):
        g.abort()

    def test_GIVEN_out_of_range_block_WHEN_start_run_THEN_dae_waiting(self):
        g.cset(self.block_name, runcontrol=True, lowlimit=1, highlimit=2)
        g.begin()
        self._waitfor_runstate("WAITING")

    def test_GIVEN_dae_waiting_WHEN_block_goes_into_range_THEN_dae_running(self):
        g.begin()
        self._waitfor_runstate("RUNNING")
        g.cset(self.block_name, runcontrol=True, lowlimit=1, highlimit=2)
        self._waitfor_runstate("WAITING")
        g.cset(self.block_name, runcontrol=True, lowlimit=-1, highlimit=1)
        self._waitfor_runstate("RUNNING")

    def test_GIVEN_dae_waiting_WHEN_runcontrol_disabled_THEN_dae_running(self):
        g.begin()
        self._waitfor_runstate("RUNNING")
        g.cset(self.block_name, runcontrol=True, lowlimit=1, highlimit=2)
        self._waitfor_runstate("WAITING")
        g.cset(self.block_name, runcontrol=False)
        self._waitfor_runstate("RUNNING")

    def _waitfor_runstate(self, state):
        g.waitfor_runstate(state, TIMEOUT)
        self.assertEqual(g.get_runstate(), state)


class TestAlerts(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(SIMPLE_CONFIG_NAME)
        self.block_name = "FLOAT_BLOCK"
        assert_that(check_block_exists(self.block_name), is_(True))
        g.cset(self.block_name, 0)
        g.alerts.enable(self.block_name, False)
        self._waitfor_runstate("SETUP")

    def tearDown(self):
        g.abort()

    def test_GIVEN_alert_range_WHEN_parameter_out_of_range_THEN_alert_sent(self):
        # setup
        g.begin()
        self._waitfor_runstate("RUNNING")
        mobiles_pv = g.prefix_pv_name("CS:AC:ALERTS:MOBILES:SP")
        emails_pv = g.prefix_pv_name("CS:AC:ALERTS:EMAILS:SP")
        pw_pv = g.prefix_pv_name("CS:AC:ALERTS:PW:SP")
        inst_pv = g.prefix_pv_name("CS:AC:ALERTS:INST:SP")
        url_pv = g.prefix_pv_name("CS:AC:ALERTS:URL:SP")
        out_pv = g.prefix_pv_name("CS:AC:OUT:CNT")
        send_cnt_pv = g.prefix_pv_name("CS:AC:ALERTS:_SENDCNT")
        assert_that(g.get_pv(out_pv), is_(0))
        assert_that(g.get_pv(send_cnt_pv), is_(0))
        g.set_pv(pw_pv, "dummy")
        g.set_pv(inst_pv, "TESTINST")
        g.set_pv(
            url_pv, "test"
        )  # this needs to be "test" so that webget knows not to send a message

        # check setting mobiles and emails
        g.alerts.set_sms(["123456", "789"])
        g.alerts.set_email(["a@b", "c@d"])
        time.sleep(5)
        assert_that(g.get_pv(mobiles_pv), "123456;789")
        assert_that(g.get_pv(emails_pv), "a@b;c@d")

        # enable alert and check still in range
        g.alerts.set_range(self.block_name, -10.0, 20.0, delay_out=1, delay_in=2)
        g.alerts.enable(self.block_name, True)
        time.sleep(5)
        assert_that(g.get_pv(out_pv), is_(0))
        assert_that(g.get_pv(send_cnt_pv), is_(0))

        # now make out of range
        g.alerts.set_range(self.block_name, 10.0, 20.0)
        time.sleep(5)
        assert_that(g.get_pv(out_pv), is_(1))
        assert_that(g.get_pv(send_cnt_pv), is_(1))

        # now make in range
        g.alerts.set_range(self.block_name, -10.0, 20.0)
        time.sleep(5)
        assert_that(g.get_pv(out_pv), is_(0))
        assert_that(g.get_pv(send_cnt_pv), is_(2))

        # now disable alerts, but put out of range
        g.alerts.enable(self.block_name, False)
        g.alerts.set_range(self.block_name, 10.0, 20.0, False)
        time.sleep(5)
        assert_that(g.get_pv(out_pv), is_(0))
        assert_that(g.get_pv(send_cnt_pv), is_(2))

        # check values
        vals = g.alerts._dump(self.block_name)
        assert_that(vals["emails"], is_(["a@b", "c@d"]))
        assert_that(vals["mobiles"], is_(["123456", "789"]))
        assert_that(vals["lowlimit"], is_(10.0))
        assert_that(vals["highlimit"], is_(20.0))
        assert_that(vals["delay_in"], is_(2.0))
        assert_that(vals["delay_out"], is_(1.0))
        assert_that(vals["enabled"], is_("NO"))

    def test_GIVEN_details_WHEN_message_specified_THEN_alert_message_sent(self):
        url_pv = g.prefix_pv_name("CS:AC:ALERTS:URL:SP")
        message_pv = g.prefix_pv_name("CS:AC:ALERTS:MESSAGE:SP")
        send_cnt_pv = g.prefix_pv_name("CS:AC:ALERTS:_SENDCNT")
        old_send_cnt = g.get_pv(send_cnt_pv)
        g.set_pv(
            url_pv, "test"
        )  # this needs to be "test" so that webget knows not to send a message

        g.alerts.send("test message")
        time.sleep(5)
        assert_that(g.get_pv(send_cnt_pv), is_(old_send_cnt + 1))
        assert_that(g.get_pv(message_pv), is_("test message"))

    def _waitfor_runstate(self, state):
        g.waitfor_runstate(state, TIMEOUT)
        self.assertEqual(g.get_runstate(), state)


class SystemTestScriptChecker(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)

    # Test that functions from C:\Instrument\scripts can be accessed and reports pyright reports error if used incorrectly
    # "" C:\Instrument\Settings\config\NDW2452\Python\inst ""
    # Using system tests as doing it from a unit tests perspective would mean depending on the nature of the local machine they may not have the modules
    # to make these tests pass

    def test_GIVEN_invalid_inst_script_from_settings_area_WHEN_calling_script_checker_THEN_pyright_throws_error(
        self,
    ):
        path_to_inst = os.path.join(
            "c:\\",
            "instrument",
            "settings",
            "config",
            g.adv.get_instrument_full_name(),
            "Python",
            "inst",
        )
        temp_file_name = "temp_file.py"

        script_lines_1 = "def sample_changer_scloop(a: int, b: str):\n\tpass\n"

        script_lines_2 = ["from inst import temp_file\n" "temp_file.sample_changer_scloop('a',2)\n"]

        with open(os.path.join(path_to_inst, temp_file_name), "w") as temp_file:
            temp_file.write(script_lines_1)
            temp_file.flush()

            with CreateTempScriptAndReturnErrors(
                ScriptChecker(), g.adv.get_instrument_full_name(), script_lines_2
            ) as errors_2:
                self.assertTrue(errors_2[0].startswith("E: 2: Argument of type"))

        os.unlink(temp_file.name)

    def test_GIVEN_invalid_inst_script_from_general_WHEN_calling_script_checker_THEN_pyright_throws_error(
        self,
    ):
        script_lines = [
            "from technique.muon.muon_begin_end import g\n",
            "def test_inst():\n",
            "   g.begin(1.2, 'b', 'a', 'a', 'a')\n",
        ]

        with CreateTempScriptAndReturnErrors(
            ScriptChecker(), g.adv.get_instrument_full_name(), script_lines
        ) as errors:
            self.assertTrue(errors[0].startswith("E: 3: Argument of type"))
