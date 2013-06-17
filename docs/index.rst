.. module:: kplr

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
Below, I'll describe the features provided by kplr but to get things
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


Table of Contents
-----------------

* `Installation`_
* `API Interface`_
    * `Kepler Objects of Interest`_
    * `Confirmed Planets`_
    * `Kepler Input Catalog Targets`_
    * `Datasets`_
* `Data Access`_

For a detailed description of the Python bindings see the Python API
documentation:

.. toctree::
   :maxdepth: 2

   api


Installation
------------

You can install kplr using the standard Python packaging tool `pip
<http://www.pip-installer.org/>`_:

.. code-block:: bash

    pip install kplr

or (if you must) `easy_install <https://pypi.python.org/pypi/setuptools>`_:

.. code-block:: bash

    easy_install kplr

The development version can be installed using pip:

.. code-block:: bash

    pip install -e git+https://github.com/dfm/kplr#egg=kplr-dev

or by cloning the `GitHub repository <https://github.com/dfm/kplr>`_:

.. code-block:: bash

    git clone https://github.com/dfm/kplr.git
    cd kplr
    python setup.py install


API Interface
-------------

The basic work flow for interacting with the APIs starts by initializing an
:class:`API` object:

.. code-block:: python

    import kplr
    client = kplr.API()

Then, this object provides methods for constructing various queries to find

* `Kepler objects of interest`_,
* `confirmed planets`_,
* `Kepler input catalog targets`_, and
* `datasets`_.

Kepler Objects of Interest
^^^^^^^^^^^^^^^^^^^^^^^^^^

The kplr KOI search interfaces with `The Exoplanet Archive API
<http://exoplanetarchive.ipac.caltech.edu/docs/program_interfaces.html>`_ to
return the most up to date information possible. In particular, it searches
the `cumulative table
<http://exoplanetarchive.ipac.caltech.edu/docs/API_kepcandidate_columns.html>`_.
As shown in the sample code at the top of this page, it is very easy to
retrieve the listing for a single :class:`KOI`:

.. code-block:: python

    koi = client.koi(952.01)

Note the ``.01`` in the KOI ID. This is required because a KOI is specified by
the full number (not just ``952`` which will fail).
The object will have an attribute for each column listed in the `Exoplanet
Archive documentation
<http://exoplanetarchive.ipac.caltech.edu/docs/API_kepcandidate_columns.html>`_.
For example, the period and error bars (positive and negative respectively)
are given by

.. code-block:: python

    print(koi.koi_period, koi.koi_period_err1, koi.koi_period_err2)

For KOI 952.01, this result will print ``5.901269, 1.7e-05, -1.7e-05``.

Finding a set of KOIs that satisfy search criteria is a little more
complicated because you must provide syntax that is understood by the
Exoplanet Archive. For example, to find all the KOIs with period longer than
200 days, you would run

.. code-block:: python

    kois = client.kois(where="koi_period>200")

At the time of writing, this should return 224 :class:`KOI` objects.

Confirmed Planets
^^^^^^^^^^^^^^^^^



Kepler Input Catalog Targets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



Datasets
^^^^^^^^


