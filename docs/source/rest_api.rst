REST API
========

.. code-block:: shell

   geocoder runserver --host 127.0.0.1 --port 8000 --workers 4

The interactive documentation (Swagger) is served at ``/doc`` and a small demo page at ``/home``.

``GET /geocode/<address>/<postal_code>/<city>``
    Geocodes one address.

``POST /geocode_file``
    Geocodes a JSON list of addresses; the other keys of each object are returned untouched.

    .. code-block:: shell

       curl --header "Content-Type: application/json" --request POST \
         --data '[{"address": "12, Bd des Maréchaux", "postal_code": "91120", "city": "Palaiseau"}]' \
         http://localhost:8000/geocode_file

    The answer contains ``data`` (the input rows with ``lon``, ``lat``, ``quality`` and ``code_insee``), ``quality``
    (the meaning of each quality value), ``uuid``, ``geocoded_time`` and ``api_version``. Missing positions are
    ``null``. Invalid input is answered with ``400`` and ``{"errors": [...]}``, too large requests with ``413``.

``GET /version``
    Version of the service (usable as a health check).

Settings:

================================  ==============================================================================
``GEOCODER_MAX_ROWS``             maximum number of addresses per ``/geocode_file`` request (default 10000)
``GEOCODER_MAX_CONTENT_LENGTH``   maximum size of a request body in bytes (default 10 MiB)
``GEOCODER_HOST`` / ``_PORT``     address the server listens on (default ``127.0.0.1:8000``)
``GEOCODER_WORKERS``              number of gunicorn workers; the database is memory-mapped, so it is shared
``GEOCODER_TIMEOUT``              gunicorn worker timeout in seconds (default 120)
``GEOCODER_TILE_URL``             raster tiles of the demo map, default OpenStreetMap
                                  (``https://tile.openstreetmap.org/{z}/{x}/{y}.png``); follow the usage policy of
                                  the tile server you choose
``FLASK_DEBUG``                   ``1`` enables the Flask debugger; never expose it
================================  ==============================================================================

.. warning::

   The API has no authentication and no rate limiting. Put it behind a reverse proxy or an API gateway if it is
   reachable by anyone you do not trust.
