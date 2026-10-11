"""
original geocoding module

.. autosummary::
    :toctree:

    __main__
    activate_reverse
    ban_processing
    datapaths
    datatypes
    download
    index
    normalize
    query
    result
    search
    similarity
    spatial
    utils
"""
import os

from geocoder.geocoding.utils import env_bool

DEBUG = env_bool("DEBUG", False)  # restricts the database to département 01 (development / tests)
LOCAL_DB = env_bool("LOCAL_DB", True)

if DEBUG and not os.environ.get("LOGURU_LEVEL"):
    os.environ["LOGURU_LEVEL"] = "DEBUG"
elif not os.environ.get("LOGURU_LEVEL"):  # pragma: no cover
    os.environ["LOGURU_LEVEL"] = "ERROR"

if not LOCAL_DB:
    import boto3

    # TLS certificates are verified; point S3_CA_BUNDLE to a CA file for private endpoints
    s3 = boto3.client('s3',
                      endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
                      use_ssl=True,
                      verify=os.environ.get("S3_CA_BUNDLE") or True)
else:
    s3 = None
