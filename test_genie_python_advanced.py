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
        g.set_pv("CS:MANAGER", "Yes", True, True)  # Check that the get_manager_mode() function works as expected.
        assert g.adv.get_manager_mode()

        g.set_pv("CS:MANAGER", "No", True, True)
        assert not g.adv.get_manager_mode()

    def test_GIVEN_no_manager_mode_WHEN_setting_motor_position_THEN_exception_is_raised(self):
        g.set_pv("CS:MANAGER", "No", True, True)

        with self.assertRaises(RuntimeError):
            # Check that the user will not be allowed to change the motor position without being in manager mode
            g.adv.set_motor_position("MTR0101", 1000)

    def test_GIVEN_invalid_motor_name_WHEN_setting_motor_position_THEN_exception_is_raised(self):
        g.set_pv("CS:MANAGER", "Yes", True, True)

        with self.assertRaises(ValueError):
            # Check that the set_motor_position will only accept motors it recognises
            g.adv.set_motor_position("INVALID_MOTOR_NAME", 1000)

    def test_GIVEN_manager_mode_and_valid_motor_name_WHEN_setting_motor_position_THEN_no_exception_raised(self):
        params = [(1000, "Frozen"), (-1000, "Frozen"), (1000, "Variable"), (-1000, "Variable")]
        g.set_pv("CS:MANAGER", "Yes", True, True)

        for motor_value, foff_value in params:

            g.set_pv(g.my_pv_prefix + "MOT:MTR0101.FOFF", foff_value, True, True)

            g.adv.set_motor_position("MTR0101", motor_value)

            assert motor_value == g.get_pv(g.my_pv_prefix + "MOT:MTR0101.VAL")
            # Assert that the motor position changes after calling set_motor_position()
            assert g.get_pv(g.my_pv_prefix + "MOT:MTR0101.SET", True) == "Use"
            # Check that MOT:MTR0101.SET is in Use mode after calling set_motor_position()
            assert g.get_pv(g.my_pv_prefix + "MOT:MTR0101.FOFF") == foff_value
            # Check that MOT:MTR0101.FFOF is in the same mode before and after calling set_motor_position()

    def test_GIVEN_motor_is_moving_WHEN_setting_motor_position_THEN_exception_raised(self):
        g.set_pv("CS:MANAGER", "Yes", True, True)
        g.set_pv(g.my_pv_prefix + "MOT:MTR0101.SET", 0, True)  # Use mode

        g.set_pv(g.my_pv_prefix + "MOT:MTR0101.VAL", 30000.0, False)  # Set position so that motor begins moving

        with self.assertRaises(RuntimeError) as e:
            print(e)
            g.adv.set_motor_position("MTR0101", 1000)  # Check that it throws as exception as it is moving

    def tearDown(self):
        g.set_pv(g.my_pv_prefix + "MOT:MTR0101.STOP", 1, True)  # Make sure motor is not moving
        g.set_pv(g.my_pv_prefix + "MOT:MTR0101.SET", 1, True)  # Set mode
        g.set_pv(g.my_pv_prefix + "MOT:MTR0101.VAL", 0.0, True)  # Motor is repositioned
        g.set_pv("CS:MANAGER", "No", True, True)  # Make sure not in manager mode
        set_genie_python_raises_exceptions(False)
