import random

import numpy as np
import pytest

from geocoder.geocoding import ban_processing, index, query, utils
from geocoder.geocoding.similarity import Similarity


def reference_score(s, t):
    """The original, set-of-strings implementation of the score"""
    def grams(x):
        return set(list(x) + [x[i:i + 2] for i in range(0, len(x) - 1)])

    def weight(words):
        return sum(len(word) for word in words)

    a, b = grams(s), grams(t)
    inter = weight(a & b)
    union = weight(a) + weight(b) - inter
    return 0 if union == 0 else inter / union


def test_similarity_matches_the_reference_implementation():
    rng = random.Random(1)
    words = ["".join(rng.choice("ABCDE FG") for _ in range(rng.randint(0, 12))) for _ in range(150)]
    words += ["", "A", "AB", "RUE DE PARIS", "RUE DE PARI"]
    for s in words:
        similarity = Similarity(s)
        for t in words:
            assert similarity.score(t) == reference_score(s, t), (s, t)


def test_most_similar():
    values = np.array(["RUE A", "RUE B", "AVENUE C", "RUE B BIS"])
    score = Similarity("RUE B").score
    assert utils.most_similar(range(0, 4), values, score)[1:] == (1, 1)  # exact match stops the search
    assert utils.most_similar([3, 2], values, score)[1:] == (0, 3)  # rank in the given indices, index in values
    assert utils.most_similar(range(0), values, score) == (None, None, None)
    assert utils.most_similar(np.array([2, 0]), values, score)[1:] == (1, 0)
    assert utils.most_similar(range(0, 4), list(values), score)[1:] == (1, 1)


LINE = "id;fantoir;{numero};{rep};{voie};{cp};{insee};{commune};;;0;0;{lon};{lat};entrée;;;;;;;;"


def line(**kwargs):
    values = dict(numero="12", rep="", voie="Rue de la Paix", cp="75002", insee="75102", commune="Paris",
                  lon="2.33", lat="48.87")
    values.update(kwargs)
    return LINE.format(**values).split(";")


def test_get_attributes():
    assert ban_processing.get_attributes(line()) == (
        75002, "PARIS", "PARIS", "75102", "RUEDELAPAIX", "RUE DE LA PAIX", 12, "", 23300000, 488700000)


@pytest.mark.parametrize("kwargs", [
    {"cp": "abc"}, {"lon": ""}, {"lat": "x"}, {"numero": "x"}, {"numero": "99999"}, {"numero": "-1"},
    {"voie": ""}, {"voie": "R" * 48}, {"commune": ""}, {"commune": "(only parentheses)"},
])
def test_get_attributes_skips_unusable_lines(kwargs):
    assert ban_processing.get_attributes(line(**kwargs)) is None


def test_get_attributes_short_line():
    assert ban_processing.get_attributes(["only", "three", "fields"]) is None


def test_lieux_dits_have_no_number():
    fields = "id;Le Pileu;91120;91477;Palaiseau;;;0;0;2.23;48.73;commune;commune".split(";")
    attributes = ban_processing.get_attributes(fields, "lieux-dits")
    assert attributes[6:8] == (0, "")  # numero, repetition (never None: it must sort against real repetitions)


def test_database_cross_references():
    """every start/end/ref_id of the merged tables points to the right place"""
    d = query.data
    assert d['departement']['code'].tolist() == ['75', '91']
    for table, child, ref in (('postal', 'commune', 'start'), ('commune', 'voie', 'start'),
                              ('voie', 'localisation', 'start')):
        assert d[table][ref][0] == 0
        assert d[table]['end'][-1] == len(d[child])
        assert np.all(d[table]['start'][1:] == d[table]['end'][:-1])
        for i, row in enumerate(d[table]):
            assert np.all(d[child]['ref_id'][row['start']:row['end']] == i)
    for i, row in enumerate(d['departement']):
        assert np.all(d['postal']['ref_id'][row['start']:row['end']] == i)


def test_index_tables_are_sorted():
    d = query.data
    for table, column in (('postal', 'code'), ('commune', 'normalise'), ('voie', 'normalise')):
        values = d[table][column][d[table + '_index']]
        assert np.all(values[:-1] <= values[1:])


def test_merge_shifts_references():
    one = ban_processing.build_tables(ban_processing.read_files("tests/data/raw/adresses-75.csv"))
    one['departement'] = np.array([("75", 0, len(one['postal']))], dtype=index.dtypes['departement'])
    merged = index.merge([one, one])
    assert len(merged['postal']) == 2 * len(one['postal'])
    assert merged['postal']['ref_id'].tolist() == [0, 1]
    assert merged['departement']['start'].tolist() == [0, 1]
    assert merged['commune']['ref_id'].tolist() == [0, 1]
    assert merged['voie']['start'][len(one['voie']):].min() == len(one['localisation'])
    assert merged['localisation']['ref_id'][len(one['localisation']):].min() == len(one['voie'])
