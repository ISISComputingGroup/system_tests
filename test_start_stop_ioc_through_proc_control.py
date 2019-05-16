import os
import unittest
from utilities.utilities import g
from six.moves import range
import requests
import time


class TestPlotting(unittest.TestCase):
    """
    It is very hard to write "comprehensive" unit tests for our integration layer with matplotlib

    Instead, we write a handful of "smoke tests" to check that it isn't throwing any hugely obvious exceptions
    """
    PYPLOT = None

    @classmethod
    def setUpClass(cls):
        """
        This is all a hack to get around the following:
        - unittest can't import modules by name
        - matplotlib imports modules by name as soon as you call either matplotlib.use(...) or import pyplot
        - once the backend has been imported in matplotlib it can't re-import a different one

        Our approach here is:
        - Set a matplotlib configuration variable to tell it where to find our backend
        - replace the __import__ special function in matplotlib.backends with a version that always returns our backend
        - then import pyplot

        THE ORDER OF THESE ITEMS IS IMPORTANT!
        """
        g.set_instrument(os.getenv("MYPVPREFIX"))
        import matplotlib
        matplotlib.rcParams['backend'] = "module://genie_python.matplotlib_backends/ibex_web_backend"
        import matplotlib.backends
        import genie_python.matplotlib_backend.ibex_web_backend
        matplotlib.backends.__import__ = lambda *a, **kw: genie_python.matplotlib_backend.ibex_web_backend
        import matplotlib.pyplot as pyplot
        TestPlotting.PYPLOT = pyplot

    def setUp(self):
        TestPlotting.PYPLOT.close('all')

    def assert_webserver_up(self):
        web_response = requests.get("http://127.0.0.1:8988/")
        self.assertEqual(web_response.status_code, 200)

    def test_GIVEN_spectra_plot_THEN_no_exceptions_thrown(self):
        g.begin()
        try:
            g.plot_spectrum(1)
            self.assert_webserver_up()
        finally:
            g.end()

    def test_GIVEN_spectra_plot_WHEN_adding_more_traces_THEN_no_exceptions_thrown(self):
        g.begin()
        try:
            p = g.plot_spectrum(1)
            p.add_spectrum(2)
            p.add_spectrum(3, period=2)
            self.assert_webserver_up()
        finally:
            g.end()

    def test_GIVEN_when_plot_exists_WHEN_connect_to_matplotlib_server_THEN_response_is_http_200_ok(self):
        TestPlotting.PYPLOT.plot(range(5))
        TestPlotting.PYPLOT.show()
        self.assert_webserver_up()
