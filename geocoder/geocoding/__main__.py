#!/usr/bin/env python3
"""
defines entrypoints
"""
import multiprocessing
import os
import sys
from argparse import ArgumentParser

from geocoder.geocoding import LOCAL_DB
from geocoder.geocoding.activate_reverse import create_kdtree
from geocoder.geocoding.datapaths import paths
from geocoder.geocoding.download import check_ban_version, decompress, remove_downloaded_raw_ban_files
from geocoder.geocoding.index import create_database, process_files
from geocoder.wsgi import runserver


def update():
    if check_ban_version() or (LOCAL_DB and not all([os.path.exists(path) for path in paths])):
        decompress()
        process_files()
        create_database()
        create_kdtree()
    try:
        remove_downloaded_raw_ban_files()
    except Exception:  # nosec
        pass
    return True


commands = {
    'download': [check_ban_version],
    'decompress': [decompress],
    'index': [process_files, create_database],
    'reverse': [create_kdtree],
    'update': [update],
    'clean': [remove_downloaded_raw_ban_files],
    'runserver': [runserver]
}

parser = ArgumentParser(description='Runserver parser')
parser.add_argument('--host', type=str, default=os.environ.get("GEOCODER_HOST", '127.0.0.1'),
                    help='IP to bind (use 0.0.0.0 to listen on all interfaces)')
parser.add_argument('--port', type=str, default=os.environ.get("GEOCODER_PORT", '8000'),
                    help='port to bind')
parser.add_argument('--workers', type=int,
                    default=int(os.environ.get("GEOCODER_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 9))),
                    help='number of gunicorn workers')
parser.add_argument('--timeout', type=int, default=int(os.environ.get("GEOCODER_TIMEOUT", 120)),
                    help='gunicorn worker timeout in seconds')


def main():
    command = sys.argv[1:]

    if not command or command[0] not in commands:
        print('usage: geocoder '
              '{update, download, decompress, index, clean, reverse, runserver}')
        return

    if command[0] == "runserver":
        args, unknown = parser.parse_known_args()
        runserver(vars(args))
    else:
        for function in commands[command[0]]:
            success = function()
            if not success:
                return


if __name__ == "__main__":
    main()
