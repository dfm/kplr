# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from kplr.api import API, Model
from kplr.config import KPLR_ROOT


class ApiTestCase(unittest.TestCase):
    def test_default_data_root(self):
        api = API()
        self.assertEqual(api.data_root, KPLR_ROOT)

    def test_custom_data_root(self):
        api = API("/home/data/")
        self.assertEqual(api.data_root, "/home/data/")

    def test_munge_dict_int_value(self):
        api = API()
        row = {"key": "666"}
        new_row = api._munge_dict(row)
        self.assertEqual(new_row["key"], 666)

    def test_munge_dict_float_value(self):
        api = API()
        row = {"key": "66.6"}
        new_row = api._munge_dict(row)
        self.assertAlmostEqual(new_row["key"], 66.6)

    def test_munge_dict_text_value(self):
        api = API()
        row = {"key": "value"}
        new_row = api._munge_dict(row)
        self.assertEqual(new_row["key"], "value")

    def test_munge_dict_empty_value(self):
        api = API()
        row = {"key": ""}
        new_row = api._munge_dict(row)
        self.assertIsNone(new_row["key"])


class TestModel(Model):
    _id = "\"{kepler_name}\""


class ModelTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_api = mock.MagicMock(spec=API)
        self.params = {
            "kepler_name": "Kepler-32 f",
            "kepid": 9787239,
        }
        self.model = TestModel(self.mock_api, self.params)

    def test_setting_params_in_init(self):
        self.assertEqual(self.model.kepler_name, self.params["kepler_name"])

    def test_class_in_str_and_repr(self):
        self.assertIn("TestModel", str(self.model))
        self.assertIn("TestModel", repr(self.model))

    def test_name_in_str_and_repr(self):
        self.assertIn("Kepler-32 f", str(self.model))
        self.assertIn("Kepler-32 f", repr(self.model))

    def test_get_light_curves(self):
        self.model.get_light_curves(short_cadence=False, fetch=True,
                                    clobber=True)
        self.mock_api.light_curves.assert_called_once_with(
            self.model.kepid,
            short_cadence=False,
            fetch=True,
            clobber=True,
        )

    def test_get_target_pixel_files(self):
        self.model.get_target_pixel_files(short_cadence=False, fetch=True,
                                          clobber=True)
        self.mock_api.target_pixel_files.assert_called_once_with(
            self.model.kepid,
            short_cadence=False,
            fetch=True,
            clobber=True,
        )
