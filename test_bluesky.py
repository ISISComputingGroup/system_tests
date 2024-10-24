import unittest
import os, sys

import bluesky.plan_stubs as bps
import bluesky.plans as bp
from bluesky.callbacks import LiveTable
from bluesky.preprocessors import subs_decorator
from bluesky.run_engine import RunEngine, RunEngineResult
from genie_python import genie as g  # type: ignore
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_r, block_rw_rbv
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
    PeriodGoodFramesNormalizer,
)
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.logger import logger
from ibex_bluesky_core.run_engine import get_run_engine
from ophyd_async.plan_stubs import ensure_connected

from utilities.utilities import (
    load_config_if_not_already_loaded,
    set_genie_python_raises_exceptions,
)

RE: RunEngine = get_run_engine()

P3_INIT_VALUE: float = 123.456
P5_INIT_VALUE: float = 987.654321

LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", "bluesky")
LOG_MESSAGE = "Logging something to "
LOG_ENV_PATH = "BLUESKY_LOGS"


class TestBluesky(unittest.TestCase):
    def setUp(self) -> None:
        g.set_instrument(None)
        load_config_if_not_already_loaded("bluesky_sys_test")
        set_genie_python_raises_exceptions(True)
        g.cset("p3", P3_INIT_VALUE)
        g.cset("p5", P5_INIT_VALUE)

    def _run_per_point_dae(self) -> SimpleDae:
        prefix = get_pv_prefix()
        controller = RunPerPointController(save_run=True)
        waiter = GoodFramesWaiter(100)
        reducer = GoodFramesNormalizer(
            prefix=prefix,
            detector_spectra=[i for i in range(1, 10)],
        )

        dae = SimpleDae(
            prefix=prefix,
            controller=controller,
            waiter=waiter,
            reducer=reducer,
        )
        return dae

    def _period_per_point_dae(self) -> SimpleDae:
        prefix = get_pv_prefix()
        controller = PeriodPerPointController(save_run=True)
        waiter = PeriodGoodFramesWaiter(100)
        reducer = PeriodGoodFramesNormalizer(
            prefix=prefix,
            detector_spectra=[i for i in range(1, 10)],
        )

        dae = SimpleDae(
            prefix=prefix,
            controller=controller,
            waiter=waiter,
            reducer=reducer,
        )
        return dae

    def test_rd_block(self) -> None:
        def _plan():
            p3 = block_r(float, "p3")
            yield from ensure_connected(p3)
            return (yield from bps.rd(p3))

        result = RE(_plan())
        assert isinstance(result, RunEngineResult)

        self.assertAlmostEqual(result.plan_result, P3_INIT_VALUE, places=5)

    def test_abs_scan_two_blocks(self) -> None:
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.scan([p3], p5, -10, 10, num=41)

        RE(_plan())

        # At end of scan, p5 should be left at last value by default.
        self.assertAlmostEqual(g.cget("p5")["value"], 10)

    def test_rel_scan_two_blocks(self) -> None:
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.rel_scan([p3], p5, -10, 10, num=41)

        RE(_plan())

        # After a rel_scan, the movable is moved back to original value
        self.assertAlmostEqual(g.cget("p5")["value"], P5_INIT_VALUE)

    def test_scan_with_livetable_callback(self) -> None:
        livetable_lines = []

        @subs_decorator(
            [
                LiveTable(["p3", "p5"], out=livetable_lines.append),
            ]
        )
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.scan([p3], p5, -10, 10, num=41)

        RE(_plan())

        # Tricky as livetable contains timestamps etc, but check that the table
        # describes the first and last point we were trying to measure, with appropriate
        # precisions pulled from the PVs.
        self.assertTrue(any("|    123.456 |  -10.00000 |" in line for line in livetable_lines))
        self.assertTrue(any("|    123.456 |   10.00000 |" in line for line in livetable_lines))

    def test_count_simple_dae(self) -> None:
        start_run_number = int(g.get_runnumber())

        def _plan():
            dae = self._run_per_point_dae()
            yield from ensure_connected(dae)
            yield from bps.mv(dae.number_of_periods, 1)
            yield from bp.count([dae])

        RE(_plan())
        end_run_number = int(g.get_runnumber())

        self.assertEqual(start_run_number + 1, end_run_number)

    def test_scan_simple_dae_in_run_per_point_mode(self) -> None:
        npoints = 3
        start_run_number = int(g.get_runnumber())

        def _plan():
            dae = self._run_per_point_dae()
            p3 = block_rw_rbv(float, "p3")
            yield from ensure_connected(dae, p3)
            yield from bps.mv(dae.number_of_periods, 1)
            yield from bp.scan([dae], p3, 0, 10, num=npoints)

        RE(_plan())
        end_run_number = int(g.get_runnumber())

        # Assert we've done npoints runs
        self.assertEqual(start_run_number + npoints, end_run_number)

    def test_scan_simple_dae_in_period_per_point_mode(self) -> None:
        npoints = 3
        start_run_number = int(g.get_runnumber())

        def _plan():
            dae = self._period_per_point_dae()
            p3 = block_rw_rbv(float, "p3")
            yield from ensure_connected(dae, p3)
            yield from bps.mv(dae.number_of_periods, npoints)
            yield from bp.scan([dae], p3, 0, 10, num=npoints)

        RE(_plan())
        end_run_number = int(g.get_runnumber())

        # Assert we've done only one run
        self.assertEqual(start_run_number + 1, end_run_number)
        # Assert we successfully set npoints periods
        self.assertEqual(g.get_number_periods(), npoints)

    def test_GIVEN_logging_is_requested_THEN_the_log_folder_exists():
        this_function_name = sys._getframe().f_code.co_name
        message = LOG_MESSAGE + this_function_name
        # Log invocation.
        logger.blueskylogger.info(message)
        if LOG_ENV_PATH in os.environ:
            assert os.path.exists(os.environ[LOG_ENV_PATH]) == False

        if LOG_ENV_PATH not in os.environ:
            assert os.path.exists(LOG_FOLDER) == True

    def test_GIVEN_logging_is_requested_THEN_the_log_file_exists():
        log_path = LOG_FOLDER
        if LOG_ENV_PATH in os.environ:
            log_path = os.environ[LOG_ENV_PATH]

        # Log invocation.
        this_function_name = sys._getframe().f_code.co_name
        message = LOG_MESSAGE + this_function_name
        logger.blueskylogger.info(message)
        qualified_log_filename = os.path.join(log_path, LOG_FILE_NAME)
        assert os.path.exists(qualified_log_filename) == True

    def test_GIVEN_logging_is_requested_THEN_the_log_file_contains_the_message():
        log_path = LOG_FOLDER
        if LOG_ENV_PATH in os.environ:
            log_path = os.environ[LOG_ENV_PATH]

        # Log invocation.
        this_function_name = sys._getframe().f_code.co_name
        message = LOG_MESSAGE + this_function_name
        logger.blueskylogger.info(message)
        qualified_log_filename = os.path.join(log_path, LOG_FILE_NAME)
        assert os.path.exists(qualified_log_filename) == True
        # Open the log file and read its content.
        with open(qualified_log_filename, "r") as f:
            content = f.read()
            assert content.__contains__(message)


if __name__ == "__main__":
    unittest.main()
