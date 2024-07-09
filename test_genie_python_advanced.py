import unittest

from utilities.utilities import load_config_if_not_already_loaded, g, \
    set_genie_python_raises_exceptions

ADV_CONFIG_NAME = "advanced"


class TestAdvancedMotorControls(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        load_config_if_not_already_loaded(ADV_CONFIG_NAME)
        set_genie_python_raises_exceptions(True)

    def test_GIVEN_manager_mode_WHEN_calling_get_manager_mode_THEN_returns_true(self):
        # Checks that the get_manager_mode() function works as expected.
        g.set_pv("CS:MANAGER", "Yes", True, True)
        assert g.adv.get_manager_mode()

        g.set_pv("CS:MANAGER", "No", True, True)
        assert not g.adv.get_manager_mode()

    def test_GIVEN_no_manager_mode_WHEN_setting_motor_position_THEN_exception_is_raised(self):
        # Checks that the user will not be allowed to change the motor position without being in manager mode
        g.set_pv("CS:MANAGER", "No", True, True)

        with self.assertRaises(RuntimeError):
            g.adv.set_motor_position("MTR0101", 1000)

    def test_GIVEN_invalid_motor_name_WHEN_setting_motor_position_THEN_exception_is_raised(self):
        # Checks that the set_motor_position function will only accept motors it recognises
        g.set_pv("CS:MANAGER", "Yes", True, True)

        with self.assertRaises(ValueError):
            g.adv.set_motor_position("INVALID_MOTOR_NAME", 1000)

    def test_set_and_foff_change_before_after_setting_motor_position(self):
        # Before changing motor position, check that SET mode is on Set
        # and FOFF is on Frozen

        pv_name = g.my_pv_prefix + "MOT:MTR0101"
        foff_value = "Variable"

        g.set_pv(pv_name + ".FOFF", foff_value, True, True)

        with g.adv.motor_in_set_mode(pv_name):
            assert g.get_pv(pv_name + ".SET", True) == "Set"
            assert g.get_pv(pv_name + ".FOFF", True) == "Frozen"

        assert g.get_pv(pv_name + ".SET", True) == "Use"
        # Check that MOT:MTR0101.SET is in Use mode after calling set_motor_position()
        assert g.get_pv(pv_name + ".FOFF") == foff_value
        # Check that MOT:MTR0101.FFOF is in the same mode before and after calling set_motor_position()

    def test_GIVEN_manager_mode_and_valid_motor_name_WHEN_setting_motor_position_THEN_motor_position_set(self):
        # Checks that for a combination of valid parameters there are no exceptions
        params = [1000, -1000]
        g.set_pv("CS:MANAGER", "Yes", True, True)

        pv_name = g.my_pv_prefix + "MOT:MTR0101"

        for motor_value in params:

            g.adv.set_motor_position("MTR0101", motor_value)

            assert motor_value == g.get_pv(pv_name + ".VAL")
            # Assert that the motor position changes after calling set_motor_position()

    def test_GIVEN_motor_is_moving_WHEN_setting_motor_position_THEN_exception_raised(self):
        pv_name = g.my_pv_prefix + "MOT:MTR0101"
        g.set_pv("CS:MANAGER", "Yes", True, True)
        g.set_pv(pv_name + ".SET", 0, True)  # Use mode

        g.set_pv(pv_name + ".VAL", 30000.0, False)  # Set position so that motor begins moving

        with self.assertRaises(RuntimeError) as e:
            print(e)
            g.adv.set_motor_position("MTR0101", 1000)  # Check that it throws as exception as it is moving

    def tearDown(self):
        pv_name = g.my_pv_prefix + "MOT:MTR0101"
        g.set_pv(pv_name + ".STOP", 1, True)  # Make sure motor is not moving
        g.set_pv(pv_name + ".SET", 1, True)  # Set mode
        g.set_pv(pv_name + ".VAL", 0.0, True)  # Motor is repositioned
        g.set_pv("CS:MANAGER", "No", True, True)  # Make sure not in manager mode
        set_genie_python_raises_exceptions(False)
