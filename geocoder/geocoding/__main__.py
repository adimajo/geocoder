#!/usr/bin/env python3
"""
defines entrypoints
"""
import sys

from geocoding.activate_reverse import create_kdtree
from geocoding.download import get_ban_file, decompress, remove_downloaded_raw_ban_files
from geocoding.index import process_files, create_database

commands = {
    'download': [get_ban_file],
    'decompress': [decompress],
    'index': [process_files, create_database],
    'reverse': [create_kdtree],
    'update': [get_ban_file, decompress, process_files,
               create_database, create_kdtree, remove_downloaded_raw_ban_files],
    'clean': [remove_downloaded_raw_ban_files],
}


def main(args=None):
    command = sys.argv[1:]

    if not command or command[0] not in commands:
        print('usage: geocoding '
              '{update, download, decompress, index, remove_non_necessary_files, reverse}')
        return

    for function in commands[command[0]]:
        success = function()
        if not success:
            return


if __name__ == "__main__":
    main()
