#!/bin/sh
# Brings the database up to date (download + indexing, skipped when the BAN did not change), then serves the API.
# Extra arguments are passed to `geocoder runserver` (--workers, --timeout, ...).
set -eu

if [ "${GEOCODER_SKIP_UPDATE:-false}" != "true" ]; then
    geocoder update
fi
exec geocoder runserver "$@"
