import logging
import os
import unittest
import uuid
from pathlib import Path

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import matplotlib
from bluesky.callbacks import LiveTable
from bluesky.preprocessors import subs_decorator
from bluesky.run_engine import RunEngine, RunEngineResult
from genie_python import genie as g  # type: ignore
from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
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
from ibex_bluesky_core.devices.simpledae.waiters import (
    GoodFramesWaiter,
    PeriodGoodFramesWaiter,
)
from ibex_bluesky_core.log import set_bluesky_log_levels
from ibex_bluesky_core.run_engine import get_run_engine
from ophyd_async.plan_stubs import ensure_connected

from utilities.utilities import (
    load_config_if_not_already_loaded,
    set_genie_python_raises_exceptions,
)

matplotlib.use("qtagg")
RE: RunEngine = get_run_engine()

P3_INIT_VALUE: float = 123.456
P5_INIT_VALUE: float = 987.654321

LOG_FOLDER = os.path.join("C:\\", "instrument", "var", "logs", "bluesky")
LOG_MESSAGE = "Logging something to "
LOG_ENV_PATH = "IBEX_BLUESKY_CORE_LOGS"
LOG_FILE_NAME = "bluesky.log"


class TestBluesky(unittest.TestCase):
    def setUp(self) -> None:
        g.set_instrument(None)
        load_config_if_not_already_loaded("bluesky_sys_test")
        set_genie_python_raises_exceptions(True)
        g.cset("p3", P3_INIT_VALUE)
        g.cset("p5", P5_INIT_VALUE)
        set_bluesky_log_levels("DEBUG")

        log_path = LOG_FOLDER
        if LOG_ENV_PATH in os.environ:
            log_path = os.environ[LOG_ENV_PATH]

        self.qualified_log_filename = os.path.join(log_path, LOG_FILE_NAME)

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

    def test_scan_with_standard_callbacks(self) -> None:
        icc = ISISCallbacks(
            x="p5",
            y="p3",
            fit=Linear().fit(),
            human_readable_file_output_dir=Path(LOG_FOLDER) / "output_files",
            live_fit_logger_output_dir=Path(LOG_FOLDER) / "fitting",
        )

        @icc
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.scan([p3], p5, -10, 10, num=10)

        RE(_plan())

        self.assertAlmostEqual(icc.peak_stats["com"], 0)
        print(icc.live_fit.result.params["c0"])
        print(icc.live_fit.result.fit_report())
        self.assertAlmostEqual(icc.live_fit.result.params["c0"], P3_INIT_VALUE)

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

    def test_GIVEN_logging_is_requested_THEN_the_log_folder_exists(self) -> None:
        # Log invocation.
        logging.getLogger("ibex_bluesky_core").info(
            "test_GIVEN_logging_is_requested_THEN_the_log_folder_exists"
        )
        self.assertTrue(os.path.exists(LOG_FOLDER))

    def test_GIVEN_logging_is_requested_THEN_the_log_file_exists(self) -> None:
        # Log invocation.
        logging.getLogger("ibex_bluesky_core").info(
            "test_GIVEN_logging_is_requested_THEN_the_log_file_exists"
        )
        self.assertTrue(os.path.exists(self.qualified_log_filename))

    def test_GIVEN_logging_is_requested_THEN_the_log_file_contains_the_message(
        self,
    ) -> None:
        # Log invocation.
        bluesky_message = LOG_MESSAGE + str(uuid.uuid4())
        other_message = LOG_MESSAGE + str(uuid.uuid4())

        logging.getLogger("ibex_bluesky_core").info(bluesky_message)
        logging.getLogger("an.other.logger").info(other_message)

        # Open the log file and read its content.
        with open(self.qualified_log_filename, "r") as f:
            content = f.read()
            self.assertIn(bluesky_message, content)
            self.assertNotIn(other_message, content)

    def test_GIVEN_logging_is_configured_at_info_level_THEN_debug_messages_do_not_go_to_log_file(
        self,
    ):
        debug_msg = LOG_MESSAGE + str(uuid.uuid4())
        info_msg = LOG_MESSAGE + str(uuid.uuid4())

        set_bluesky_log_levels("INFO")
        logging.getLogger("ibex_bluesky_core").debug(debug_msg)
        logging.getLogger("ibex_bluesky_core").info(info_msg)

        with open(self.qualified_log_filename, "r") as f:
            content = f.read()
            self.assertNotIn(debug_msg, content)
            self.assertIn(info_msg, content)

    def test_GIVEN_logging_is_configured_at_debug_level_THEN_debug_messages_do_go_to_log_file(
        self,
    ):
        debug_msg = LOG_MESSAGE + str(uuid.uuid4())
        info_msg = LOG_MESSAGE + str(uuid.uuid4())

        set_bluesky_log_levels("DEBUG")
        logging.getLogger("ibex_bluesky_core").debug(debug_msg)
        logging.getLogger("ibex_bluesky_core").info(info_msg)

        with open(self.qualified_log_filename, "r") as f:
            content = f.read()
            self.assertIn(debug_msg, content)
            self.assertIn(info_msg, content)


if __name__ == "__main__":
    unittest.main()
