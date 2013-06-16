A Python interface to the Kepler data
=====================================

Python bindings for the `MAST interface
<http://archive.stsci.edu/vo/mast_services.html>`_ to the `Kepler
<http://kepler.nasa.gov/>`_ dataset.

.. code-block::

    import kplr
    client = kplr.API()
    koi = client.koi(952.01)
    print(koi.koi_period)

Installation
------------

You can install the module by running:

::

    pip install kplr

If you want to access the MAST API, you'll need the `requests
<http:python-requests.org>`_ module and if you want to load light curve data
sets, you'll need `numpy <http://www.numpy.org/>`_ and `pyfits
<http://pythonhosted.org/pyfits/>`_.
