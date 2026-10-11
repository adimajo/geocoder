"""Update the raw data used as the main source of information.

The BAN (Base Adresse Nationale) files are downloaded for every département, in parallel, and either kept locally
(default) or mirrored on S3 (:code:`LOCAL_DB=false`).

Environment variables:

* :code:`SSL_VERIFICATION` (default :code:`true`): set to :code:`false` to disable TLS verification (not recommended);
  a custom CA bundle can be given with the standard :code:`REQUESTS_CA_BUNDLE`
* :code:`GEOCODER_DEPARTEMENTS`: comma separated list of the départements to use (e.g. :code:`75,92,2A`), all of
  France by default (:code:`01` only when :code:`DEBUG=true`)
* :code:`GEOCODER_DOWNLOAD_WORKERS` (default 4): number of parallel downloads
"""
import gzip
import hashlib
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry

from geocoder.geocoding import DEBUG, LOCAL_DB, s3
from geocoder.geocoding.datapaths import data_dir, database
from geocoder.geocoding.utils import env_bool

SSL_VERIFICATION = env_bool("SSL_VERIFICATION", True)
TIMEOUT = (10, 120)  # connect, read (seconds)
DOWNLOAD_WORKERS = int(os.environ.get("GEOCODER_DOWNLOAD_WORKERS", 4))

if not SSL_VERIFICATION:  # pragma: no cover
    logger.warning("TLS verification is disabled (SSL_VERIFICATION=false)")
    disable_warnings(InsecureRequestWarning)

raw_data_folder_path = os.path.join(data_dir, 'raw')
ban_url = 'https://adresse.data.gouv.fr/data/ban/adresses-odbl/latest/csv/{}'
ban_dpt_gz_file_name = ['adresses-{}.csv.gz', 'lieux-dits-{}-beta.csv.gz']
ban_dpt_file_name = [filegz[:-3] for filegz in ban_dpt_gz_file_name]

content_folder_path = 'content'
server_content_file_name = 'server_content_v2.txt'
local_content_file_name = 'local_content_v2.txt'

if LOCAL_DB:
    content_folder_path = os.path.join(data_dir, content_folder_path)
    server_content_file_name = os.path.join(content_folder_path, server_content_file_name)
    local_content_file_name = os.path.join(content_folder_path, local_content_file_name)

if os.environ.get("GEOCODER_DEPARTEMENTS"):
    dpt_list = [dpt.strip().upper() for dpt in os.environ["GEOCODER_DEPARTEMENTS"].split(",") if dpt.strip()]
elif DEBUG:
    dpt_list = ["01"]
else:  # pragma: no cover
    dpt_list = ["01", "02", "03", "04", "05", "06", "07", "08", "09",
                "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
                "2A", "2B", "21", "22", "23", "24", "25", "26", "27", "28", "29",
                "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
                "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
                "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
                "60", "61", "62", "63", "64", "65", "66", "67", "68", "69",
                "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
                "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
                "90", "91", "92", "93", "94", "95",
                "971", "972", "973", "974", "975", "976", "977", "978", "984", "986", "987", "988", "989"]


def _session():
    """requests session with connection pooling and retries on transient errors"""
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=max(DOWNLOAD_WORKERS, 1))
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.verify = SSL_VERIFICATION or False  # an explicit CA bundle can be given with REQUESTS_CA_BUNDLE
    return session


def _md5(fname):
    """
    Calculates md5 hash of file (only used to detect whether the BAN listing changed, not for security)

    Args:
        fname: file path
    """
    md5_hash = hashlib.md5(usedforsecurity=False)
    if LOCAL_DB:
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                md5_hash.update(chunk)
    else:
        f = s3.get_object(Bucket="geocoder", Key=f"content/{fname}")['Body']
        for chunk in iter(lambda: f.read(65536), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def update_ban_file(url, file_name):
    """
    Download a (small) file and store it locally or on S3

    Args:
        url (str): URL of BAN database
        file_name (os.Path): name of the file to write
    """
    try:
        r = _session().get(url, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:  # pragma: no cover
        raise ConnectionError(f'Unable to join BAN address website ({url}): {e}') from e
    if r.status_code != 200:  # pragma: no cover
        raise ConnectionError(f'Unable to join BAN address website ({url}). Status error code: {r.status_code}')

    if LOCAL_DB:
        with open(file_name, 'wb') as file:
            file.write(r.content)
    else:
        s3.put_object(Body=r.content, Bucket="geocoder", Key=f"content/{file_name}")


def update_local_content_file():
    logger.debug("Update local content file")
    update_ban_file(ban_url.format(""), local_content_file_name)


def update_server_content_file():
    logger.debug("Update server content file")
    update_ban_file(ban_url.format(""), server_content_file_name)


def need_to_download():
    """
    Defines whether new data needs to be downloaded

    :rtype: bool
    """
    if LOCAL_DB and not os.path.exists(local_content_file_name):
        return True
    elif not LOCAL_DB:
        try:
            s3.head_object(Bucket='geocoder', Key=f"content/{local_content_file_name}")
        except s3.exceptions.ClientError:
            return True
    logger.debug("Local content file exists")
    update_server_content_file()
    logger.debug("Comparing local and server content files")
    if _md5(server_content_file_name) == _md5(local_content_file_name) and (
            (LOCAL_DB and os.path.exists(database)) or (not LOCAL_DB)):
        logger.info('BAN database is already up to date. No need to download it again.')
        if LOCAL_DB:
            os.remove(server_content_file_name)
        else:
            s3.delete_object(Bucket="geocoder", Key=f"content/{server_content_file_name}")
        return False
    else:
        return True


def _download_ban_dpt_file(ban_dpt_file_name, session=None):
    """
    Downloads a single file from BAN (to a temporary name first, so that a partial file is never mistaken for a
    complete one)

    Args:
        ban_dpt_file_name (str): name of file to download

    :rtype: bool
    """
    session = session or _session()
    path = os.path.join(raw_data_folder_path, ban_dpt_file_name)
    tmp_path = path + ".part"
    try:
        with session.get(ban_url.format(ban_dpt_file_name), stream=True, timeout=TIMEOUT) as response:
            if not response.ok:  # pragma: no cover
                logger.error(f'Download {ban_dpt_file_name} unsuccessful: HTTP {response.status_code}')
                return False
            expected = response.headers.get('content-length')
            done = 0
            with open(tmp_path, 'wb') as ban_dpt_file:
                for block in response.iter_content(65536):
                    ban_dpt_file.write(block)
                    done += len(block)
        if expected is not None and done != int(expected):  # pragma: no cover
            logger.error(f'Download {ban_dpt_file_name} unsuccessful: incomplete')
            return False
        os.replace(tmp_path, path)
    except requests.exceptions.RequestException as e:  # pragma: no cover
        logger.error(f'Download {ban_dpt_file_name} unsuccessful: {e}')
        return False
    finally:
        if os.path.exists(tmp_path):  # pragma: no cover
            os.remove(tmp_path)

    if not LOCAL_DB:
        with open(path, 'rb') as ban_dpt_file:
            s3.upload_fileobj(Fileobj=ban_dpt_file,
                              Bucket='geocoder',
                              Key=f"raw/{ban_dpt_file_name}")
    return True


def _s3_keys(prefix):
    """All the keys under a prefix (the listing is paginated)"""
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket='geocoder', Prefix=prefix):
        for obj in page.get('Contents', []):
            yield obj['Key']


def _update_ban_files():
    """
    Downloads everything

    The local content file (which records which BAN version we have) is only written once every file has been
    downloaded: an interrupted or partial download is retried on the next run.
    """
    logger.info('A new version of BAN base is available.')

    if LOCAL_DB:
        if os.path.exists(raw_data_folder_path):
            shutil.rmtree(raw_data_folder_path)
        os.makedirs(raw_data_folder_path)
    else:
        for key in _s3_keys("raw/"):
            s3.delete_object(Bucket="geocoder", Key=key)
        os.makedirs(raw_data_folder_path, exist_ok=True)

    file_names = [name.format(dpt) for dpt in dpt_list for name in ban_dpt_gz_file_name]
    session = _session()
    with ThreadPoolExecutor(max_workers=max(DOWNLOAD_WORKERS, 1)) as pool:
        results = list(tqdm(pool.map(lambda name: _download_ban_dpt_file(name, session), file_names),
                            total=len(file_names), desc="Download raw data"))

    failed = [name for name, ok in zip(file_names, results) if not ok]
    if failed:
        raise RuntimeError("Could not download: " + ", ".join(failed))

    update_local_content_file()
    return True


def check_ban_version():
    """
    Checks BAN version and triggers download if necessary

    Returns: whether a download has been performed
    :rtype: bool
    """
    if LOCAL_DB:
        os.makedirs(content_folder_path, exist_ok=True)

    if not need_to_download():
        return False
    return _update_ban_files()


def _eventually_download_files_locally():
    """
    If raw files were downloaded to S3, download locally before decompression
    """
    if not LOCAL_DB and not os.path.exists(raw_data_folder_path):
        # retrieve from S3
        os.makedirs(raw_data_folder_path)
        for key in _s3_keys("raw/"):
            filename = key.replace('raw/', "")
            if not filename.endswith(".gz"):
                continue
            s3.download_file('geocoder', key, os.path.join(raw_data_folder_path, filename))


def _decompress_one(gz_file_name):
    """Decompress one archive, remove it, return whether it worked"""
    dpt_gz_file_path = os.path.join(raw_data_folder_path, gz_file_name)
    if not os.path.isfile(dpt_gz_file_path):  # pragma: no cover
        logger.error(f'Decompression unsuccessful: nonexistent file {dpt_gz_file_path}')
        return False
    logger.info(f'Extracting file {gz_file_name[:-3]}')
    with gzip.open(dpt_gz_file_path, 'rb') as f_in, open(dpt_gz_file_path[:-3], 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out, 1024 * 1024)
    _remove_file(dpt_gz_file_path)
    return True


def decompress():
    """
    Decompress every downloaded archive

    Returns: whether decompression was successful
    :rtype: bool
    """
    _eventually_download_files_locally()

    file_names = [name.format(dpt) for dpt in dpt_list for name in ban_dpt_gz_file_name]
    with ThreadPoolExecutor(max_workers=max(os.cpu_count() or 1, 1)) as pool:  # zlib releases the GIL
        results = list(pool.map(_decompress_one, file_names))
    return all(results)


def _remove_file(file_path):
    """
    Delete file

    Args:
        file_path (os.Path): path to file to be deleted
    """
    logger.info(f'Deleting file {file_path}')
    try:
        os.remove(file_path)
    except OSError:  # pragma: no cover
        pass


def remove_downloaded_raw_ban_files():
    """
    Removes all raw files (compressed and uncompressed)

    Returns: whether removing was successful
    :rtype: bool
    """
    shutil.rmtree(raw_data_folder_path, ignore_errors=True)
    return True
