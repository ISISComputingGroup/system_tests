import os
import unittest
import types
import pkgutil

import sys


class TestGeniePythonImports(unittest.TestCase):
    """
    Tests that modules which users use can be imported.
    """
    def _attempt_to_import_module_by_name(self, module_name):
        """
        Attempts to import a module by name.
        :param module_name: the module name to import
        :return: None if no error on import, String describing error if there was an error.
        """
        try:
            mod = __import__(module_name)
            self.assertIsInstance(mod, types.ModuleType)
            return None
        except Exception as e:
            return "Could not import module '{}'. Exception was: {}: {}.".format(module_name, e.__class__.__name__, e)

    def test_WHEN_importing_all_installed_packages_THEN_no_error(self):
        """
        This tests that all of the modules we've installed are importable as modules.
        """
        failures = []
        for _, pkg, is_package in pkgutil.iter_modules():
            if is_package:
                res = self._attempt_to_import_module_by_name(pkg)
                if res is not None:
                    failures.append(res)

        self.assertEqual(len(failures), 0, "Could not import modules: \n{}".format("\n".join(failures)))
