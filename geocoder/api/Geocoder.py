"""
implementation of class Geocoder which will deal with requests
"""
import math
import uuid
from datetime import datetime, timezone

import geocoder
from geocoder.columns import ADDRESS, CITY, POSTAL_CODE

REQUIRED_COLUMNS = (ADDRESS, POSTAL_CODE, CITY)
OUTPUT_COLUMNS = ("lon", "lat", "quality", "code_insee")


def _clean(value):
    """
    Turns a user supplied value into something :code:`geocoder.find` understands (a string or None)

    Numbers are accepted for convenience (a postal code sent as a JSON number), missing values become None.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float):
        return None if math.isnan(value) else str(int(value)) if value.is_integer() else str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    return None


class Geocoder:
    """
    class to handle geocoding of addresses through API
    """

    def __init__(self, data_to_geocode):
        """
        Initialize geocoder with data and utility attributes

        :param list data_to_geocode: list of dicts, each one containing
            :code:`{"address": "...", "postal_code": "...", "city": "..."}`; further keys are returned untouched
        """
        self.errors = []
        self.geocoded = False
        self.uuid = str(uuid.uuid4())
        self.data = data_to_geocode
        self.geocoded_date_time = None
        self.check_data_to_geocode()

    def get_geocoded_date_time(self):
        return self.geocoded_date_time

    def get_geocoded_data(self):
        """
        Returns the object's data attribute

        :return: list of records if already geocoded otherwise None
        :rtype: list
        """
        if self.geocoded:
            return self.data
        return None  # pragma: no cover

    def check_data_to_geocode(self):
        """
        Checks input data and increment :code:`errors` attribute
        """
        if not isinstance(self.data, list):
            self.errors = ["The input must be a JSON list of objects."]
            return
        if not all(isinstance(row, dict) for row in self.data):
            self.errors = ["The input must be a JSON list of objects."]
            return
        present = set().union(*(row.keys() for row in self.data)) if self.data else set()
        self.errors = [f"Column {col} is missing." for col in REQUIRED_COLUMNS if col not in present]

    def has_errors(self):
        return bool(self.errors)

    def get_errors(self):
        return self.errors

    def geocode(self):
        """
        Geocode data if not already geocoded and no read error(s) by calling geocoder.find

        Identical (postal code, city, address) triplets are only searched once.
        """
        if self.geocoded or self.errors:
            return
        cache = {}
        records = []
        for row in self.data:
            args = (_clean(row.get(POSTAL_CODE)), _clean(row.get(CITY)), _clean(row.get(ADDRESS)))
            if args not in cache:
                cache[args] = self._find(*args)
            lon, lat, quality, code_insee = cache[args]
            records.append({**row, "lon": lon, "lat": lat, "quality": quality, "code_insee": code_insee})
        self.data = records
        self.geocoded_date_time = datetime.now(timezone.utc)
        self.geocoded = True

    @staticmethod
    def _find(postal_code, city, address):
        if postal_code == "98000":  # Monaco is not covered by the BAN
            return None, None, None, None
        res = geocoder.find(postal_code or None, city or None, address or None)
        return (res.get("longitude"), res.get("latitude"), res.get("quality"),
                (res.get("commune") or {}).get("code_insee"))
