# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = [
    "download",
    "PlanetCatalog", "KOICatalog", "KICCatalog", "EPICCatalog",
]

import os
import logging

import numpy as np
import pandas as pd
from six.moves import urllib

from .utils import singleton
from .coords import radec_to_xyz
from .config import KPLR_DATA_DIR

try:
    from scipy.spatial import cKDTree
except ImportError:
    cKDTree = None


def download():
    for c in (PlanetCatalog, KOICatalog, KICCatalog, EPICCatalog):
        print("Downloading {0}...".format(c.__name__))
        c().fetch(clobber=True)


class Catalog(object):

    url = None
    name = None
    ext = ".h5"

    def __init__(self, data_root=None):
        self.data_root = KPLR_DATA_DIR if data_root is None else data_root
        self._df = None
        self._spatial = None

    @property
    def filename(self):
        if self.name is None:
            raise NotImplementedError("subclasses must provide a name")
        return os.path.join(self.data_root, "catalogs", self.name + self.ext)

    def fetch(self, clobber=False):
        # Check for a local file first.
        fn = self.filename
        if os.path.exists(fn) and not clobber:
            logging.info("Found local file: '{0}'".format(fn))
            return

        # Fetch the remote file.
        if self.url is None:
            raise NotImplementedError("subclasses must provide a URL")
        url = self.url
        logging.info("Downloading file from: '{0}'".format(url))
        r = urllib.request.Request(url)
        handler = urllib.request.urlopen(r)
        code = handler.getcode()
        if int(code) != 200:
            raise CatalogDownloadError(code, url, "")

        # Make sure that the root directory exists.
        try:
            os.makedirs(os.path.split(fn)[0])
        except os.error:
            pass

        self._save_fetched_file(handler)

    def _save_fetched_file(self, file_handle):
        raise NotImplementedError("subclasses must implement this method")

    @property
    def df(self):
        if self._df is None:
            print("loading df")
            if not os.path.exists(self.filename):
                self.fetch()
            self._df = pd.read_hdf(self.filename, self.name)
        return self._df

    @property
    def spatial(self):
        if self._spatial is None:
            self._spatial = self._build_spatial()
        return self._spatial

    def _build_spatial(self):
        if cKDTree is None:
            raise ImportError("scipy is required for spatial search")
        df = self.df
        x, y, z = radec_to_xyz(df.ra, df.dec)
        coords = np.vstack((x, y, z)).T
        tree = cKDTree(coords)
        return tree


class ExoplanetArchiveCatalog(Catalog):

    @property
    def url(self):
        if self.name is None:
            raise NotImplementedError("subclasses must provide a name")
        return ("http://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI/"
                "nph-nstedAPI?table={0}&select=*").format(self.name)

    def _save_fetched_file(self, file_handle):
        df = pd.read_csv(file_handle)
        df.to_hdf(self.filename, self.name, format="t")


class PlanetCatalog(ExoplanetArchiveCatalog):

    name = "planets"


class KOICatalog(ExoplanetArchiveCatalog):
    name = "cumulative"

    def join_stars(self, df=None):
        if df is None:
            df = self.df
        kic = KICCatalog(data_root=self.data_root)
        return pd.merge(df, kic.df, on="kepid")


class KICCatalog(ExoplanetArchiveCatalog):
    name = "keplerstellar"


class EPICCatalog(ExoplanetArchiveCatalog):
    name = "k2targets"


class CatalogDownloadError(Exception):
    """
    Exception raised when an catalog download request fails.

    :param code:
        The HTTP status code that caused the failure.

    :param url:
        The endpoint (with parameters) of the request.

    :param txt:
        A human readable description of the error.

    """

    def __init__(self, code, url, txt):
        super(CatalogDownloadError, self).__init__(
            "The download returned code {0} for URL: '{1}' with message:\n{2}"
            .format(code, url, txt))
        self.code = code
        self.txt = txt
        self.url = url


# Set all the catalogs to be singletons so that the data are shared across
# instances.
PlanetCatalog = singleton(PlanetCatalog)
KOICatalog = singleton(KOICatalog)
KICCatalog = singleton(KICCatalog)
EPICCatalog = singleton(EPICCatalog)
