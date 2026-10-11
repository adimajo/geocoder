"""Path to the database files.

Attributes:
    here (str): Path to the package.
    data_dir (str): Path to the folder holding the data (GEOCODER_DATA_DIR, defaults to the package folder).
    database (str): Path to the database folder.
    tables (:obj:`list` of :obj:`str`): The name of each table in the database.
    paths (:obj:`list` of :obj:`str`): The path to each table of the database.
"""

import os

here = os.path.abspath(os.path.dirname(__file__))

# Where the downloaded BAN files and the built database live. Defaults to the package folder (historical behaviour);
# set GEOCODER_DATA_DIR to keep the (large, mutable) data outside of the installed code, e.g. on a volume.
data_dir = os.path.abspath(os.environ.get("GEOCODER_DATA_DIR") or here)

database = os.path.join(data_dir, 'database')

tables = ['departement', 'postal', 'commune', 'voie', 'localisation',
          'commune_index', 'postal_index', 'voie_index', 'grid_cells', 'grid_offsets', 'grid_order']

paths = {table: os.path.join(database, table + '.dat') for table in tables}
