#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["API", "KOI", "Planet", "Star", "LightCurve", "TargetPixelFile"]

import os
import re
import json
import types
import urllib
import urllib2
import logging

try:
    import pyfits
    pyfits = pyfits
except ImportError:
    pyfits = None

from .config import KPLR_ROOT
from . import mast


class API(object):
    """
    Interface with MAST and Exoplanet Archive APIs.

    :param data_root: (optional)
        The local base directory where any data should be downloaded to. This
        can also be set using the ``KPLR_ROOT`` environment variable. The
        default value is ``~/.kplr``.

    """

    ea_url = ("http://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI"
              "/nph-nstedAPI")
    mast_url = "http://archive.stsci.edu/kepler/{0}/search.php"

    def __init__(self, data_root=None):
        self.data_root = data_root
        if data_root is None:
            self.data_root = KPLR_ROOT

    def __str__(self):
        return "<API(data_root=\"{0}\")>".format(self.data_root)

    def __unicode__(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def ea_request(self, table, sort=None, **params):
        """
        Submit a request to the Exoplanet Archive API and return a dictionary.

        :param table:
            The table that you want to search.

        :param **params:
            Any other search parameters.

        """
        params["table"] = table

        # Deal with sort order.
        if sort is not None:
            if isinstance(sort, types.StringTypes):
                params["order"] = sort
            else:
                params["order"] = sort[0]
                if sort[1] == -1:
                    params["order"] += "+desc"

        # Format the URL in the *horrifying* way that EA needs it to be...
        # they don't un-escape the HTTP parameters!!!
        payload = ["{0}={1}".format(k, urllib.quote_plus(v, "\"'+"))
                   for k, v in params.items()]

        # Send the request.
        r = urllib2.Request(self.ea_url, data="&".join(payload))
        handler = urllib2.urlopen(r)
        code = handler.getcode()
        txt = handler.read()

        # Hack because Exoplanet Archive doesn't return HTTP errors.
        if int(code) != 200 or "ERROR" in txt:
            full_url = handler.geturl() + "?" + "&".join(payload)
            raise APIError(code, full_url, txt)

        # Parse the CSV output.
        csv = txt.splitlines()
        columns = csv[0].split(",")
        result = []
        for line in csv[1:]:
            result.append(dict(zip(columns, line.split(","))))

        return [self._munge_dict(row) for row in result]

    def mast_request(self, category, adapter=None, sort=None, **params):
        """
        Submit a request to the MAST API and return a dictionary of parameters.

        :param category:
            The table that you want to search.

        :param **params:
            Any other search parameters.

        """
        params["action"] = params.get("action", "Search")
        params["outputformat"] = "JSON"
        params["coordformat"] = "dec"
        params["verb"] = 3

        # Deal with sort order.
        if sort is not None:
            if isinstance(sort, types.StringTypes):
                params["ordercolumn1"] = sort
            else:
                params["ordercolumn1"] = sort[0]
                if sort[1] == -1:
                    params["descending1"] = "on"

        # Send the request.
        r = urllib2.Request(self.mast_url.format(category),
                            data=urllib.urlencode(params))
        handler = urllib2.urlopen(r)
        code = handler.getcode()
        txt = handler.read()
        if int(code) != 200:
            full_url = handler.geturl() + "?" + urllib.urlencode(params)
            raise APIError(code, full_url, txt)

        # Parse the JSON.
        try:
            result = json.loads(txt)
        except ValueError:
            full_url = handler.geturl() + "?" + urllib.urlencode(params)
            raise APIError(code, full_url,
                           "No JSON object could be decoded.\n" + txt)

        # Fake munge the types if no adapter was provided.
        if adapter is None:
            return [self._munge_dict(row) for row in result]

        return [adapter(row) for row in result]

    def _munge_dict(self, row):
        """
        Iterate through a dictionary and try to interpret the data types in a
        sane way.

        :param row:
            A dictionary of (probably) strings.

        :returns new_row:
            A dictionary with the same keys as ``row`` but reasonably typed
            values.

        """
        tmp = {}
        for k, v in row.items():
            # Good-god-what-type-is-this-parameter?!?
            try:
                tmp[k] = int(v)
            except ValueError:
                try:
                    tmp[k] = float(v)
                except ValueError:
                    tmp[k] = v

            # Empty entries are mapped to None.
            if v == "":
                tmp[k] = None

        return tmp

    def kois(self, **params):
        """
        Get a list of KOIs from The Exoplanet Archive.

        :param **params:
            The search parameters for the Exoplanet Archive API.

        """
        return [KOI(self, k) for k in self.ea_request("cumulative", **params)]

    def koi(self, koi_number):
        """
        Find a single KOI given a KOI number (e.g. 145.01).

        :param koi_number:
            The number identifying the KOI. This should be a float with the
            ``.0N`` for some value of ``N``.

        """
        kois = self.kois(where="kepoi_name+like+'K{0:08.2f}'"
                         .format(float(koi_number)))
        if not len(kois):
            raise ValueError("No KOI found with the number: '{0}'"
                             .format(koi_number))
        return kois[0]

    def planets(self, **params):
        """
        Get a list of confirmed (Kepler) planets from MAST.

        :param **params:
            The search parameters for the MAST API.

        """
        planets = self.mast_request("confirmed_planets",
                                    adapter=mast.planet_adapter, **params)
        return [Planet(self, p) for p in planets]

    def planet(self, name):
        """
        Get a planet by the Kepler name (e.g. "6b" or "Kepler-62b").

        :param name:
            The name of the planet.

        """
        # Parse the planet name.
        matches = re.findall("([0-9]+)[-\s]*([a-zA-Z])", name)
        if len(matches) != 1:
            raise ValueError("Invalid planet name '{0}'".format(name))
        kepler_name = "Kepler-{0} {1}".format(*(matches[0]))

        # Query the API.
        planets = self.planets(kepler_name=kepler_name, max_records=1)
        if not len(planets):
            raise ValueError("No planet found with the name: '{0}'"
                             .format(kepler_name))
        return planets[0]

    def stars(self, **params):
        """
        Get a list of KIC targets from MAST. Only return up to 100 results by
        default.

        :param **params:
            The query parameters for the MAST API.

        """
        params["max_records"] = params.pop("max_records", 100)
        stars = self.mast_request("kic10", adapter=mast.star_adapter,
                                  **params)
        return [Star(self, s) for s in stars]

    def star(self, kepid):
        """
        Get a KIC target by id from MAST.

        :param kepid:
            The integer ID of the star in the KIC.

        """
        stars = self.stars(kic_kepler_id=kepid, max_records=1)
        if not len(stars):
            raise ValueError("No KIC target found with id: '{0}'"
                             .format(kepid))
        return stars[0]

    def _data_search(self, kepler_id, short_cadence=True):
        """
        Run a generic data search on MAST to return a list of dictionaries
        describing the data products.

        :param kepler_id:
            The KIC ID of the target star.

        :param short_cadence:
            A boolean flag that determines whether or not the short cadence
            data should be included.

        """
        params = {"ktc_kepler_id": kepler_id}
        if not short_cadence:
            params["ktc_target_type"] = "LC"

        data_list = self.mast_request("data_search",
                                      adapter=mast.dataset_adapter,
                                      **params)
        if not len(data_list):
            raise ValueError("No data files found for: '{0}'"
                             .format(kepler_id))
        return data_list

    def light_curves(self, kepler_id, short_cadence=True, fetch=False,
                     clobber=False):
        """
        Find the set of light curves associated with a KIC target.

        :param kepler_id:
            The KIC ID of the target star.

        :param short_cadence:
            A boolean flag that determines whether or not the short cadence
            data should be included. (default: True)

        :param fetch:
            A boolean flag that determines whether or not the data file should
            be downloaded.

        :param clobber:
            A boolean flag that determines whether or not the data file should
            be overwritten even if it already exists.

        """
        lcs = [LightCurve(self, d) for d in self._data_search(kepler_id,
               short_cadence=short_cadence)]
        if fetch:
            [l.fetch(clobber=clobber) for l in lcs]
        return lcs

    def target_pixel_files(self, kepler_id, short_cadence=True, fetch=False,
                           clobber=False):
        """
        Find the set of target pixel files associated with a KIC target.

        :param kepler_id:
            The KIC ID of the target star.

        :param short_cadence:
            A boolean flag that determines whether or not the short cadence
            data should be included. (default: True)

        :param fetch:
            A boolean flag that determines whether or not the data file should
            be downloaded.

        :param clobber:
            A boolean flag that determines whether or not the data file should
            be overwritten even if it already exists.

        """
        tpfs = [TargetPixelFile(self, d) for d in self._data_search(kepler_id,
                short_cadence=short_cadence)]
        if fetch:
            [l.fetch(clobber=clobber) for l in tpfs]
        return tpfs


class APIError(Exception):
    """
    Exception raised when an API request fails.

    :param code:
        The HTTP status code that caused the failure.

    :param url:
        The endpoint (with parameters) of the request.

    :param txt:
        A human readable description of the error.

    """

    def __init__(self, code, url, txt):
        super(APIError, self).__init__(("The API returned code {0} for URL: "
                                        "'{1}' with message:\n{2}")
                                       .format(code, url, txt))
        self.code = code
        self.txt = txt
        self.url = url


class Model(object):
    """
    An abstract base class that provides functions for converting the JSON
    dictionaries returned by the API into Python objects with the correct
    properties.

    :param api:
        A reference to the :class:`API` object that made the request.

    :param params:
        The dictionary of values returned by the API.

    """

    # A format string that generates a unique identifier for the model that
    # should be overloaded by subclasses.
    _id = "..."

    def __init__(self, api, params):
        self.api = api
        self.params = params
        for k, v in params.iteritems():
            setattr(self, k, v)

        self._name = self._id.format(**params)

    def __str__(self):
        return "<{0}({1})>".format(self.__class__.__name__, self._name)

    def __unicode__(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def get_light_curves(self, short_cadence=True, fetch=False, clobber=False):
        """
        Get a list of light curve datasets for the model and optionally
        download the FITS files.

        :param short_cadence:
            A boolean flag that determines whether or not the short cadence
            data should be included. (default: True)

        :param fetch:
            A boolean flag that determines whether or not the data file should
            be downloaded.

        :param clobber:
            A boolean flag that determines whether or not the data file should
            be overwritten even if it already exists.

        """
        return self.api.light_curves(self.kepid, short_cadence=short_cadence,
                                     clobber=clobber)

    def get_target_pixel_files(self, short_cadence=True, fetch=False,
                               clobber=False):
        """
        Get a list of target pixel datasets for the model and optionally
        download the FITS files.

        :param short_cadence:
            A boolean flag that determines whether or not the short cadence
            data should be included. (default: True)

        :param fetch:
            A boolean flag that determines whether or not the data file should
            be downloaded.

        :param clobber:
            A boolean flag that determines whether or not the data file should
            be overwritten even if it already exists.

        """
        return self.api.target_pixel_files(self.kepid,
                                           short_cadence=short_cadence,
                                           clobber=clobber)


class KOI(Model):
    """
    A model specifying a Kepler Object of Interest (KOI).

    """

    _id = "\"{kepoi_name}\""

    def __init__(self, *args, **params):
        super(KOI, self).__init__(*args, **params)
        self._star = None

    @property
    def star(self):
        """
        The :class:`Star` entry from the Kepler Input Catalog associated with
        this object.

        """
        if self._star is None:
            self._star = self.api.star(self.kepid)
        return self._star


class Planet(Model):
    """
    A confirmed planet from the `MAST confirmed_planets table
    <http://archive.stsci.edu/search_fields.php?mission=kepler_cp>`_. This
    table has far less—and far less accurate—information than the KOI table
    so it's generally a good idea to use the ``koi`` property to access the
    catalog values.

    """

    _id = "\"{kepler_name}\""

    def __init__(self, *args, **params):
        super(Planet, self).__init__(*args, **params)
        self._koi = None
        self._star = None

    @property
    def koi(self):
        """
        The :class:`KOI` entry that led to this planet. The KOI table is much
        more complete so the use of this object tends to be preferred over the
        built in :class:`Planet` property values.

        """
        if self._koi is None:
            self._koi = self.api.koi(self.koi_number)
        return self._koi

    @property
    def star(self):
        """
        The :class:`Star` entry from the Kepler Input Catalog associated with
        this object.

        """
        if self._star is None:
            self._star = self.api.star(self.kepid)
        return self._star


class Star(Model):
    """
    A star from the `Kepler Input Catalog (KIC)
    <http://archive.stsci.edu/search_fields.php?mission=kic10>`_.

    """

    _id = "{kic_kepler_id}"

    def __init__(self, *args, **params):
        super(Star, self).__init__(*args, **params)
        self.kepid = self.kic_kepler_id
        self._kois = None

    @property
    def kois(self):
        """
        The list of :class:`KOI` entries found in this star's light curve.

        """
        if self._kois is None:
            self._kois = self.api.kois(where="kepid like '{0}'"
                                       .format(self.kepid))
        return self._kois


class _datafile(Model):

    _id = "\"{sci_data_set_name}_{ktc_target_type}\""
    base_url = "http://archive.stsci.edu/pub/kepler/{0}/{1}/{2}/{3}"
    product = None
    suffixes = None
    filetype = None

    def __init__(self, *args, **params):
        super(_datafile, self).__init__(*args, **params)
        self.kepid = "{0:09d}".format(int(self.ktc_kepler_id))
        self.base_dir = os.path.join(self.api.data_root, "data", self.product,
                                     self.kepid)

        suffix = self.suffixes[int(self.ktc_target_type != "LC")]
        self._filename = "{0}_{1}{2}".format(self.sci_data_set_name,
                                             suffix, self.filetype).lower()

    @property
    def filename(self):
        """
        The local filename of the data file. This file is only guaranteed to
        exist after ``fetch()`` has been called.

        """
        return os.path.join(self.base_dir, self._filename)

    @property
    def url(self):
        """
        The remote URL for the data file on the MAST servers.

        """
        return self.base_url.format(self.product, self.kepid[:4],
                                    self.kepid, self._filename)

    def open(self, clobber=False, **kwargs):
        """
        Open the FITS data file and return the ``pyfits.HDUList``. This will
        download the file if it isn't already saved locally.

        :param clobber:
            Overwrite the local file even if it exists? This can be helpful if
            the file gets corrupted somehow.

        :param **kwargs:
            Any keyword arguments that you would like to pass to the
            :func:`pyfits.open` function.

        """
        if pyfits is None:
            raise ImportError("The pyfits module is required to read data "
                              "files.")

        # Download the file if it's not already cached.
        fn = self.filename
        self.fetch(clobber=clobber)

        # Load the pyfits file.
        return pyfits.open(fn, **kwargs)

    def fetch(self, clobber=False):
        """
        Download the data file from the server and save it locally. The local
        file will be saved in the directory specified by the ``data_root``
        property of the API.

        :param clobber:
            Should an existing local file be overwritten? (default: False)

        """
        # Check if the file already exists.
        filename = self.filename
        if os.path.exists(filename) and not clobber:
            logging.info("Found local file: '{0}'".format(filename))
            return self

        # Fetch the remote file.
        url = self.url
        logging.info("Downloading file from: '{0}'".format(url))
        r = urllib2.Request(url)
        handler = urllib2.urlopen(r)
        code = handler.getcode()
        if int(code) != 200:
            raise APIError(code, url, "")

        # Make sure that the root directory exists.
        try:
            os.makedirs(self.base_dir)
        except os.error:
            pass

        # Save the contents of the file.
        logging.info("Saving file to: '{0}'".format(filename))
        open(filename, "wb").write(handler.read())

        return self


class LightCurve(_datafile):
    """
    A reference to a light curve dataset on the MAST severs. This object
    handles local caching of the file in a strict directory structure.

    """

    product = "lightcurves"
    suffixes = ["llc", "slc"]
    filetype = ".fits"


class TargetPixelFile(_datafile):
    """
    A reference to a target pixel dataset on the MAST severs. Like the
    :class:`LightCurve` object, this object handles local caching of the file
    in a strict directory structure.

    """

    product = "target_pixel_files"
    suffixes = ["lpd-targ", "spd-targ"]
    filetype = ".fits.gz"
