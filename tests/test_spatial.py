import numpy as np
import pytest

from geocoder.geocoding import spatial

SCALE = spatial.SCALE


def to_int(values):
    return np.round(np.asarray(values) * SCALE).astype(np.int32)


def brute_force(lon, lat, qlon, qlat):
    d = spatial.haversine(lon / SCALE, lat / SCALE, qlon, qlat)
    return int(np.argmin(d)), float(d.min())


@pytest.fixture(scope="module")
def points():
    rng = np.random.default_rng(0)
    # a dense city, a sparse countryside, an island far away, and points on cell borders
    lon = np.concatenate([rng.normal(2.35, 0.05, 3000), rng.uniform(-1, 6, 500), rng.normal(55.5, 0.1, 100),
                          [2.0, 2.01, 2.02, 179.99, -179.99]])
    lat = np.concatenate([rng.normal(48.85, 0.03, 3000), rng.uniform(43, 50, 500), rng.normal(-21.1, 0.1, 100),
                          [48.0, 48.01, 48.02, 0.0, 0.0]])
    return to_int(lon), to_int(lat)


@pytest.fixture(scope="module")
def grid(points):
    return spatial.build_grid(*points)


def test_grid_structure(points, grid):
    cells, offsets, order = grid
    assert len(offsets) == len(cells) + 1
    assert offsets[0] == 0 and offsets[-1] == len(points[0])
    assert sorted(order.tolist()) == list(range(len(points[0])))
    assert np.all(np.diff(cells) > 0)


@pytest.mark.parametrize("seed", range(5))
def test_matches_brute_force(points, grid, seed):
    rng = np.random.default_rng(seed)
    lon, lat = points
    queries = np.concatenate([
        np.column_stack([rng.normal(2.35, 0.1, 40), rng.normal(48.85, 0.06, 40)]),  # in the city
        np.column_stack([rng.uniform(-3, 8, 40), rng.uniform(41, 51, 40)]),  # anywhere in mainland France
        np.column_stack([rng.uniform(-180, 180, 10), rng.uniform(-80, 80, 10)]),  # far from any point
        [[2.005, 48.005], [0.0, 0.0], [179.995, 0.0], [-179.995, 0.0], [55.5, -21.1]],
    ])
    for qlon, qlat in queries:
        expected, expected_distance = brute_force(lon, lat, qlon, qlat)
        found, found_distance = spatial.nearest(lon, lat, *grid, qlon, qlat)
        assert found_distance == pytest.approx(expected_distance, rel=1e-9, abs=1e-6), (qlon, qlat)
        if found != expected:  # tie
            assert spatial.haversine(lon[found] / SCALE, lat[found] / SCALE, qlon, qlat) == pytest.approx(expected_distance)


def test_single_point():
    lon, lat = to_int([2.3]), to_int([48.8])
    grid = spatial.build_grid(lon, lat)
    assert spatial.nearest(lon, lat, *grid, 100.0, -50.0)[0] == 0


def test_haversine():
    # Paris - Marseille is about 660 km
    assert spatial.haversine(2.35, 48.85, 5.37, 43.30) == pytest.approx(660_000, rel=0.01)
    assert spatial.haversine(2.35, 48.85, 2.35, 48.85) == 0
