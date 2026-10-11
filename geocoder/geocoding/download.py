"""Update the raw data used as the main source of information.

"""
import gzip
import hashlib
import os
import shutil

import requests
from botocore.errorfactory import ClientError
from loguru import logger
from tqdm import tqdm
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from geocoder.geocoding import DEBUG, LOCAL_DB, s3
from geocoder.geocoding.datapaths import data_dir, database

SSL_VERIFICATION = os.environ.get("SSL_VERIFICATION", False)

if not SSL_VERIFICATION:
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

if DEBUG:
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


def _md5(fname):
    """
    Calculates md5 hash of file

    Args:
        fname: file path
    """
    md5_hash = hashlib.md5()  # nosec
    if LOCAL_DB:
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
    else:
        f = s3.get_object(Bucket="geocoder", Key=f"content/{fname}")['Body']
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def update_ban_file(url, file_name):
    """
    Check which files are present

    Args:
        url (str): URL of BAN database
        file_name (os.Path): name of the file to write
    """
    try:
        msg = f'Unable to join BAN address website ({url}).'
        r = requests.get(url, verify=SSL_VERIFICATION)  # nosec
        msg += f' Status error code: {r.status_code}'
        if r.status_code != 200:  # pragma: no cover
            raise ConnectionError(msg)
    except (requests.exceptions.ConnectionError, requests.exceptions.SSLError, requests.exceptions.HTTPError):
        raise ConnectionError(msg)  # pragma: no cover

    if LOCAL_DB:
        with open(file_name, 'w') as file:
            file.write(r.text)
    else:
        s3.put_object(Body=r.text, Bucket="geocoder", Key=f"content/{file_name}")


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
        except ClientError:
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


def _download_ban_dpt_file(ban_dpt_file_name):
    """
    Downloads a single file from BAN

    Args:
        ban_dpt_file_name (str): name of file to download

    :rtype: bool
    """
    with open(os.path.join(raw_data_folder_path, ban_dpt_file_name), 'wb') as ban_dpt_file:
        response = requests.get(ban_url.format(ban_dpt_file_name), stream=True,  # nosec
                                verify=SSL_VERIFICATION)

        if not response.ok:  # pragma: no cover
            logger.info(f'Download {ban_dpt_file_name} unsuccessful: bad response')
            return False

        done, total_size = 0, int(response.headers.get('content-length'))
        for block in response.iter_content(4096):
            ban_dpt_file.write(block)
            done += len(block)

    if done != total_size:  # pragma: no cover
        logger.error(f'Download {ban_dpt_file_name} unsuccessful: incomplete')
        return False

    if not LOCAL_DB:
        with open(os.path.join(raw_data_folder_path, ban_dpt_file_name), 'rb') as ban_dpt_file:
            s3.upload_fileobj(Fileobj=ban_dpt_file,
                              Bucket='geocoder',
                              Key=f"raw/{ban_dpt_file_name}")
    return True


def _update_ban_files():
    """
    Downloads everything
    """
    logger.info('A new version of BAN base is available.')
    update_local_content_file()

    if LOCAL_DB and os.path.exists(raw_data_folder_path):
        shutil.rmtree(raw_data_folder_path)
    if LOCAL_DB:
        os.mkdir(raw_data_folder_path)
    else:
        bucket_list_result_set = s3.list_objects_v2(Bucket='geocoder',
                                                    Prefix="content/",
                                                    Delimiter='/')['Contents']
        for obj in bucket_list_result_set:
            if obj['Key'] == 'content/':
                continue
            s3.delete_object(Bucket="geocoder", Key=obj["Key"])

    for dpt in tqdm(dpt_list, desc="Download raw data"):
        for ban_dpt_gz_file_name_type in ban_dpt_gz_file_name:
            downloading_ban_dpt_gz_file_name = ban_dpt_gz_file_name_type.format(dpt)
            if not _download_ban_dpt_file(downloading_ban_dpt_gz_file_name):
                logger.error(f'Impossible to download {downloading_ban_dpt_gz_file_name}')

    return True


def check_ban_version():
    """
    Checks BAN version and triggers download if necessary

    Returns: whether a download has been performed
    :rtype: bool
    """
    if LOCAL_DB and not os.path.exists(content_folder_path):
        os.mkdir(content_folder_path)

    if not need_to_download():
        return False
    return _update_ban_files()


def _eventually_download_files_locally():
    """
    If raw files were downloaded to S3, download locally before decompression
    """
    if not LOCAL_DB and not os.path.exists(raw_data_folder_path):
        # retrieve from S3
        os.mkdir(raw_data_folder_path)
        bucket_list_result_set = s3.list_objects_v2(Bucket='geocoder',
                                                    Prefix="raw/",
                                                    Delimiter='/')['Contents']
        for obj in bucket_list_result_set:
            filename = obj['Key'].replace('raw/', "")
            if filename is None or filename == "" or not filename.endswith(".gz"):
                continue
            s3.download_file('geocoder', obj['Key'], os.path.join(raw_data_folder_path, filename))


def decompress():
    """
    Decompress every downloaded archive

    Returns: whether decompression was successful
    :rtype: bool
    """
    _eventually_download_files_locally()

    count = 0
    for dpt in dpt_list:
        # Certifies the existence of the subdirectory.
        for ban_dpt_gz_file_name_type in ban_dpt_gz_file_name:
            dpt_gz_file_path = os.path.join(raw_data_folder_path, ban_dpt_gz_file_name_type.format(dpt))
            if not os.path.isfile(dpt_gz_file_path):  # pragma: no cover
                logger.error(f'Decompression unsuccessful: nonexistent file {dpt_gz_file_path}')
                count += 1

            else:  # Decompress each file within gzip
                with gzip.open(dpt_gz_file_path, 'rb') as f_in:
                    dpt_file_path = os.path.join(raw_data_folder_path, ban_dpt_gz_file_name_type.format(dpt)[:-3])
                    logger.info(f'Extracting file {ban_dpt_gz_file_name_type.format(dpt)[:-3]}')
                    with open(dpt_file_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                _remove_file(dpt_gz_file_path)

    if count:  # pragma: no cover
        return False
    return True


def _remove_file(file_path):
    """
    Delete file

    Args:
        file_path (os.Path): path to file to be deleted
    """
    logger.info(f'Deleting file {file_path}')
    try:
        os.remove(file_path)
    except Exception:  # nosec
        pass


def remove_downloaded_raw_ban_files():
    """
    Removes all raw files (compressed and uncompressed)

    Returns: whether removing was successful
    :rtype: bool
    """
    for dpt in dpt_list:
        for ban_dpt_gz_file_name_type in ban_dpt_gz_file_name:
            _remove_file(os.path.join(raw_data_folder_path, ban_dpt_gz_file_name_type.format(dpt)))
        for ban_dpt_file_name_type in ban_dpt_file_name:
            _remove_file(os.path.join(raw_data_folder_path, ban_dpt_file_name_type.format(dpt)))
    shutil.rmtree(raw_data_folder_path)
    return True
