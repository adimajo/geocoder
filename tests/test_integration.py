"""
End to end test on the real BAN data of the département 01 (downloaded, ~10 s), in a separate process with its own
data folder: ``pytest -m integration``
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration


def test_pipeline_on_departement_01(tmp_path):
    import os

    env = {**os.environ, "DEBUG": "true", "GEOCODER_DATA_DIR": str(tmp_path), "LOGURU_LEVEL": "ERROR"}

    def run(*args):
        return subprocess.run(args, env=env, cwd=ROOT, check=True, capture_output=True, text=True, timeout=900)

    for step in ("download", "decompress", "index", "reverse"):
        run(sys.executable, "-m", "geocoder.geocoding", step)

    # a second `update` finds that the BAN did not change and has nothing to do
    run(sys.executable, "-m", "geocoder.geocoding", "update")

    # queries made from the BAN itself must find their address (and the reverse search its commune)
    output = run(sys.executable, "benchmarks/run.py", "--min-exact", "0.95").stdout
    assert "exact" in output
    reverse = run(sys.executable, "-c",
                  "import geocoder; print(geocoder.near((5.3527, 45.9815))['commune']['nom'])").stdout.strip()
    assert reverse == "AMBERIEU-EN-BUGEY"
