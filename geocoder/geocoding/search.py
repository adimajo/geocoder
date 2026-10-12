"""Definition of the search methods.

This module defines the logic of the two most relevant methods of this package:
the position method and the reverse method.
"""
from geocoder.geocoding import normalize, query, result


def preprocessing(code_postal, commune, adresse):
    """First processing of the input from the position method.

    Convert postal code to int, normalize the city name and separate number
    and street from adresse.

    Args:
        code_postal (str): The postal code.
        commune (str): The city name.
        adresse(str): Address with number and street name.

    Returns:
        tuple: the postal code (int), the normalized city name (str), the street number (int), the normalized street
        name (str) and the type of street (str).

    """
    # Try to convert postal code to int.
    if isinstance(code_postal, str):
        try:
            code_postal = int(code_postal)
        except ValueError:
            code_postal = None
    else:
        code_postal = None

    # Normalize city.
    if isinstance(commune, str):
        commune = normalize.uniform_commune(commune)
    else:
        commune = None

    # Retrieve the number and street from address and normalize street name.
    numero, voie, voie_type = None, None, None
    if isinstance(adresse, str):
        numero, voie, voie_type = normalize.mine(adresse)

    return code_postal, commune, numero, voie, voie_type


def position(code_postal=None, commune=None, adresse=None):
    """Find the position over the surface of the Earth of the given address.

    Args:
        code_postal (str): The postal code.
        commune (str): The city name.
        adresse (str): Address with number and street name.

    Returns:
        dict: the keys are ``departement`` (``code``), ``postal`` (``code``), ``commune`` (``nom``, ``code_insee``),
        ``voie`` (``nom``), ``localisation`` (``numero``), ``longitude`` and ``latitude`` (floats) and ``quality``
        (int, see the documentation of the package).

    """
    query.setup()

    # Input preprocessing.
    code_postal, commune, numero, voie, voie_type = \
        preprocessing(code_postal, commune, adresse)

    # Try to find postal code.
    postal_id = query.select_code_postal(code_postal)

    # Try to find city.
    commune_id = query.select_commune(postal_id, commune)
    if commune_id is None:
        commune_id = query.complete_commune_selection(commune)

    # Try to find street.
    voie_id = query.select_voie(commune_id, voie, voie_type)
    if voie_id is None and commune_id is None:
        # a postal code shared by several communes and no commune: look for the street in all of them
        voie_id = query.select_voie_in_postal(postal_id, voie)
    if voie_id is None:
        voie_id = query.complete_voie_selection(code_postal, commune, voie)

    # Try to find number.
    localisation_id = query.select_localisation(voie_id, numero)

    # Prepare the output.
    if localisation_id is not None:
        # Quality = 1 -> The search was successful.
        status, quality = ('localisation', localisation_id), 1

    elif voie_id is not None:
        status = ('voie', voie_id)
        # Quality = 2 -> The precise number was not found.
        # Quality = 3 -> The precise number was not found and there was no
        #                number in the input.
        quality = 3 if numero is None else 2

    elif commune_id is not None:
        # Quality = 4 -> The street was not found.
        status, quality = ('commune', commune_id), 4

    elif postal_id is not None:
        # Quality = 5 -> The commune was not found.
        status, quality = ('postal', postal_id), 5

    else:
        # Quality = 6 -> Nothing was found.
        status, quality = None, 6

    return result.get_output(status, quality)


def _valid_position(position):
    try:
        lon, lat = (float(coordinate) for coordinate in position)
    except (TypeError, ValueError):
        return False
    return -180 <= lon <= 180 and -90 <= lat <= 90  # False for NaN


def reverse(position):
    """Finds the nearest address in France to a given position over the Earth.

    Args:
        position (:obj:`tuple` of float): Longitude and latitude of the in this
            order.

    Returns:
        dict: the keys are ``departement`` (``code``), ``postal`` (``code``), ``commune`` (``nom``, ``code_insee``),
        ``voie`` (``nom``), ``localisation`` (``numero``), ``longitude`` and ``latitude`` (floats) and ``quality``
        (int, see the documentation of the package).

    """
    query.setup()
    if not _valid_position(position):
        return result.get_output(None, 6)
    localisation_id, dist = query.nearest_point_from(position)
    return result.get_output(('localisation', localisation_id), 1)
