# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = ["KPLR_DATA_DIR"]

import os

KPLR_DATA_DIR = os.path.expanduser(
    os.environ.get("KPLR_DATA_DIR", os.path.join("~", ".kplr"))
)
