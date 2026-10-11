"""
geocoder modules and API

.. autosummary::
    :toctree:

    api
    geocoding
    wsgi
"""
from geocoder.geocoding import search

__version__ = "2.1.23"

find = search.position
near = search.reverse
