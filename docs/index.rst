A Python interface to the Kepler data
=====================================

If you're here, then you probably already know about the `Kepler mission
<http://kepler.nasa.gov/>`_. You probably also know that it can be a bit of a
pain to get access to this public dataset. As I understand things, the
canonical source for a catalog of planet candidates—or more precisely Kepler
Objects of Interest (KOIs)—is the `NASA Exoplanet Archive
<http://exoplanetarchive.ipac.caltech.edu/>`_ but the data is available
through `MAST <http://archive.stsci.edu/>`_. There are programmatic interfaces
(APIs) available for both of these services but it can still be frustrating to
interact with them in an automated way. That's why I made **kplr**.

**kplr** provides a lightweight Pythonic interface to the catalogs and data.
Below, I'll describe the features provided by **kplr** but to get things
started, let's see an example of how you would go about finding the published
parameters of a KOI and download the light curve data.

.. code-block:: python

    import kplr
    client = kplr.API()

    # Find a KOI.
    koi = client.koi(952.01)
    print(koi.koi_period)

    # This KOI has an associated star.
    star = koi.star
    print(star.kic_teff)

    # Download the lightcurves for this KOI.
    lightcurves = koi.get_light_curves()
    for lc in lightcurves:
        print(lc.filename)

Installation
------------

You can install the module by running:

.. code-block:: bash

    pip install kplr

If you want to access the MAST API, you'll need the `requests
<http:python-requests.org>`_ module and if you want to load light curve data
sets, you'll need `numpy <http://www.numpy.org/>`_ and `pyfits
<http://pythonhosted.org/pyfits/>`_.
