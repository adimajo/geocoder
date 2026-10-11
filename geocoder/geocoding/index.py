"""Processing of raw data.

This module creates an intermediary database in csv format. The goal of this
intermediate step is to easy the next step: the construction of the binary
files using tools from the package numpy.

"""

import os
import shutil
from collections import defaultdict, deque

import numpy as np
from loguru import logger
from tqdm import tqdm

from geocoder.geocoding import LOCAL_DB, ban_processing, s3
from geocoder.geocoding.datapaths import database, paths
from geocoder.geocoding.datatypes import dtypes
from geocoder.geocoding.download import raw_data_folder_path

file_names = ['departement', 'postal', 'commune', 'voie', 'localisation']
processed_files = defaultdict(deque)


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
    for (dirname, dirs, files) in os.walk(raw_data_folder_path):
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

    departements = list(ban_files.keys())
    departements.sort()

    for departement in tqdm(departements, desc="Process files"):
        logger.debug(f"Département : {departement}")
        ban_processing.update(departement, ban_files[departement], processed_files)

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
        create_dat_file(list(processed_file), paths[table], dtypes[table])

    return True


def add_index_tables():
    index_tables = ['postal', 'commune', 'voie']

    # Index tables creation
    for current_table in tqdm(index_tables, desc="Index tables"):
        sort_method = (lambda j, table=current_table: processed_files[table][j])

        # Sort table and add it to the module level dict processed_files
        processed_files[current_table + '_index'] = \
            sorted(range(len(processed_files[current_table])), key=sort_method)


def create_dat_file(lst, out_filename, dtype):
    """Write a list in a binary file as a numpy array.

    Args:
        lst: The list that will be written in the file.
        out_filename: The name of the binary file. It must be in the same
            directory.
        dtype: The type of the numpy array.
    """
    dat_file = np.memmap(out_filename, mode='w+', dtype=dtype, shape=(len(lst), ))
    try:
        dat_file[:] = lst[:]
    except TypeError:
        logger.debug(lst[-10:])
    dat_file.flush()
    if not LOCAL_DB:
        s3.upload_file(out_filename, "geocoder", f"database/{os.path.basename(out_filename)}")
