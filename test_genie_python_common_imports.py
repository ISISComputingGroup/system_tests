import importlib
import pkgutil
import types
import unittest
import warnings

IGNORED_MODULES = {
    "curses",  # Not supported on windows
    "dockerpty",  # Not supported on windows
    "adodbapi",  # Not needed by users
    "black",  # Not needed by users
    # importing pip overwrites distutils in sys.modules
    # with a copy of setuptools instead, which then breaks
    # any packages that depend on distutils directly.
    # https://github.com/pypa/pip/issues/8761
    #
    # Importing pip as a module in general is a bad idea (tm), so just don't do that.
    #
    # It's possible to use:
    # >>> import _distutils_hack
    # >>> _distutils_hack.remove_shim()
    # >>> import pip
    # if someone *really* needs to import pip (yes, seriously; no, it's not a good idea).
    "pip",
}


class TestGeniePythonImports(unittest.TestCase):
    """
    Tests that modules which users use can be imported.
    """

    def _attempt_to_import_module_by_name(self, module_name: str) -> str | None:
        """
        Attempts to import a module by name.
        :param module_name: the module name to import
        :return: None if no error on import, String describing error if there was an error.
        """

        if module_name in IGNORED_MODULES or module_name.startswith("_"):
            return None

        try:
            mod = importlib.import_module(module_name)
            self.assertIsInstance(mod, types.ModuleType)
            del mod
        except Exception as e:
            return "Could not import module '{}'. Exception was: {}: {}.".format(
                module_name, e.__class__.__name__, e
            )
        else:
            return None

    def test_WHEN_importing_all_installed_packages_THEN_no_error(self) -> None:
        """
        This tests that all of the modules we've installed are importable as modules.
        """

        # Ignore warnings. We get lots of these from various modules and it's too noisy for this
        # test suite.
        warnings.filterwarnings("ignore")

        failures = []
        for _, pkg, is_package in pkgutil.iter_modules():
            if is_package:
                res = self._attempt_to_import_module_by_name(pkg)
                if res is not None:
                    failures.append(res)

        self.assertEqual(
            len(failures), 0, "Could not import modules: \n{}".format("\n".join(failures))
        )
