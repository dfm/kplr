# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = [
    "download",
    "PlanetCatalog", "KOICatalog", "KICCatalog", "EPICCatalog",
]

import os
import logging

import pandas as pd
from six.moves import urllib

from .config import KPLR_DATA_DIR


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
