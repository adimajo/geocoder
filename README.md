[![CI](https://github.com/adimajo/geocoder/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/adimajo/geocoder/actions/workflows/ci.yml)
[![Documentation](https://github.com/adimajo/geocoder/actions/workflows/docs.yml/badge.svg?branch=master)](https://adimajo.github.io/geocoder/)

Geocoder
========

Geocoder is an address search engine for France.
Unlike other APIs, it uses a database provided by the French government
(Base Adresse Nationale - BAN) as the main source of information and does
not impose any limit to the number of queries. The purpose of the project
is to supply the needs of French data scientists that rely on geocoded data.

Fork from [chrlryo/Geocoding](https://github.com/chrlryo/Geocoding) itself
a fork from [DeVilhena-Paulo/Geocoding](https://github.com/DeVilhena-Paulo/Geocoding).

Full documentation: https://adimajo.github.io/geocoder/

Getting started
===============

With Docker (REST API)
----------------------

```shell
docker run -d -p 8000:8000 -v geocoder-data:/data ghcr.io/adimajo/geocoder
```

On the first start the container downloads the BAN and builds the database in the `/data` volume (about 2 GB on
disk once built, 7 GB while building, estimated from a build of four large départements; keep the volume so that
later starts only check whether the BAN changed). Add `-e GEOCODER_DEPARTEMENTS=75,92`
to only serve some départements. The API listens on port 8000 once the database is ready:

* In your browser: http://localhost:8000 (demo page), http://localhost:8000/doc (Swagger),
  http://localhost:8000/geocode/12,%20Bd%20des%20Mar%C3%A9chaux/91120/Palaiseau
* With curl:

```shell
curl --header "Content-Type: application/json" \
--request POST \
--data '[{"address": "12, Bd des Maréchaux", "postal_code": "91120", "city": "Palaiseau"}]' \
http://localhost:8000/geocode_file
```

The API has no authentication nor rate limiting: do not expose it to untrusted clients without a reverse proxy.

As a Python package
-------------------

> The name `geocoder` on PyPI belongs to an unrelated project: install this one from GitHub.

```shell
pip install "geocoder[api] @ git+https://github.com/adimajo/geocoder.git"   # [api]: REST server, [s3]: S3 storage
```

Before the first use, download the BAN and build the database (`GEOCODER_DATA_DIR` chooses where it is stored,
`GEOCODER_DEPARTEMENTS` which départements are used; all of France by default):

```shell
geocoder update
```

or step by step: `geocoder download`, `decompress`, `index`, `reverse`. Serve the REST API with
`geocoder runserver --host 127.0.0.1 --port 8000`.

Usage
=====

The search engine
-----------------

```python
import geocoder

# -*- Complete search -*-
output = geocoder.find('91120', 'Palaiseau', '12, Bd des Maréchaux')
print(output['longitude'], output['latitude'])  # 2.2099342 48.7099138
print(output['quality'])  # 1 -> It means that the search was successful

# -*- Incomplete search -*-
geocoder.find('91120', None, '12, Bd des Maréchaux')['quality']  # 1
geocoder.find(None, 'Palaiseau', '12, Bd des Maréchaux')['quality']  # 1
geocoder.find('91120', None, 'Bd des Maréchaux')['quality']  # 3 -> The number was not found
geocoder.find('91120', 'Palaiseau', None)['quality']  # 4 -> The street was not found
geocoder.find('91120')['quality']  # 5 -> The city was not found (the position is the one of the postal code)

# -*- Search with typos -*-
geocoder.find('91120', 'Palaiseau', '12, Bd des Maréchx')['quality']  # 1
geocoder.find('91120', 'Palaiau', '12, Bd des Maréchx')['quality']  # 1
geocoder.find('91189', 'Palaiseau', '12, Bd des Maréchx')['quality']  # 1

# -*- Flexible syntax -*-
geocoder.find(commune='Palaiseau')['quality']
args = {'code_postal': '91120', 'commune': 'Palaiseau', 'adresse': '12, Bd Marechaux'}
geocoder.find(**args)
```

The reverse functionality
-------------------------

```python
import geocoder

# longitude and latitude
output = geocoder.near((2.2099, 48.7099))
output['commune']['nom']  # PALAISEAU
output['voie']['nom']  # BOULEVARD DES MARECHAUX
```

Development
===========

```shell
uv sync --all-extras                 # environment (Python >= 3.10)
uv run pytest                        # unit tests, on a tiny fixture database: no download
uv run pytest -m integration         # builds the database of the département 01 from the real BAN (~20 s)
uv run ruff check geocoder tests benchmarks
uv run sphinx-build -W -b html docs/source docs/build/html   # needs: uv sync --extra api --group docs
```

[`benchmarks/`](benchmarks) measures speed and accuracy against the true coordinates of random BAN addresses.
On the département 01, compared with the version before the modernisation (2.1.23):

| | before | now |
|---|---|---|
| Queries answered within 100 m of the true address (400 mixed queries) | 63 % | 87 % |
| Building the database (index) | 17 s | 3.4 s (on one core, parallel over départements) |
| Building the reverse search index | 6.8 s (kd-tree, ~30 min for France) | 1.3 s |
| Reverse query | 2.6 ms, wrong address for 12 % of the queries | 0.55 ms, always the nearest |
| Fuzzy street search, worst case | 4.7 ms | 1.3 ms |

Releases: push a `vX.Y.Z` tag matching `geocoder/__version__`; GitHub Actions scans and publishes the image to
`ghcr.io/adimajo/geocoder` and creates the GitHub release.
