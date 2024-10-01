import unittest
from io import StringIO

from utilities.utilities import (
    g,
    load_config_if_not_already_loaded,
    set_genie_python_raises_exceptions,
)
from ibex_bluesky_core.run_engine import get_run_engine
from bluesky.run_engine import RunEngine
import bluesky.plan_stubs as bps
import bluesky.plans as bp
from ophyd_async.plan_stubs import ensure_connected
from ibex_bluesky_core.devices.block import block_r, block_rw, block_rw_rbv
from bluesky.preprocessors import subs_decorator
from bluesky.callbacks import LiveTable
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import PeriodPerPointController, RunPerPointController
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.devices.simpledae.reducers import GoodFramesNormalizer, PeriodGoodFramesNormalizer

RE: RunEngine = get_run_engine()

P3_INIT_VALUE = 123.456
P5_INIT_VALUE = 987.654321


class TestBluesky(unittest.TestCase):
    def setUp(self):
        g.set_instrument(None)
        # load_config_if_not_already_loaded("bluesky_sys_test")
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

    def test_rd_block(self):
        def _plan():
            p3 = block_r(float, "p3")
            yield from ensure_connected(p3)
            return (yield from bps.rd(p3))

        result = RE(_plan())

        self.assertAlmostEqual(result.plan_result, P3_INIT_VALUE, places=5)

    def test_abs_scan_two_blocks(self):
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.scan([p3], p5, -10, 10, num=41)

        RE(_plan())

        # At end of scan, p5 should be left at last value by default.
        self.assertAlmostEqual(g.cget("p5")["value"], 10)

    def test_rel_scan_two_blocks(self):
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.rel_scan([p3], p5, -10, 10, num=41)

        RE(_plan())

        # After a rel_scan, the movable is moved back to original value
        self.assertAlmostEqual(g.cget("p5")["value"], P5_INIT_VALUE)

    def test_scan_with_livetable_callback(self):
        livetable_lines = []

        @subs_decorator([
            LiveTable(["p3", "p5"], out=livetable_lines.append),
        ])
        def _plan():
            p3 = block_r(float, "p3")
            p5 = block_rw_rbv(float, "p5")
            yield from ensure_connected(p3, p5)
            yield from bp.scan([p3], p5, -10, 10, num=41)

        RE(_plan())

        # Tricky as livetable contains timestamps etc, but check that the table
        # describes the first and last point we were trying to measure, with appropriate
        # precisions.
        self.assertTrue(any("|    123.456 |  -10.00000 |" in line for line in livetable_lines))
        self.assertTrue(any("|    123.456 |   10.00000 |" in line for line in livetable_lines))

    def test_count_simple_dae(self):
        start_run_number = int(g.get_runnumber())

        def _plan():
            dae = self._run_per_point_dae()
            yield from ensure_connected(dae)
            yield from bps.mv(dae.number_of_periods, 1)
            yield from bp.count([dae])

        RE(_plan())
        end_run_number = int(g.get_runnumber())

        self.assertEqual(start_run_number + 1, end_run_number)

    def test_scan_simple_dae_in_run_per_point_mode(self):
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

    def test_scan_simple_dae_in_period_per_point_mode(self):
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


if __name__ == "__main__":
    unittest.main()
