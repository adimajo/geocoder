Using the Python package
========================

Installation
------------

The distribution name ``geocoder`` on PyPI belongs to an unrelated project: install this one from GitHub.

.. code-block:: shell

   pip install "geocoder[api] @ git+https://github.com/adimajo/geocoder.git"

The ``api`` extra adds the web server (Flask, gunicorn), the ``s3`` extra the support of an S3 storage for the data.

Building the database
---------------------

Before the first use, the BAN has to be downloaded and indexed (about 7 GB of disk are needed while building,
about 2 GB afterwards; estimates extrapolated from a build of four large départements):

.. code-block:: shell

   geocoder update      # download, decompress, index, spatial index; does nothing if the BAN did not change

or step by step: ``geocoder download``, ``decompress``, ``index``, ``reverse``, ``clean``.

Environment variables:

==============================  ==============================================================================
``GEOCODER_DATA_DIR``           where the BAN files and the database are stored (default: the package folder)
``GEOCODER_DEPARTEMENTS``       comma separated list of départements to use, e.g. ``75,92,2A`` (default: all)
``DEBUG``                       ``true``: only the département 01 and verbose logs (development, tests)
``SSL_VERIFICATION``            ``false`` disables TLS verification of the BAN download (not recommended)
``REQUESTS_CA_BUNDLE``          CA file for the download behind an inspecting proxy
``GEOCODER_DOWNLOAD_WORKERS``   number of parallel downloads (default 4)
``GEOCODER_INDEX_WORKERS``      number of processes building the database (default: number of CPUs)
``LOCAL_DB``                    ``false``: keep the BAN and the database in an S3 bucket (see ``S3_ENDPOINT_URL``,
                                ``S3_CA_BUNDLE``, standard ``AWS_*`` variables)
==============================  ==============================================================================

Searching
---------

.. code-block:: python

   import geocoder

   # complete search
   output = geocoder.find('91120', 'Palaiseau', '12, Bd des Maréchaux')
   print(output['longitude'], output['latitude'])  # 2.2099342 48.7099138
   print(output['quality'])  # 1 -> the search was successful

   # incomplete search and typos are fine
   geocoder.find('91120', None, '12, Bd des Maréchaux')['quality']  # 1
   geocoder.find('91120', 'Palaiau', '12, Bd des Maréchx')['quality']  # 1
   geocoder.find(None, 'Palaiseau', '12, Bd des Maréchaux')['quality']  # 1

   # reverse search: the nearest address of a (longitude, latitude)
   output = geocoder.near((2.2099, 48.7099))
   output['commune']['nom'], output['voie']['nom']  # PALAISEAU, BOULEVARD DES MARECHAUX

The ``quality`` of an answer tells how precise it is:

====  ============================================================
1     successful
2     the street was found but not the number
3     the street was found, and there was no number in the input
4     the street was not found: position of the commune
5     the commune was not found: position of the postal code
6     nothing was found
====  ============================================================
