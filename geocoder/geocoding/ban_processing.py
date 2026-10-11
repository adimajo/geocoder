"""
process decompressed files into a database

.. autosummary::
    test
    get_gield
    get_voie
    get_commune
    get_attributes
    update
    update_departement
    update_postal
    update_commune
    update_voie
    update_localisation
"""
import os
from typing import Literal

import numpy as np
from loguru import logger
from sortedcontainers import SortedDict, SortedSet

from geocoder.geocoding import normalize as norm
from geocoder.geocoding.utils import degree_to_int

line_specs = {
    "adresses": {
        "nom_voie": 4,
        "numero": 2,
        "repetition": 3,
        "code_insee": 6,
        "code_postal": 5,
        "longitude": 12,
        "latitude": 13,
        "nom_commune": 7,
        "nom_complementaire": 16},
    "lieux-dits": {
        "nom_voie": 1,  # is actually nom_lieu_dit
        "numero": None,
        "repetition": None,
        "code_insee": 3,
        "code_postal": 2,
        "longitude": 9,
        "latitude": 10,
        "nom_commune": 4,
        "nom_complementaire": None}
}

types = {
    "code_postal": int,
    "numero": int,
    "longitude": float,
    "latitude": float
}

voie_fields = ['nom_voie']

commune_fields = ['nom_commune', 'nom_complementaire']


def test(fields: list, lieu: Literal["adresses", "lieux-dits"]):
    """
    Checks if fields are of correct type

    :param list fields: extracted fields
    :param str lieu: adresses or lieux-dits
    :rtype: bool
    """
    for field in types:
        if lieu == "lieux-dits" and field == "numero":
            continue
        try:
            types[field](fields[line_specs[lieu][field]])
        except ValueError:
            logger.debug(f"Error reading {field}")
            logger.debug(f"Line: {fields}")
            logger.debug(f"Type of lieu: {lieu}")
            logger.debug(f"Field: {line_specs[lieu][field]}")
            return False
    return True


def get_field(field_name, fields, normalization_method, lieu: Literal["adresses", "lieux-dits"], size_limit=None):
    """
    Gets field and try to normalize

    :param str field_name: name of the field to parse
    :param list fields: all fields obtained
    :param fun normalization_method: function to normalize the parsed string
    :param str lieu: adresses or lieux-dits
    :param int size_limit: max length of resulting string
    :rtype: (str, str)
    """
    field = line_specs[lieu][field_name]
    if field is None:  # pragma: no cover
        return None, None
    text = fields[field].replace('"', '')
    normalise = normalization_method(text)
    if len(normalise) > 0:
        nom = norm.remove_separators(norm.uniform(text))
        if size_limit is None or len(nom) <= size_limit:
            return nom, normalise
    return None, None


def get_voie(fields, lieu: Literal["adresses", "lieux-dits"]):
    """
    Gets "voie" by calling :code:`get_field`
    """
    for field_name in voie_fields:
        voie_nom, voie_normalise = get_field(field_name,
                                             fields,
                                             norm.uniform_adresse,
                                             lieu,
                                             47)
        if voie_normalise is not None:
            return voie_nom, voie_normalise
    return None, None  # pragma: no cover


def get_commune(fields, lieu: Literal["adresses", "lieux-dits"]):
    """
    Gets "commune" by calling :code:`get_field`
    """
    for field_name in commune_fields:
        commune_nom, commune_normalise = get_field(field_name,
                                                   fields,
                                                   norm.uniform_commune,
                                                   lieu)
        if commune_normalise is not None:
            return commune_nom, commune_normalise
    return None, None  # pragma: no cover


def get_attributes(fields, lieu: Literal["adresses", "lieux-dits"] = "adresses"):
    """
    Parse attributes from fields

    :param list fields: all fields obtained
    :param str lieu: adresses or lieux-dits
    :rtype: tuple
    """
    if not test(fields, lieu):
        return None  # pragma: no cover

    commune_nom, commune_normalise = get_commune(fields, lieu)
    if commune_nom is None:
        logger.debug("Error reading commune")
        logger.debug(f"Line: {fields}")
        logger.debug(f"Type of lieu: {lieu}")
        return None  # pragma: no cover

    voie_nom, voie_normalise = get_voie(fields, lieu)
    if voie_nom is None:
        logger.debug("Error reading voie")
        logger.debug(f"Line: {fields}")
        logger.debug(f"Type of lieu: {lieu}")
        return None  # pragma: no cover

    code_insee = fields[line_specs[lieu]['code_insee']]
    code_postal = int(fields[line_specs[lieu]['code_postal']])
    lon = degree_to_int(fields[line_specs[lieu]['longitude']])
    lat = degree_to_int(fields[line_specs[lieu]['latitude']])
    if lon is None or lat is None:
        return None

    try:
        numero = int(fields[line_specs[lieu]['numero']])
        repetition = fields[line_specs[lieu]['repetition']].replace('"', '')
    except TypeError:  # pragma: no cover
        numero, repetition = 0, None

    return (code_postal, commune_normalise, commune_nom, code_insee,
            voie_normalise, voie_nom, numero, repetition, lon, lat)


def update(dpt_nom: str, csv_file_paths, processed_files: dict):
    """
    Update processed_files with all the files of one département

    The "adresses" and the "lieux-dits" files of a département must be merged before being indexed: otherwise a
    postal code appears twice in the database and a search restricted to that postal code only looks into one of the
    two sets of streets.

    :param str dpt_nom: departement
    :param csv_file_paths: path(s) to the CSV file(s) to read and add to processed_files
    :param dict processed_files: databases
    """
    if isinstance(csv_file_paths, (str, os.PathLike)):
        csv_file_paths = [csv_file_paths]
    postal_dict = SortedDict()

    for csv_file_path in sorted(csv_file_paths):
        lieu = "lieux-dits" if "lieux-dits" in os.path.basename(csv_file_path) else "adresses"
        with open(csv_file_path, encoding='UTF-8') as f:
            try:  # some lieux-dits might be empty
                next(f)
            except StopIteration:  # pragma: no cover
                logger.debug(f"{csv_file_path} was empty")
                continue
            for line in f:
                attributes = get_attributes(line.strip().split(';'), lieu)
                if attributes is None:
                    logger.debug("Failed to parse line")
                    continue
                postal_key = attributes[:1]
                commune_key = attributes[1:4]
                voie_key = attributes[4:6]
                localisation = attributes[6:]

                commune_dict = postal_dict.setdefault(postal_key, SortedDict())
                voie_dict = commune_dict.setdefault(commune_key, SortedDict())
                voie_dict.setdefault(voie_key, SortedSet()).add(localisation)

    update_departement(dpt_nom, processed_files, postal_dict)


def update_departement(dpt_nom, processed_files, postal_dict):
    current_id = len(processed_files['departement'])

    start = len(processed_files['postal'])
    update_postal(current_id, processed_files, postal_dict)
    end = len(processed_files['postal'])

    processed_files['departement'].append((dpt_nom, start, end))


def update_postal(id_ref, processed_files, postal_dict):
    for key in postal_dict.keys():
        current_id = len(processed_files['postal'])

        start = len(processed_files['commune'])
        logger.debug(key)
        logger.debug(postal_dict[key])
        update_commune(current_id, processed_files, postal_dict[key])
        end = len(processed_files['commune'])

        tuple_value = key + (start, end, id_ref)
        processed_files['postal'].append(tuple_value)


def update_commune(id_ref, processed_files, commune_dict):
    for key in commune_dict.keys():
        current_id = len(processed_files['commune'])

        start = len(processed_files['voie'])
        logger.debug(key)
        logger.debug(commune_dict[key])
        update_voie(current_id, processed_files, commune_dict[key])
        end = len(processed_files['voie'])

        localisation_list = [value for k, value in commune_dict[key].items()]
        lon, lat = tuple_list_mean(localisation_list, range(2))
        if lon is None or lat is None:
            logger.error(localisation_list)

        tuple_value = key + (lon, lat, start, end, id_ref)
        processed_files['commune'].append(tuple_value)


def update_voie(id_ref, processed_files, voie_dict):
    for key in voie_dict.keys():
        current_id = len(processed_files['voie'])

        start = len(processed_files['localisation'])
        logger.debug(key)
        logger.debug(voie_dict[key])
        update_localisation(current_id, processed_files, voie_dict[key])
        lon, lat = tuple_list_mean(voie_dict[key], range(2, 4))
        if lon is None or lat is None:
            logger.error(voie_dict[key])
        end = len(processed_files['localisation'])

        tuple_value = key + (lon, lat, start, end, id_ref)
        processed_files['voie'].append(tuple_value)

        # Gambiarra - não me orgulho disso
        voie_dict[key] = (lon, lat)


def update_localisation(id_ref, processed_files, localisation_set):
    for localisation in localisation_set:
        tuple_value = localisation + (id_ref, )
        if localisation[0] is None:
            logger.error(localisation)
            logger.error(localisation_set)
            # raise ValueError
        processed_files['localisation'].append(tuple_value)


def tuple_list_mean(tuple_list, indices):
    return (int(np.mean([int(value[index]) for value in tuple_list]))
            for index in indices)
