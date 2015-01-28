# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = ["radec_to_xyz"]

import numpy as np


def radec_to_xyz(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    return np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)
