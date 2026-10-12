Deployment
==========

Docker
------

Images are published to the GitHub container registry: ``ghcr.io/adimajo/geocoder`` (``edge`` follows ``master``,
``X.Y.Z`` and ``latest`` follow the releases).

.. code-block:: shell

   docker run -d -p 8000:8000 -v geocoder-data:/data ghcr.io/adimajo/geocoder

At start, the container downloads the BAN and builds the database in ``/data`` when needed (a few tens of minutes for
all of France the first time, nothing when the BAN has not changed), then serves the API on port 8000. Keep the
``/data`` volume between runs. Set ``GEOCODER_DEPARTEMENTS=75,92`` to only serve some départements,
``GEOCODER_SKIP_UPDATE=true`` to skip the update step (database prepared in advance). Further arguments are passed to
``geocoder runserver``.

The image runs as a non-root user and works with a read-only root filesystem (only ``/data`` is written).
Count about 7 GB of disk for the volume while the database is being built (about 2 GB afterwards) and a few GB of
memory for all of France (the database is memory-mapped; building it uses one process per CPU, set
``GEOCODER_INDEX_WORKERS`` lower if memory is short). These figures are estimates extrapolated from a build of four
large départements.

Building the image yourself:

.. code-block:: shell

   docker build -t geocoder .

Releases
--------

Pushing a ``vX.Y.Z`` tag (the same version as ``geocoder/__init__.py``) builds, scans and pushes the multi-arch
image and creates a GitHub release with the wheel and the source distribution. Every push to ``master`` updates the
``edge`` image.

Documentation
-------------

This documentation is built by the *Documentation* GitHub Actions workflow and published to GitHub Pages
(*Settings > Pages > Source: GitHub Actions*). To build it locally:

.. code-block:: shell

   uv sync --extra api --group docs
   uv run sphinx-build -W -b html docs/source docs/build/html
