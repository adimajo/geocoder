"""
create the spatial index for reverse search

.. autosummary::
    create_spatial_index
"""
import numpy as np
from loguru import logger

from geocoder.geocoding import spatial
from geocoder.geocoding.datapaths import paths
from geocoder.geocoding.datatypes import dtypes
from geocoder.geocoding.index import create_dat_file


def create_spatial_index():
    """
    Creates and stores a grid index as dat files on disk for reverse search of addresses given geolocation

    :rtype: bool
    """
    table = np.memmap(paths['localisation'], dtype=dtypes['localisation'], mode='r')
    logger.info('Building the spatial index...')
    cells, offsets, order = spatial.build_grid(table['longitude'], table['latitude'])
    for name, values in (('grid_cells', cells), ('grid_offsets', offsets), ('grid_order', order)):
        create_dat_file(values, paths[name], dtypes[name])
    logger.info('Done')
    return True


create_kdtree = create_spatial_index  # historical name
