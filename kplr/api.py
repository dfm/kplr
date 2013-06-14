#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["API", "KOI", "Planet"]

import os
import re
import json
import urllib
import logging
import urllib2

from .config import KPLR_ROOT
from . import mast

# Root directory for local data.
KPLR_DATA_DIR = os.path.join(KPLR_ROOT, "data")
try:
    os.makedirs(KPLR_DATA_DIR)
except os.error:
    pass


class API(object):

    ea_url = ("http://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI"
              "/nph-nstedAPI")
    mast_url = "http://archive.stsci.edu/kepler/{0}/search.php"

    def __init__(self, data_root=None):
        self.data_root = data_root
        if self.data_root is None:
            self.data_root = KPLR_DATA_DIR

    def ea_request(self, table, **params):
        """
        Submit a request to the API and return the JSON response.

        :param table:
            The table that you want to search.

        :param params:
            Any other search parameters.

        """
        params["table"] = table

        # Format the URL in the *horrifying* way that EA needs it to be.
        payload = ["{0}={1}".format(k, urllib.quote_plus(v, "\"'+"))
                   for k, v in params.items()]

        # Send the request.
        r = urllib2.Request(self.ea_url, data="&".join(payload))
        handler = urllib2.urlopen(r)
        code = handler.getcode()
        if int(code) != 200:
            raise RuntimeError("The Exoplanet Archive returned {0}"
                               .format(code))
        txt = handler.read()

        # Hack because Exoplanet Archive doesn't return HTTP errors.
        if "ERROR" in txt:
            raise RuntimeError("The Exoplanet Archive failed with message:\n"
                               + txt)

        # Parse the CSV output.
        csv = txt.splitlines()
        columns = csv[0].split(",")
        result = []
        for line in csv[1:]:
            result.append(dict(zip(columns, line.split(","))))

        return [self._munge_dict(row) for row in result]

    def mast_request(self, category, adapter=None, **params):
        """
        Submit a request to the API and return the JSON response.

        :param category:
            The table that you want to search.

        :param params:
            Any other search parameters.

        """
        params["action"] = params.get("action", "Search")
        params["outputformat"] = "JSON"
        params["coordformat"] = "dec"
        params["verb"] = 3
        if "sort" in params:
            params["ordercolumn1"] = params.pop("sort")

        # Send the request.
        r = urllib2.Request(self.mast_url.format(category),
                            data=urllib.urlencode(params))
        handler = urllib2.urlopen(r)
        code = handler.getcode()
        txt = handler.read()
        if int(code) != 200:
            raise RuntimeError("The MAST API returned {0} with message:\n {1}"
                               .format(code, txt))

        # Parse the JSON.
        result = json.loads(txt)

        # Fake munge the types if no adapter was provided.
        if adapter is None:
            return [self._munge_dict(row) for row in result]

        return [adapter(row) for row in result]

    def _munge_dict(self, row):
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
        Get a list of all the KOIs.

        """
        params["max_records"] = params.pop("max_records", 1000)

        # Submit the initial request.
        kois = self.request("koi", **params)
        if kois is None:
            raise StopIteration()

        # Yield each KOI as a generator.
        for k in kois:
            yield KOI(k)

    def koi(self, koi_number):
        """
        Find a single KOI given a KOI number (e.g. 145.01).

        """
        try:
            return self.kois(kepoi=koi_number).next()
        except StopIteration:
            raise ValueError("No KOI found with the number: '{0}'"
                             .format(koi_number))

    def planets(self, **params):
        """
        Get a list of all the confirmed planets.

        """
        planets = self.request("confirmed_planets", **params)

        if planets is None:
            raise StopIteration()

        for p in planets:
            yield Planet(p)

    def planet(self, name):
        """
        Get a planet by the Kepler name (e.g. "6b" or "Kepler-62b").

        """
        matches = re.findall("([0-9]+)[-\s]*([a-zA-Z])", name)
        if len(matches) != 1:
            raise ValueError("Invalid planet name '{0}'".format(name))
        kepler_name = "Kepler-{0} {1}".format(*(matches[0]))
        try:
            return self.planets(kepler_name=kepler_name, max_records=1).next()
        except StopIteration:
            raise ValueError("No planet found with the name: '{0}'"
                             .format(kepler_name))

    def stars(self, **params):
        """
        Get a list of KIC targets.

        """
        stars = self.request("kic10", **params)

        if stars is None:
            raise StopIteration()

        for s in stars:
            yield Star(s)

    def star(self, kepid):
        """
        Get a KIC target by id.

        """
        try:
            return self.stars(kic_kepler_id=kepid, max_records=1).next()
        except StopIteration:
            raise ValueError("No KIC target found with id: '{0}'"
                             .format(kepid))

    def data(self, kepler_id):
        """
        Get the :class:`bart.kepler.DataList` of observations associated with
        a particular Kepler ID.

        :param kepler_id:
            The Kepler ID.

        """
        data_list = self.request("data_search", ktc_kepler_id=kepler_id)
        if data_list is None:
            raise StopIteration()
        for d in data_list:
            yield _dataset(d)


class APIModel(object):

    _id = "{_id}"
    _parameters = {"_id": None}

    def __init__(self, params):
        params = dict(params)
        self._values = {}
        for k, v in self._parameters.iteritems():
            try:
                self._values[v[0]] = v[1](params.pop(k))
            except KeyError:
                logging.warn("Key '{0}' doesn't exist in MAST docs."
                             .format(k))
            except ValueError:
                self._values[v[0]] = None

        for k, v in self._values.iteritems():
            setattr(self, k, v)

        self._name = self._id.format(**self._values)

        if len(params):
            logging.debug("Unrecognized parameters: {0}"
                          .format(", ".join(params.keys())))

    def __str__(self):
        return "<{0}({1})>".format(self.__class__.__name__, self._name)

    def __unicode__(self):
        return self.__str__()

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, k):
        return self._values[k]

    def __getattr__(self, k):
        try:
            return self._values[k]
        except KeyError:
            raise AttributeError("{0} has no attribute '{1}'"
                                 .format(self.__class__.__name__, k))

    def keys(self):
        return self._values.keys()

    def iteritems(self):
        for k, v in self._values.iteritems():
            yield k, v


class KOI(APIModel):

    _id = "{kepoi}"

    def __init__(self, *args, **params):
        super(KOI, self).__init__(*args, **params)
        self._star = None

    @property
    def data(self):
        api = API()
        return api.data(self.kepid)

    @property
    def star(self):
        if self._star is None:
            api = API()
            self._star = api.star(self.kepid)
        return self._star


class Planet(APIModel):

    _id = "\"{kepler_name}\""
    @property
    def data(self):
        api = API()
        return api.data(self.kic_kepler_id)


class _dataset(APIModel):

    _id = "\"{sci_data_set_name}_{ktc_target_type}\""

    @property
    def _filename(self):
        suffix = "llc" if self.ktc_target_type == "LC" else "slc"
        return "{0}_{1}.fits".format(self.sci_data_set_name, suffix).lower()

    @property
    def filename(self):
        return os.path.join(KPLR_DATA_DIR, self._filename)

    @property
    def url(self):
        url = "http://archive.stsci.edu/pub/kepler/lightcurves/{0}/{1}/{2}"
        kid = "{0:09d}".format(int(self.ktc_kepler_id))
        return url.format(kid[:4], kid, self._filename)

    def fetch(self, clobber=False):
        # Check if the file already exists.
        filename = self.filename
        if os.path.exists(filename) and not clobber:
            logging.info("Found local file: '{0}'".format(filename))
            return self

        # Fetch the remote file.
        url = self.url
        logging.info("Downloading file from: '{0}'".format(url))
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        # Save the contents of the file.
        logging.info("Saving file to: '{0}'".format(filename))
        open(filename, "wb").write(r.content)

        return self
