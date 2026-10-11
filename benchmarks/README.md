# Benchmarks

Regression / accuracy harness on département 01 (the one downloaded in `DEBUG` mode).

```shell
export DEBUG=true GEOCODER_DATA_DIR=/tmp/geocoder-dept01
geocoder download && geocoder decompress && geocoder index && geocoder reverse

python benchmarks/run.py                      # timings + accuracy against the true coordinates
python benchmarks/run.py --dump out.json      # also dump every result
python benchmarks/run.py --diff a.json b.json # compare two dumps
python benchmarks/make_cases.py geocoder/geocoding/raw/adresses-01.csv > benchmarks/cases.json  # regenerate queries
```

* `cases.json`: 400 queries made from random BAN addresses (exact, with a typo in the street or in the city, without
  city / postal code / number, street only) and 203 reverse positions. Deterministic.
* `golden_legacy.json`: results of the code as it was before the modernisation (against the same data).

Accuracy before / after the modernisation (share of the 400 queries answered within 100 m / 1 km of the address):
63 % / 70 % -> 87 % / 94 %.
