#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["API", "KOI", "Planet"]

import os
import re
import logging

try:
    import requests
except ImportError:
    requests = None

from .config import KPLR_ROOT

# Root directory for local data.
KPLR_DATA_DIR = os.path.join(KPLR_ROOT, "data")

try:
    os.makedirs(KPLR_DATA_DIR)
except os.error:
    pass


class API(object):

    base_url = "http://archive.stsci.edu/kepler/{0}/search.php"

    def __init__(self):
        if not requests:
            raise ImportError("The requests module is required to interface "
                              "with the MAST API.")

    def request(self, category, **params):
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

        r = requests.get(self.base_url.format(category), params=params)
        logging.info("Fetching URL: '{0}'".format(r.url))

        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        try:
            return r.json()

        except ValueError:
            return None

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
    _parameters = {
        "Kepler ID": ("kepid", int),
        "KOI Name": ("kepoi_name", unicode),
        "KOI Number": ("kepoi", unicode),
        "Kepler Disposition": ("koi_pdisposition", unicode),
        "NExScI Disposition": ("koi_disposition", unicode),
        "RA (J2000)": ("degree_ra", float),
        "Dec (J2000)": ("degree_dec", float),
        "Time of Transit Epoch": ("koi_time0bk", float),
        "Time err1": ("koi_time0bk_err1", float),
        "Time_err2": ("koi_time0bk_err2", float),
        "Period": ("koi_period", float),
        "Period err1": ("koi_period_err1", float),
        "Period err2": ("koi_period_err2", float),
        "Transit Depth": ("koi_depth", float),
        "Depth err1": ("koi_depth_err1", float),
        "Depth err2": ("koi_depth_err2", float),
        "Duration": ("koi_duration", float),
        "Duration err1": ("koi_duration_err1", float),
        "Duration err2": ("koi_duration_err2", float),
        "Ingress Duration": ("koi_ingress", float),
        "Ingress err1": ("koi_ingress_err1", float),
        "Ingress err2": ("koi_ingress_err2", float),
        "Impact Parameter": ("koi_impact", float),
        "Impact Parameter err1": ("koi_impact_err1", float),
        "Impact Parameter err2": ("koi_impact_err2", float),
        "Inclination": ("koi_incl", float),
        "Inclination err1": ("koi_incl_err1", float),
        "Inclination err2": ("koi_incl_err2", float),
        "Semi-major Axis": ("koi_sma", float),
        "Semi-major Axus err1": ("koi_sma_err1", float),
        "Semi-major Axis err2": ("koi_sma_err2", float),
        "Eccentricity": ("koi_eccen", float),
        "Eccentricity err1": ("koi_eccen_err1", float),
        "Eccentricity err2": ("koi_eccen_err2", float),
        "Long of Periastron": ("koi_longp", float),
        "Long err1": ("koi_longp_err1", float),
        "Long err2": ("koi_longp_err2", float),
        "r/R": ("koi_ror", float),
        "r/R err1": ("koi_ror_err1", float),
        "r/R err2": ("koi_ror_err2", float),
        "a/R": ("koi_dor", float),
        "a/R err1": ("koi_dor_err1", float),
        "a/R err2": ("koi_dor_err2", float),
        "Planet Radius": ("koi_prad", float),
        "Planet Radius err1": ("koi_prad_err1", float),
        "Planet Radius err2": ("koi_prad_err2", float),
        "Teq": ("koi_teq", int),
        "Teq err1": ("koi_teq_err1", int),
        "Teq err2": ("koi_teq_err2", int),
        "Teff": ("koi_steff", int),
        "Teff err1": ("koi_steff_err1", int),
        "Teff err2": ("koi_steff_err2", int),
        "log(g)": ("koi_slogg", float),
        "log(g) err1": ("koi_slogg_err1", float),
        "log(g) err2": ("koi_slogg_err2", float),
        "Metallicity": ("koi_smet", float),
        "Metallicity err1": ("koi_smet_err1", float),
        "Metallicity err2": ("koi_smet_err2", float),
        "Stellar Radius": ("koi_srad", float),
        "Stellar Radius err1": ("koi_srad_err1", float),
        "Stellar Radius err2": ("koi_srad_err2", float),
        "Stellar Mass": ("koi_smass", float),
        "Stellar Mass err2": ("koi_smass_err2", float),
        "Stellar Mass err1": ("koi_smass_err1", float),
        "Age": ("koi_sage", float),
        "Age err1": ("koi_sage_err1", float),
        "Age err2": ("koi_sage_err2", float),
        "Provenance": ("koi_sparprov", unicode),
        "Quarters": ("koi_quarters", unicode),
        "Limb Darkening Model": ("koi_limbdark_mod", unicode),
        "Limb Darkening Coeff1": ("koi_ldm_coeff1", float),
        "Limb Darkening Coeff2": ("koi_ldm_coeff2", float),
        "Limb Darkening Coeff3": ("koi_ldm_coeff3", float),
        "Limb Darkening Coeff4": ("koi_ldm_coeff4", float),
        "Transit Number": ("koi_num_transits", int),
        "Max single event sigma": ("koi_max_sngle_ev", float),
        "Max Multievent sigma": ("koi_max_mult_ev", float),
        "KOI count": ("koi_count", int),
        "Binary Discrimination": ("koi_bin_oedp_sig", float),
        "False Positive Bkgnd ID": ("koi_fp_bkgid", unicode),
        "J-band diff": ("koi_fp_djmag", unicode),
        "Comments": ("koi_comment", unicode),
        "Transit Model": ("koi_trans_mod", unicode),
        "Transit Model SNR": ("koi_model_snr", float),
        "Transit Model DOF": ("koi_model_dof", float),
        "Transit Model chisq": ("koi_model_chisq", float),
        "FWM motion signif.": ("koi_fwm_stat_sig", float),
        "gmag": ("koi_gmag", float),
        "gmag err": ("koi_gmag_err", float),
        "rmag": ("koi_rmag", float),
        "rmag err": ("koi_rmag_err", float),
        "imag": ("koi_imag", float),
        "imag err": ("koi_imag_err", float),
        "zmag": ("koi_zmag", float),
        "zmag err": ("koi_zmag_err", float),
        "Jmag": ("koi_jmag", float),
        "Jmag err": ("koi_jmag_err", float),
        "Hmag": ("koi_hmag", float),
        "Hmag err": ("koi_hmag_err", float),
        "Kmag": ("koi_kmag", float),
        "Kmag err": ("koi_kmag_err", float),
        "kepmag": ("koi_kepmag", float),
        "kepmag err": ("koi_kepmag_err", float),
        "Delivery Name": ("koi_delivname", unicode),
        "FWM SRA": ("koi_fwm_sra", float),
        "FWM SRA err": ("koi_fwm_sra_err", float),
        "FWM SDec": ("koi_fwm_sdec", float),
        "FWM SDec err": ("koi_fwm_sdec_err", float),
        "FWM SRAO": ("koi_fwm_srao", float),
        "FWM SRAO err": ("koi_fwm_srao_err", float),
        "FWM SDeco": ("koi_fwm_sdeco", float),
        "FWM SDeco err": ("koi_fwm_sdeco_err", float),
        "FWM PRAO": ("koi_fwm_prao", float),
        "FWM PRAO err": ("koi_fwm_prao_err", float),
        "FWM PDeco": ("koi_fwm_pdeco", float),
        "FWM PDeco err": ("koi_fwm_pdeco_err", float),
        "Dicco MRA": ("koi_dicco_mra", float),
        "Dicco MRA err": ("koi_dicco_mra_err", float),
        "Dicco MDec": ("koi_dicco_mdec", float),
        "Dicco MDec err": ("koi_dicco_mdec_err", float),
        "Dicco MSky": ("koi_dicco_msky", float),
        "Dicco MSky err": ("koi_dicco_msky_err", float),
        "Dicco FRA": ("koi_dicco_fra", float),
        "Dicco FRA err": ("koi_dicco_fra_err", float),
        "Dicco FDec": ("koi_dicco_fdec", float),
        "Dicco FDec err": ("koi_dicco_fdec_err", float),
        "Dicco FSky": ("koi_dicco_fsky", float),
        "Dicco FSky err": ("koi_dicco_fsky_err", float),
        "Dikco MRA": ("koi_dikco_mra", float),
        "Dikco MRA err": ("koi_dikco_mra_err", float),
        "Dikco MDec": ("koi_dikco_mdec", float),
        "Dikco MDec err": ("koi_dikco_mdec_err", float),
        "Dikco MSky": ("koi_dikco_msky", float),
        "Dikco MSky err": ("koi_dikco_msky_err", float),
        "Dikco FRA": ("koi_dikco_fra", float),
        "Dikco FRA err": ("koi_dikco_fra_err", float),
        "Dikco FDec": ("koi_dikco_fdec", float),
        "Dikco FDec err": ("koi_dikco_fdec_err", float),
        "Dikco FSky": ("koi_dikco_fsky", float),
        "Dikco FSky err": ("koi_dikco_fsky_err", float),
        "Last Update": ("rowupdate", unicode),
    }

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
    _parameters = {
        "Planet Name": ("kepler_name", unicode),
        "Kepler ID": ("kepid", int),
        "KOI Name": ("kepoi_name", unicode),
        "Alt Name": ("alt_name", unicode),
        "KOI Number": ("koi_number", unicode),  # Just `koi` in API.
        "RA (J2000)": ("degree_ra", float),
        "RA Error": ("ra_err", float),
        "Dec (J2000)": ("degree_dec", float),
        "Dec Error": ("dec_err", float),
        "2mass Name": ("tm_designation", unicode),
        "Planet temp": ("koi_teq", int),
        "Planet Radius": ("koi_prad", float),
        "Transit duration": ("koi_duration", float),
        "Period": ("koi_period", float),
        "Period err1": ("koi_period_err1", float),
        "Ingress Duration": ("koi_ingress", float),
        "Impact Parameter": ("koi_impact", float),
        "Inclination": ("koi_incl", float),
        "Provenance": ("koi_sparprov", unicode),
        "a/R": ("koi_dor", float),
        "Transit Number": ("koi_num_transits", int),
        "Transit Model": ("koi_trans_mod", unicode),
        "Time of transit": ("koi_time0bk", float),
        "Time of transit err1": ("koi_time0bk_err1", float),
        "Transit Depth": ("koi_depth", float),
        "Semi-major Axis": ("koi_sma", float),
        "r/R": ("koi_ror", float),
        "r/R err1": ("koi_ror_err1", float),
        "Age": ("koi_sage", float),
        "Metallicity": ("koi_smet", float),
        "Stellar Mass": ("koi_smass", float),
        "Stellar Radius": ("koi_srad", float),
        "Stellar Teff": ("koi_steff", int),
        "Logg": ("koi_slogg", float),
        "KEP Mag": ("koi_kepmag", float),
        "g Mag": ("koi_gmag", float),
        "r Mag": ("koi_rmag", float),
        "i Mag": ("koi_imag", float),
        "z Mag": ("koi_zmag", float),
        "J Mag": ("koi_jmag", float),
        "H Mag": ("koi_hmag", float),
        "K Mag": ("koi_kmag", float),
        "KOI List": ("koi_list_flag", unicode),
        "Last Update": ("koi_vet_date", unicode),
    }

    def __init__(self, *args, **params):
        super(Planet, self).__init__(*args, **params)
        self._koi = None
        self._star = None

    @property
    def data(self):
        api = API()
        return api.data(self.kepid)

    @property
    def koi(self):
        if self._koi is None:
            api = API()
            self._koi = api.koi(self.koi_number)
        return self._koi

    @property
    def star(self):
        if self._star is None:
            api = API()
            self._star = api.star(self.kepid)
        return self._star


class Star(APIModel):

    _id = "\"{kic_kepler_id}\""
    _parameters = {
        "Kepler ID": ("kic_kepler_id", int),
        "RA (J2000)": ("kic_degree_ra", float),
        "Dec (J2000)": ("kic_dec", float),
        "RA PM (arcsec/yr)": ("kic_pmra", float),
        "Dec PM (arcsec/yr)": ("kic_pmdec", float),
        "u Mag": ("kic_umag", float),
        "g Mag": ("kic_gmag", float),
        "r Mag": ("kic_rmag", float),
        "i Mag": ("kic_imag", float),
        "z Mag": ("kic_zmag", float),
        "Gred Mag": ("kic_gredmag", float),
        "D51 Mag": ("kic_d51mag", float),
        "J Mag": ("kic_jmag", float),
        "H Mag": ("kic_hmag", float),
        "K Mag": ("kic_kmag", float),
        "Kepler Mag": ("kic_kepmag", float),
        "2MASS ID": ("kic_2mass_id", unicode),
        "2MASS Designation": ("kic_tmid", int),
        "SCP ID": ("kic_scpid", int),
        "Alt ID": ("kic_altid", int),
        "Alt ID Source": ("kic_altsource", int),
        "Star/Gal ID": ("kic_galaxy", int),
        "Isolated/Blend ID": ("kic_blend", int),
        "Var. ID": ("kic_variable", int),
        "Teff (deg K)": ("kic_teff", int),
        "Log G (cm/s/s)": ("kic_logg", float),
        "Metallicity (solar=0.0)": ("kic_feh", float),
        "E(B-V)": ("kic_ebminusv", float),
        "A_V": ("kic_av", float),
        "Radius (solar=1.0)": ("kic_radius", float),
        "Kepmag Source": ("kic_cq", unicode),
        "Photometry Qual": ("kic_pq", int),
        "Astrophysics Qual": ("kic_aq", int),
        "Catalog key": ("kic_catkey", int),
        "Scp Key": ("kic_scpkey", int),
        "Parallax (arcsec)": ("kic_parallax", float),
        "Gal Lon (deg)": ("kic_glon", float),
        "Gal Lat (deg)": ("kic_glat", float),
        "Total PM (arcsec/yr)": ("kic_pmtotal", float),
        "g-r color": ("kic_grcolor", float),
        "J-K color": ("kic_jkcolor", float),
        "g-K color": ("kic_gkcolor", float),
        "RA hours (J2000)": ("kic_ra", float),
    }

    @property
    def data(self):
        api = API()
        return api.data(self.kic_kepler_id)


class _dataset(APIModel):

    _id = "\"{sci_data_set_name}_{ktc_target_type}\""
    _parameters = {
        "Kepler ID": ("ktc_kepler_id", int),
        "Investigation ID": ("ktc_investigation_id", unicode),
        "Pep ID": ("sci_pep_id", int),
        "Dataset Name": ("sci_data_set_name", unicode),
        "Quarter": ("sci_data_quarter", int),
        "Data Release": ("sci_data_rel", int),
        "RA (J2000)": ("sci_ra", float),
        "Dec (J2000)": ("sci_dec", float),
        "Target Type": ("ktc_target_type", unicode),
        "Archive Class": ("sci_archive_class", unicode),
        "Ref": ("refnum", int),
        "Actual Start Time": ("sci_start_time", unicode),
        "Actual End Time": ("sci_end_time", unicode),
        "Release Date": ("sci_release_date", unicode),
        "RA PM": ("kic_pmra", float),
        "Dec PM": ("kic_pmdec", float),
        "U Mag": ("kic_umag", float),
        "G Mag": ("kic_gmag", float),
        "R Mag": ("kic_rmag", float),
        "I Mag": ("kic_imag", float),
        "Z Mag": ("kic_zmag", float),
        "GRed Mag": ("kic_gredmag", float),
        "D51 Mag": ("kic_d51mag", float),
        "J Mag": ("twoMass_jmag", float),
        "H Mag": ("twoMass_hmag", float),
        "K Mag": ("twoMass_kmag", float),
        "KEP Mag": ("kic_kepmag", float),
        "2MASS ID": ("twoMass_2mass_id", unicode),
        "2MASS Designation": ("twoMass_tmid", int),
        "twoMass conflict flag": ("twoMass_conflictFlag", unicode),
        "SCP ID": ("kic_scpid", int),
        "Alt ID": ("kic_altid", int),
        "Alt ID Source": ("kic_altsource", int),
        "Star/Gal ID": ("kic_galaxy", int),
        "Isolated/Blend ID": ("kic_blend", int),
        "Var. ID": ("kic_variable", int),
        "Teff": ("kic_teff", int),
        "Log G": ("kic_logg", float),
        "Metallicity": ("kic_feh", float),
        "E(B-V)": ("kic_ebminusv", float),
        "A_V": ("kic_av", float),
        "Radius": ("kic_radius", float),
        "Kepmag Source": ("kic_cq", unicode),
        "Photometry Qual": ("kic_pq", int),
        "Astrophysics Qual": ("kic_aq", int),
        "Catalog key": ("kic_catkey", int),
        "Scp Key": ("kic_scpkey", int),
        "Parallax": ("kic_parallax", float),
        "Gal Lon": ("kic_glon", float),
        "Gal Lat": ("kic_glat", float),
        "Total PM": ("kic_pmtotal", float),
        "G-R color": ("kic_grcolor", float),
        "J-K color": ("twoMass_jkcolor", float),
        "G-K color": ("twoMass_gkcolor", float),
        "Processing Date": ("sci_generation_date", unicode),
        "crowding": ("sci_crowdsap", float),
        "contamination": ("sci_contamination", float),
        "flux fraction": ("sci_flfrcsap", float),
        "cdpp3": ("sci_Cdpp3_0", float),
        "cdpp6": ("sci_Cdpp6_0", float),
        "cdpp12": ("sci_Cdpp12_0", float),
        "Module": ("sci_module", int),
        "Output": ("sci_output", int),
        "Channel": ("sci_channel", int),
        "Skygroup_ID": ("sci_skygroup_id", int),
        "Condition flag": ("condition_flag", unicode),
    }

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
