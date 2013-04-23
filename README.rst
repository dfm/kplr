kplr
====

Python bindings for the `MAST interface
<http://archive.stsci.edu/vo/mast_services.html>`_ to the `Kepler
<http://kepler.nasa.gov/>`_ dataset.

Installation
------------

You can install the module by running:

::

    pip install kplr

If you want to access the MAST API, you'll need the `requests
<http:python-requests.org>`_ module and if you want to load light curve data
sets, you'll need `numpy <http://www.numpy.org/>`_ and `pyfits
<http://pythonhosted.org/pyfits/>`_.

Usage
-----

You'll access the API using a ``kplr.API`` object:

.. code-block:: python

    import kplr
    client = kplr.API()

To get information about the planet "Kepler 62b" (for example), you would run
the command:

.. code-block:: python

    planet = client.planet("62b")  # or "Kepler-62 b"

This object has a lot of attributes (with names given by the `MAST
documentation
<http://archive.stsci.edu/search_fields.php?mission=kepler_candidates>`_)
such as a period:

.. code-block:: python

    print(planet.koi_period)
    # 5.715

For some reason, the KOI table tends to have more precise measurements so
we can look at that instead:

.. code-block:: python

    koi = planet.koi
    print("{0.koi_period} ± {0.koi_period_err1}".format(koi))
    # 5.71493 ± 0.00019

The attributes of the KOI object are given in the `MAST description of the
kepler/koi table
<http://archive.stsci.edu/search_fields.php?mission=kepler_koi>`_.
You can also directly query the KOI table using:

.. code-block:: python

    koi = client.koi("256.01")

To download all the data for this KOI (or equivalently, the above planet),
you can try:

.. code-block:: python

    datasets = [dataset.fetch() for dataset in koi.data]

This will download the FITS files containing the light curves to the directory
given by the ``KPLR_DATA_DIR`` environment variable (or ``~/.kplr/data`` by
default). To load one of the files, you'll need to make sure that you have
`pyfits <http://pythonhosted.org/pyfits/>`_ installed and then you can use the
``Dataset`` object:

.. code-block:: python

    data = kplr.Dataset(datasets[0].filename)
