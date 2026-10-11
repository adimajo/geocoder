"""Nearest neighbour search on the sphere with a sorted grid index.

All the addresses are assigned to a square cell of :data:`CELL` degrees. Sorting the addresses by cell gives three
flat arrays that are cheap to build (one :code:`argsort`), can be memory-mapped and shared between processes:

* :code:`cells`: the sorted keys of the non-empty cells,
* :code:`offsets`: where the addresses of each cell start in :code:`order` (length :code:`len(cells) + 1`),
* :code:`order`: the address indices, sorted by cell.

A search visits the cells around the query ring after ring and stops as soon as the best address found cannot be
beaten by anything outside the visited square, so the result is exact.

Coordinates are integers, in units of :math:`10^{-7}` degrees (see :mod:`geocoder.geocoding.utils`).
"""
import math

import numpy as np

SCALE = 10 ** 7
CELL = 100_000  # cell size, in 1e-7 degree: 0.01 degree, about 1.1 km
N_LAT_CELLS = 180 * SCALE // CELL
EARTH_RADIUS = 6_371_008.8  # meters
MAX_RINGS = 100  # beyond (about 100 km) the search falls back to a brute force scan
CHUNK = 5_000_000


def cell_x(lon):
    return (np.asarray(lon, dtype=np.int64) + 180 * SCALE) // CELL


def cell_y(lat):
    return (np.asarray(lat, dtype=np.int64) + 90 * SCALE) // CELL


def cell_key(x, y):
    return x * N_LAT_CELLS + y


def build_grid(lon, lat):
    """Build the grid index of points given by their integer longitudes and latitudes.

    :return: :code:`(cells, offsets, order)`, all :code:`int32`
    """
    keys = cell_key(cell_x(lon), cell_y(lat))
    order = np.argsort(keys, kind="stable")
    cells, first = np.unique(keys[order], return_index=True)
    offsets = np.append(first, len(keys))
    return cells.astype(np.int32), offsets.astype(np.int32), order.astype(np.int32)


def haversine(lon1, lat1, lon2, lat2):
    """Great-circle distance in meters. Arguments are in degrees (numpy broadcasting applies)."""
    lon1, lat1, lon2, lat2 = (np.radians(np.asarray(v, dtype=np.float64)) for v in (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _ring(x, y, k):
    """Keys of the cells at Chebyshev distance k of cell (x, y) that exist on the grid."""
    if k == 0:
        xs, ys = np.array([x]), np.array([y])
    else:
        side = np.arange(-k, k + 1)
        inner = np.arange(-k + 1, k)
        xs = np.concatenate([x + side, x + side, np.full(len(inner), x - k), np.full(len(inner), x + k)])
        ys = np.concatenate([np.full(len(side), y - k), np.full(len(side), y + k), y + inner, y + inner])
    ok = (xs >= 0) & (xs < 360 * SCALE // CELL) & (ys >= 0) & (ys < N_LAT_CELLS)
    return cell_key(xs[ok], ys[ok])


def _brute_force(lon, lat, query_lon, query_lat):
    best, best_distance = None, math.inf
    for start in range(0, len(lon), CHUNK):
        d = haversine(lon[start:start + CHUNK] / SCALE, lat[start:start + CHUNK] / SCALE, query_lon, query_lat)
        i = int(np.argmin(d))
        if d[i] < best_distance:
            best, best_distance = start + i, float(d[i])
    return best, best_distance


def nearest(lon, lat, cells, offsets, order, query_lon, query_lat):
    """Index of the point nearest to a position, with its distance in meters.

    :param lon: integer longitudes of the points (any array-like supporting fancy indexing, e.g. a memmap column)
    :param lat: integer latitudes of the points
    :param cells: the grid, see :func:`build_grid`
    :param offsets: the grid, see :func:`build_grid`
    :param order: the grid, see :func:`build_grid`
    :param query_lon: longitude of the position, in degrees
    :param query_lat: latitude of the position, in degrees
    :rtype: tuple
    """
    x = int(cell_x(round(query_lon * SCALE)))
    y = int(cell_y(round(query_lat * SCALE)))
    # a cell is at least this wide / high (meters), whatever the latitude within the searched area
    cell_height = CELL / SCALE * math.pi / 180 * EARTH_RADIUS

    best, best_distance = None, math.inf
    for k in range(MAX_RINGS + 1):
        keys = _ring(x, y, k)
        pos = _present(cells, keys)
        if len(pos):
            candidates = np.concatenate([order[offsets[p]:offsets[p + 1]] for p in pos])
            d = haversine(lon[candidates] / SCALE, lat[candidates] / SCALE, query_lon, query_lat)
            i = int(np.argmin(d))
            if d[i] < best_distance:
                best, best_distance = int(candidates[i]), float(d[i])
        cell_width = cell_height * math.cos(math.radians(min(abs(query_lat) + (k + 1) * CELL / SCALE, 89.9)))
        if best is not None and best_distance <= k * min(cell_width, cell_height):
            return best, best_distance
    return _brute_force(lon, lat, query_lon, query_lat)


def _present(cells, keys):
    """Positions in :code:`cells` of the keys that are in it"""
    pos = np.searchsorted(cells, keys)
    found = pos < len(cells)
    found[found] = cells[pos[found]] == keys[found]
    return pos[found]
