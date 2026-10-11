"""
Test configuration.

The unit tests run against a tiny database built from the BAN-formatted CSV files in ``tests/data/raw``: no
download is needed. The data folder is a temporary directory (``GEOCODER_DATA_DIR``) set before ``geocoder`` is
imported so that nothing is written inside the repository.
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

DATA_DIR = tempfile.mkdtemp(prefix="geocoder-tests-")
os.environ["GEOCODER_DATA_DIR"] = DATA_DIR
os.environ.setdefault("LOGURU_LEVEL", "ERROR")
os.environ.pop("DEBUG", None)
atexit.register(shutil.rmtree, DATA_DIR, ignore_errors=True)

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def fixture_database():
    from geocoder.geocoding import index, query
    from geocoder.geocoding.activate_reverse import create_kdtree
    from geocoder.geocoding.download import raw_data_folder_path

    shutil.copytree(Path(__file__).parent / "data" / "raw", raw_data_folder_path)
    assert index.process_files()
    assert index.create_database()
    assert create_kdtree()
    query.reset()
    yield
    query.reset()


@pytest.fixture
def client():
    from geocoder.api.provider import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
