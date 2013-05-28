#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["Dataset"]

import copy
from . import kplr

# These dependencies are optional for the ``kplr`` module but required to load
# a dataset. An ``ImportError`` exception will be raised when you try to load
# a file if any of these aren't installed.
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pyfits
except ImportError:
    pyfits = None

# ``untrendy`` is only required if you try to "untrend" a dataset so the
# ``ImportError`` will be raised then.
try:
    import untrendy
except ImportError:
    untrendy = None


class Dataset(object):
    """
    An interface to a Kepler light curve dataset.

    The object parses out various useful parameters:

    * ``texp``: the exposure time in days
    * ``time``: the array of timestamps in KBJD
    * ``bjd``: the same array in BJD
    * ``sapflux``, ``sapferr``, ``sapivar``: the raw aperture photometry
    * ``pdcflux``, ``pdcferr``, ``pdcivar``: the PDC corrected light curve
    * ``flux``, ``ferr``, ``ivar``: the "untrended" and normalized light curve

    :param filename:
        The filename of the FITS file in the standard Kepler format.

    :param untrend: (optional)
        Should the light curve be "untrended" using ``untrendy``?

    :param **untrendy_args: (optional)
        Any additional keyword arguments that should be passed to
        ``untrendy.untrend()``.

    """

    __type__ = "lc"
    vector = []

    def __init__(self, filename, untrend=False, **untrendy_args):
        if not np or not pyfits:
            raise ImportError("numpy and pyfits are required to load a "
                              "dataset.")

        self.filenames = [filename]
        with pyfits.open(filename) as f:
            # Find the cadence of the dataset and save the approximate
            # exposure time.
            self.cadence = (0 if f[0].header["OBSMODE"] == "short cadence"
                            else 1)
            self.texp = kplr.EXPOSURE_TIMES[self.cadence]

            # Convert the exposure time to days so that it is in consistent
            # units.
            self.texp /= 1440.

            # Load the actual data.
            data = f[1].data

            # Read in the timestamps in KBJD.
            self.time = np.array(data["TIME"], dtype=float)

            # Check quality flags.
            self.quality = np.array(data["SAP_QUALITY"], dtype=int)
            self.qualitymask = ~np.array(self.quality, dtype=bool)

            # Read in the raw aperture photometry of the light curve.
            self.sapflux = np.array(data["SAP_FLUX"], dtype=float)
            self.sapferr = np.array(data["SAP_FLUX_ERR"], dtype=float)
            self.sapmask = ~(np.isnan(self.time) +
                             np.isnan(self.sapflux) +
                             np.isnan(self.sapferr))
            self.sapivar = np.zeros_like(self.sapferr)
            self.sapivar[self.sapmask] = 1.0 / self.sapferr[self.sapmask] ** 2

            # Read in the PDC corrected light curve.
            self.pdcflux = np.array(data["PDCSAP_FLUX"], dtype=float)
            self.pdcferr = np.array(data["PDCSAP_FLUX_ERR"], dtype=float)
            self.pdcmask = ~(np.isnan(self.time) +
                             np.isnan(self.pdcflux) +
                             np.isnan(self.pdcferr))
            self.pdcivar = np.zeros_like(self.pdcferr)
            self.pdcivar[self.pdcmask] = 1.0 / self.pdcferr[self.pdcmask] ** 2

            # Compute the BJD.
            bjdconv = f[1].header["BJDREFI"] + f[1].header["BJDREFF"]
            self.bjd = self.time + bjdconv

        if untrend:
            if not untrendy:
                raise ImportError("The untrendy module is required for "
                                  "'untrending' of light curves.")

            self.mask = self.sapmask[:]
            m = self.sapmask * self.qualitymask
            self.flux = np.zeros_like(self.sapflux)
            self.ferr = np.zeros_like(self.sapflux)

            # Untrend the light curve using untrendy.
            mu = np.median(self.sapflux[m])
            untrendy_args["fill_times"] = untrendy_args.get("fill_times",
                                                            10 ** -1.25)
            model = untrendy.fit_trend(self.time[m], self.sapflux[m] / mu,
                                       self.sapferr[m] / mu, **untrendy_args)
            factor = mu * model(self.time[self.mask])
            self.flux[self.mask] = self.sapflux[self.mask] / factor
            self.ferr[self.mask] = self.sapferr[self.mask] / factor

            self.ivar = np.zeros_like(self.ferr)
            self.ivar[self.mask] = 1.0 / self.ferr[self.mask] ** 2

        else:
            self.flux = self.pdcflux[:]
            self.ferr = self.pdcferr[:]
            self.ivar = self.pdcivar[:]
            self.mask = self.pdcmask[:]

            factor = np.median(self.pdcflux[self.pdcmask])
            self.flux[self.mask] /= factor
            self.ferr[self.mask] /= factor
            self.ivar[self.mask] *= factor * factor

    def __add__(self, other):
        if self.texp != other.texp:
            raise ValueError("Incompatible exposure times.")

        new = copy.copy(self)
        new.filenames += other.filenames

        new.time = np.append(self.time[self.mask], other.time[other.mask])
        inds = np.argsort(new.time)
        new.time = new.time[inds]

        for attr in ["sapflux", "sapflux", "sapivar", "sapmask",
                     "pdcflux", "pdcferr", "pdcivar", "pdcmask",
                     "flux", "ferr", "ivar", "mask", "bjd"]:
            setattr(new, attr, np.append(getattr(self, attr)[self.mask],
                    getattr(other, attr)[other.mask])[inds])

        return new

    def __len__(self):
        return 0
