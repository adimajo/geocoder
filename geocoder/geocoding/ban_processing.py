"""
process decompressed files into a database

A département is processed on its own into numpy tables whose cross references (:code:`start`, :code:`end`,
:code:`ref_id`) are local to the département; :func:`geocoder.geocoding.index.merge` shifts them when the
départements are put side by side.

.. autosummary::
    get_attributes
    read_files
    build_tables
    process_departement
"""
import os
from functools import lru_cache

import numpy as np
from loguru import logger

from geocoder.geocoding import normalize as norm
from geocoder.geocoding.datatypes import dtypes
from geocoder.geocoding.utils import degree_to_int

# column index of each field in the two kinds of files
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

VOIE_SIZE_LIMIT = 47  # size of the "normalise" column of the voie table
MAX_NUMERO = np.iinfo(np.int16).max  # size of the "numero" column of the localisation table
CACHE_SIZE = 1 << 20


@lru_cache(maxsize=CACHE_SIZE)
def commune_names(nom_commune, nom_complementaire):
    """
    Names of a commune as (name, normalized name): the first of the two fields that is not empty once normalized

    :rtype: tuple
    """
    for text in (nom_commune, nom_complementaire):
        if text is None:
            continue
        text = text.replace('"', '')
        normalise = norm.uniform_commune(text)
        if normalise:
            return norm.remove_separators(norm.uniform(text)), normalise
    return None, None


@lru_cache(maxsize=CACHE_SIZE)
def voie_names(text):
    """
    Names of a street as (name, normalized name), (None, None) if it is empty or too long

    :rtype: tuple
    """
    text = text.replace('"', '')
    normalise = norm.uniform_adresse(text)
    if normalise:
        nom = norm.remove_separators(norm.uniform(text))
        if len(nom) <= VOIE_SIZE_LIMIT:
            return nom, normalise
    return None, None


def get_attributes(fields, lieu="adresses"):
    """
    Parse the attributes of a line

    :param list fields: all fields of the line
    :param str lieu: adresses or lieux-dits
    :return: (code_postal, commune_normalise, commune_nom, code_insee, voie_normalise, voie_nom, numero, repetition,
        longitude, latitude) or None if the line is not usable
    :rtype: tuple
    """
    spec = line_specs[lieu]
    try:
        code_postal = int(fields[spec['code_postal']])
        lon = degree_to_int(fields[spec['longitude']])
        lat = degree_to_int(fields[spec['latitude']])
        if spec['numero'] is None:
            numero, repetition = 0, ''
        else:
            numero = int(fields[spec['numero']])
            repetition = fields[spec['repetition']].replace('"', '')
        nom_complementaire = fields[spec['nom_complementaire']] if spec['nom_complementaire'] is not None else None
        commune_nom, commune_normalise = commune_names(fields[spec['nom_commune']], nom_complementaire)
        voie_nom, voie_normalise = voie_names(fields[spec['nom_voie']])
        code_insee = fields[spec['code_insee']]
    except (ValueError, IndexError, OverflowError):
        logger.debug(f"Error reading line {fields} ({lieu})")
        return None
    if commune_nom is None or voie_nom is None or not 0 <= numero <= MAX_NUMERO:
        logger.debug(f"Unusable line {fields} ({lieu})")
        return None

    return (code_postal, commune_normalise, commune_nom, code_insee,
            voie_normalise, voie_nom, numero, repetition, lon, lat)


def read_files(csv_file_paths):
    """
    Read the BAN files of one département

    The "adresses" and the "lieux-dits" files of a département must be merged before being indexed: otherwise a
    postal code appears twice in the database and a search restricted to that postal code only looks into one of the
    two sets of streets.

    :param csv_file_paths: path(s) to the CSV file(s)
    :return: addresses as nested dicts, :code:`{(code_postal,): {(commune_normalise, commune_nom, code_insee):
        {(voie_normalise, voie_nom): {(numero, repetition, lon, lat), ...}}}}`
    :rtype: dict
    """
    if isinstance(csv_file_paths, (str, os.PathLike)):
        csv_file_paths = [csv_file_paths]
    postal_dict = {}

    for csv_file_path in sorted(csv_file_paths):
        lieu = "lieux-dits" if "lieux-dits" in os.path.basename(csv_file_path) else "adresses"
        with open(csv_file_path, encoding='UTF-8') as f:
            next(f, None)  # header (some lieux-dits files are empty)
            for line in f:
                attributes = get_attributes(line.strip().split(';'), lieu)
                if attributes is None:
                    continue
                commune_dict = postal_dict.setdefault(attributes[:1], {})
                voie_dict = commune_dict.setdefault(attributes[1:4], {})
                voie_dict.setdefault(attributes[4:6], set()).add(attributes[6:])
    return postal_dict


def _mean(values):
    return int(sum(values) / len(values))


def build_tables(postal_dict):
    """
    Turn the nested dicts of :func:`read_files` into the tables of the database, each one sorted

    The cross references are local: they index the tables built here.

    :rtype: dict
    """
    postal_rows, commune_rows, voie_rows, localisation_rows = [], [], [], []
    for postal_key in sorted(postal_dict):
        postal_id, commune_start = len(postal_rows), len(commune_rows)
        commune_dict = postal_dict[postal_key]
        for commune_key in sorted(commune_dict):
            commune_id, voie_start = len(commune_rows), len(voie_rows)
            voie_dict = commune_dict[commune_key]
            voie_positions = []
            for voie_key in sorted(voie_dict):
                voie_id, localisation_start = len(voie_rows), len(localisation_rows)
                localisations = sorted(voie_dict[voie_key])
                localisation_rows.extend(loc + (voie_id,) for loc in localisations)
                lon = _mean([loc[2] for loc in localisations])
                lat = _mean([loc[3] for loc in localisations])
                voie_rows.append(voie_key + (lon, lat, localisation_start, len(localisation_rows), commune_id))
                voie_positions.append((lon, lat))
            lon = _mean([position[0] for position in voie_positions])
            lat = _mean([position[1] for position in voie_positions])
            commune_rows.append(commune_key + (lon, lat, voie_start, len(voie_rows), postal_id))
        postal_rows.append(postal_key + (commune_start, len(commune_rows), 0))  # ref_id: set when merging

    return {
        'postal': np.array(postal_rows, dtype=dtypes['postal']),
        'commune': np.array(commune_rows, dtype=dtypes['commune']),
        'voie': np.array(voie_rows, dtype=dtypes['voie']),
        'localisation': np.array(localisation_rows, dtype=dtypes['localisation']),
    }


def process_departement(dpt_nom, csv_file_paths):
    """
    Process all the files of a département

    :param str dpt_nom: departement
    :param csv_file_paths: path(s) to the CSV file(s) of the département
    :return: the tables of the département
    :rtype: dict
    """
    tables = build_tables(read_files(csv_file_paths))
    tables['departement'] = np.array([(dpt_nom, 0, len(tables['postal']))], dtype=dtypes['departement'])
    return tables
