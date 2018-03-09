import unittest
from time import sleep

from utilities.utilities import g


class TestDae(unittest.TestCase):
    """
    Tests to test the DAE commands.
    """

    def setUp(self):
        g.set_instrument(None)

        if g.get_runstate() != "SETUP":
            g.abort()
            g.waitfor_runstate("SETUP")

        if not g.get_dae_simulation_mode():
            g.set_dae_simulation_mode(True)
            self._wait_for_and_assert_dae_simulation_mode(True)

    def test_GIVEN_run_state_is_running_WHEN_attempt_to_change_simulation_mode_THEN_error(self):
        g.begin()
        for _ in range(10):
            if g.get_runstate() == "RUNNING":
                break
        else:
            self.fail("Could not start run")

        with self.assertRaises(ValueError):
            g.API.dae.set_simulation_mode(False)  # Have to use API as user-level command doesn't raise

    def test_GIVEN_run_state_is_setup_WHEN_attempt_to_change_simulation_mode_THEN_simulation_mode_changes(self):
        if g.get_runstate() != "SETUP":
            self.fail("Should be in SETUP")

        g.set_dae_simulation_mode(False)
        self._wait_for_and_assert_dae_simulation_mode(False)

        g.set_dae_simulation_mode(True)
        self._wait_for_and_assert_dae_simulation_mode(True)

    def _wait_for_and_assert_dae_simulation_mode(self, mode):
        for _ in range(10):
            if g.get_dae_simulation_mode() == mode:
                return
            sleep(1)
        else:
            self.assertEqual(g.get_dae_simulation_mode(), mode)
