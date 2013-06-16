#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["get_quad_coeffs", "LDCoeffAdaptor"]

import os
import requests
import numpy as np

from .config import KPLR_ROOT


def get_quad_coeffs(teff=5778, logg=None, feh=None, model="sing09",
                    data_root=None):
    """
    Get the quadratic coefficients for the standard Kepler limb-darkening
    profile.

    :param teff: (optional)
        The effective temperature in degrees K.

    :param logg: (optional)
        The log10 surface gravity in cm/s/s.

    :param feh: (optional)
        The metallicity [Fe/H].

    :model: (optional)
        The theoretical model to use. See :class:`LDCoeffAdaptor`.

    :param data_root: (optional)
        The local base directory where the grids will be downloaded to. This
        can also be set using the ``KPLR_ROOT`` environment variable. The
        default value is ``~/.kplr``.

    """
    # Find the LD coefficients from the theoretical models.
    a = LDCoeffAdaptor(model=model)
    return a.get_coeffs(teff, logg=logg, feh=feh)


class LDCoeffAdaptor(object):
    """
    Wrapper around various theoretical models for the coefficients of limb
    darkening profiles for Kepler stars.

    :param model: (optional)
        The name of the model that you would like to use. The currently
        supported models are ``sing09`` and ``claret11``. When you use a model
        for the first time, it will download the data file and save it to
        ``{data_root}/ldcoeffs/claret11.txt``.

    :param data_root: (optional)
        The local base directory where the grids will be downloaded to. This
        can also be set using the ``KPLR_ROOT`` environment variable. The
        default value is ``~/.kplr``.

    """

    models = {
        "sing09": "http://broiler.astrometry.net/~dfm265/ldcoeffs/sing.txt",
        "claret11": "http://broiler.astrometry.net/~dfm265/ldcoeffs/claret.txt"
    }

    def __init__(self, model="sing09", data_root=None):
        if model not in self.models:
            raise TypeError(("Unrecognized model '{0}'. The allowed values "
                             "are {1}.").format(model, self.allowed_models))

        # Save the provided data root directory and fall back on the
        # ``KPLR_ROOT`` environment variable.
        self.data_root = data_root
        if data_root is None:
            self.data_root = KPLR_ROOT

        # Download the data table if it doesn't always exist.
        local_fn = os.path.join(KPLR_ROOT, "ldcoeffs",
                                "{0}.txt".format(model))
        if not os.path.exists(local_fn):
            print("Downloading the data file for the '{0}' model"
                  .format(model))
            r = requests.get(self.models[model])
            if r.status_code != requests.codes.ok:
                r.raise_for_status()
            try:
                os.makedirs(os.path.dirname(local_fn))
            except os.error:
                pass
            open(local_fn, "w").write(r.content)
            print("  .. Finished.")

        if model == "sing09":
            data = np.loadtxt(local_fn, skiprows=10, usecols=range(6))
            self.T = data[:, 0]
            self.logg = data[:, 1]
            self.feh = data[:, 2]
            self.mu1 = data[:, 4]
            self.mu2 = data[:, 5]

        else:
            data = np.loadtxt(local_fn, skiprows=59, delimiter="|",
                              usecols=range(7))
            self.T = data[:, 2]
            self.logg = data[:, 1]
            self.feh = data[:, 3]
            self.mu1 = data[:, 5]
            self.mu2 = data[:, 6]

    def get_coeffs(self, teff, logg=None, feh=None):
        """
        Get the coefficients of the quadratic limb darkening profile given by
        theory.

        :param teff:
            The effective temperature in degrees K.

        :param logg: (optional)
            The log10 surface gravity in cm/s/s.

        :param feh: (optional)
            The metallicity [Fe/H].

        """
        T0 = self.T[np.argmin(np.abs(self.T - teff))]
        inds = self.T == T0
        if logg is not None:
            lg0 = self.logg[np.argmin(np.abs(self.logg - logg))]
            inds *= self.logg == lg0
        if feh is not None:
            feh0 = self.feh[np.argmin(np.abs(self.feh - feh))]
            inds *= self.feh == feh0
        return np.mean(self.mu1[inds]), np.mean(self.mu2[inds])
