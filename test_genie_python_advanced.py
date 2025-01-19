import unittest

from parameterized import parameterized as param

from utilities.utilities import (
    g,
    load_config_if_not_already_loaded,
    set_genie_python_raises_exceptions,
)

ADV_CONFIG_NAME = "advanced"


class TestAdvancedMotorControls(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(ADV_CONFIG_NAME)
        set_genie_python_raises_exceptions(True)

    @param.expand([True, False])
    def test_GIVEN_manager_mode_WHEN_calling_get_manager_mode_THEN_returns_true(self, manager_mode):
        # Checks that the get_manager_mode() function works as expected.
        g.set_pv("CS:MANAGER", manager_mode, wait=True, is_local=True)
        self.assertTrue(g.adv.get_manager_mode() == manager_mode)

    def test_GIVEN_no_manager_mode_WHEN_setting_motor_position_THEN_exception_is_raised(self):
        # Checks that the user will not be allowed to change the motor position without being in manager mode
        g.set_pv("CS:MANAGER", "No", wait=True, is_local=True)

        with self.assertRaises(RuntimeError):
            g.adv.redefine_motor_position("MTR0101", 1000)

    def test_GIVEN_invalid_motor_name_WHEN_setting_motor_position_THEN_exception_is_raised(self):
        # Checks that the set_motor_position function will only accept motors it recognises
        g.set_pv("CS:MANAGER", "Yes", wait=True, is_local=True)

        with self.assertRaises(ValueError):
            g.adv.redefine_motor_position("INVALID_MOTOR_NAME", 1000)

    def test_GIVEN_foff_is_variable_and_set_is_use_WHEN_setting_motor_position_THEN_foff_and_set_change_before_and_after(
        self,
    ):
        # Before changing motor position, check that SET mode is on Set
        # and FOFF is on Frozen

        foff_value = "Variable"
        set_value = "Use"

        g.set_pv("MOT:MTR0101.FOFF", foff_value, wait=True, is_local=True)  # Frozen mode
        g.set_pv("MOT:MTR0101.SET", set_value, wait=True, is_local=True)  # Use mode

        with g.adv.motor_in_set_mode(g.my_pv_prefix + "MOT:MTR0101"):
            self.assertTrue(g.get_pv("MOT:MTR0101.SET", to_string=True, is_local=True) == "Set")
            self.assertTrue(g.get_pv("MOT:MTR0101.FOFF", to_string=True, is_local=True) == "Frozen")

        self.assertTrue(g.get_pv("MOT:MTR0101.SET", to_string=True, is_local=True) == "Use")
        # Check that MOT:MTR0101.SET is in Use mode after calling set_motor_position()
        self.assertTrue(g.get_pv("MOT:MTR0101.FOFF", to_string=True, is_local=True) == foff_value)
        # Check that MOT:MTR0101.FFOF is in the same mode before and after calling set_motor_position()

    @param.expand([1000, -1000])
    def test_GIVEN_manager_mode_and_valid_motor_name_WHEN_setting_motor_position_THEN_motor_position_set(
        self, motor_value
    ):
        # Checks that for a combination of valid parameters there are no exceptions
        g.set_pv("CS:MANAGER", "Yes", wait=True, is_local=True)

        g.adv.redefine_motor_position("MTR0101", motor_value)

        self.assertTrue(motor_value == g.get_pv("MOT:MTR0101.VAL", to_string=False, is_local=True))
        # Assert that the motor position changes after calling set_motor_position()

    def test_GIVEN_motor_is_moving_WHEN_setting_motor_position_THEN_exception_raised(self):
        # Checks that the motor is not allowed to be repositioned while it is already moving
        g.set_pv("CS:MANAGER", "Yes", wait=True, is_local=True)
        g.set_pv("MOT:MTR0101.SET", 0, wait=True, is_local=True)  # Use mode

        g.set_pv(
            "MOT:MTR0101.VAL", 30000.0, wait=False, is_local=True
        )  # Set position so that motor begins moving

        with self.assertRaises(RuntimeError):
            g.adv.redefine_motor_position(
                "MTR0101", 1000
            )  # Check that it throws as exception as it is moving

    def test_GIVEN_invalid_pv_WHEN_calling_motor_in_set_mode_THEN_exception_raised(self):
        # Checks that the function motor_in_set_mode will not accept an invalid pv
        with self.assertRaises(ValueError):
            with g.adv.motor_in_set_mode(g.my_pv_prefix + "MOT:INVALID_MOTOR_NAME"):
                None

    def test_GIVEN_valid_pv_but_not_a_motor_pv_WHEN_calling_motor_in_set_mode_THEN_exception_raised(
        self,
    ):
        # Checks that the function motor_in_set_mode will not accept a valid pv that does not point to a motor
        with self.assertRaises(ValueError):
            with g.adv.motor_in_set_mode(g.my_pv_prefix + "CS:MANAGER"):
                None

    def tearDown(self):
        g.set_pv("MOT:MTR0101.STOP", 1, wait=True, is_local=True)  # Make sure motor is not moving
        g.set_pv("MOT:MTR0101.SET", 1, wait=True, is_local=True)  # Set mode
        g.set_pv("MOT:MTR0101.VAL", 0.0, wait=True, is_local=True)  # Motor is repositioned
        g.set_pv("CS:MANAGER", "No", wait=True, is_local=True)  # Make sure not in manager mode
        set_genie_python_raises_exceptions(False)
