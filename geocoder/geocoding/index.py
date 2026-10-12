"""Processing of raw data.

The BAN files are read département by département (in parallel), turned into numpy tables, merged and stored as
binary files that are later memory-mapped by :mod:`geocoder.geocoding.query`.

"""

import os
import shutil
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from loguru import logger
from tqdm import tqdm

from geocoder.geocoding import LOCAL_DB, ban_processing, s3
from geocoder.geocoding.datapaths import database, paths
from geocoder.geocoding.datatypes import dtypes
from geocoder.geocoding.download import raw_data_folder_path

file_names = ['departement', 'postal', 'commune', 'voie', 'localisation']
INDEX_WORKERS = int(os.environ.get("GEOCODER_INDEX_WORKERS", os.cpu_count() or 1))

processed_files = {}


def _process(args):
    return ban_processing.process_departement(*args)


def merge(departements):
    """
    Put the tables of several départements one after the other, shifting their cross references

    :param list departements: tables of each département, as returned by
        :func:`geocoder.geocoding.ban_processing.process_departement`, in the order they should appear
    :rtype: dict
    """
    merged = {name: [] for name in file_names}
    before = {name: 0 for name in file_names}
    for dpt_index, tables in enumerate(departements):
        departement = tables['departement'].copy()
        postal, commune, voie, localisation = (tables[name].copy() for name in file_names[1:])
        departement['start'] += before['postal']
        departement['end'] += before['postal']
        postal['start'] += before['commune']
        postal['end'] += before['commune']
        postal['ref_id'] = dpt_index
        commune['start'] += before['voie']
        commune['end'] += before['voie']
        commune['ref_id'] += before['postal']
        voie['start'] += before['localisation']
        voie['end'] += before['localisation']
        voie['ref_id'] += before['commune']
        localisation['ref_id'] += before['voie']
        for name, table in zip(file_names, (departement, postal, commune, voie, localisation)):
            merged[name].append(table)
            before[name] += len(table)
    return {name: np.concatenate(tables) if tables else np.empty(0, dtype=dtypes[name])
            for name, tables in merged.items()}


def process_files():
    """
    Process all downloaded decompressed files

    :return: if processing was successful
    :rtype: bool
    """
    if not os.path.exists(raw_data_folder_path):  # pragma: no cover
        logger.info('Data not found - execute: geocoder download')
        return False

    ban_files = defaultdict(list)

    # Open each csv file
    for (dirname, _dirs, files) in os.walk(raw_data_folder_path):
        for filename in files:
            if filename.endswith('.csv'):
                file_path = os.path.join(dirname, filename)
                if "adresses" in filename:
                    dpt_name = filename.split('-')[-1].split('.')[0]
                else:
                    dpt_name = filename.split('-')[-2].split('.')[0]
                ban_files[dpt_name].append(file_path)

    logger.debug(f"Files: {ban_files}")

    # Check if the folder was not empty
    if not ban_files:  # pragma: no cover
        logger.info('No CSV file - execute: geocoder decompress')
        return False

    jobs = [(departement, ban_files[departement]) for departement in sorted(ban_files)]
    workers = min(INDEX_WORKERS, len(jobs))
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            departements = list(tqdm(pool.map(_process, jobs), total=len(jobs), desc="Process files"))
    else:
        departements = [_process(job) for job in tqdm(jobs, desc="Process files")]

    processed_files.clear()
    processed_files.update(merge(departements))
    return True


def create_database():
    if os.path.exists(database):
        try:
            shutil.rmtree(database)
        except PermissionError as e:  # pragma: no cover
            logger.error('Windows sucks, remove database folder manually and proceed.')
            raise e
    os.makedirs(database)

    if not processed_files:  # pragma: no cover
        return False

    add_index_tables()

    for table, processed_file in tqdm(processed_files.items(), desc="Store database"):
        logger.debug(table)
        create_dat_file(processed_file, paths[table], dtypes[table])

    return True


def sort_order(table):
    """Positions that sort a table on all its columns, in order (a stable lexicographic sort)"""
    return np.argsort(table, order=list(table.dtype.names), kind='stable').astype(np.int32)


def add_index_tables():
    """Index tables give access to the postal, commune and voie tables sorted without moving their rows"""
    for current_table in tqdm(['postal', 'commune', 'voie'], desc="Index tables"):
        processed_files[current_table + '_index'] = sort_order(processed_files[current_table])


def create_dat_file(lst, out_filename, dtype):
    """Write an array in a binary file, to be read back as a numpy memmap.

    Args:
        lst: The array (or list) that will be written in the file.
        out_filename: The name of the binary file. It must be in the same
            directory.
        dtype: The type of the numpy array.
    """
    dat_file = np.memmap(out_filename, mode='w+', dtype=dtype, shape=(len(lst), ))
    dat_file[:] = lst[:]
    dat_file.flush()
    del dat_file
    if not LOCAL_DB:
        s3.upload_file(out_filename, "geocoder", f"database/{os.path.basename(out_filename)}")
