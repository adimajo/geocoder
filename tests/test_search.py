import pytest

import geocoder
from geocoder.geocoding import normalize, query, search


def test_exact_address():
    output = geocoder.find('91120', 'Palaiseau', '12, Bd des Maréchaux')
    assert output['quality'] == 1
    assert output['longitude'] == pytest.approx(2.209934)
    assert output['latitude'] == pytest.approx(48.709914)
    assert output['commune'] == {'nom': 'PALAISEAU', 'code_insee': '91477'}
    assert output['voie'] == {'nom': 'BOULEVARD DES MARECHAUX'}
    assert output['localisation'] == {'numero': 12}
    assert output['departement'] == {'code': '91'}


def test_missing_city_or_postal_code():
    assert geocoder.find('91120', None, '12, Bd des Maréchaux')['quality'] == 1
    output = geocoder.find(None, 'Palaiseau', '12, Bd des Maréchaux')
    assert output['quality'] == 1
    assert output['longitude'] == pytest.approx(2.209934)


def test_typos():
    for args in [('91120', 'Palaiseau', '12, Bd des Maréchx'),
                 ('91120', 'Palaiau', '12, Bd des Maréchx'),
                 ('91121', 'Palaiseau', '12, Bd des Maréchaux')]:
        output = geocoder.find(*args)
        assert output['quality'] == 1, args
        assert output['longitude'] == pytest.approx(2.209934), args


def test_street_is_searched_in_the_right_commune():
    """'Rue de Paris' exists in Orsay and in Palaiseau"""
    palaiseau = geocoder.find('91120', 'Palaiseau', '5 rue de Paris')
    orsay = geocoder.find('91400', 'Orsay', '2 rue de Paris')
    assert (palaiseau['quality'], palaiseau['commune']['nom']) == (1, 'PALAISEAU')
    assert palaiseau['longitude'] == pytest.approx(2.246)
    assert (orsay['quality'], orsay['commune']['nom']) == (1, 'ORSAY')
    assert orsay['longitude'] == pytest.approx(2.1863)


def test_street_files_are_merged_per_postal_code():
    """
    A département is made of an "adresses" and a "lieux-dits" file. Both contain the postal code 91120: a search
    restricted to that postal code must still find the streets of the "adresses" file.
    """
    postal = query.data['postal']
    assert len(postal[postal['code'] == 91120]) == 1
    output = geocoder.find('91120', 'Palaiseau', 'Rue Jacques Monod')
    assert output['quality'] == 3
    assert output['voie'] == {'nom': 'RUE JACQUES MONOD'}
    assert geocoder.find('91120', 'Palaiseau', 'Le Pileu')['voie'] == {'nom': 'LE PILEU'}


@pytest.mark.parametrize("args, quality", [
    (('91120', 'Palaiseau', '99 Boulevard des Maréchaux'), 2),  # number not found
    (('91120', 'Palaiseau', 'Boulevard des Maréchaux'), 3),  # no number
    (('91120', 'Palaiseau', None), 4),
    (('91120', None, None), 4),  # only one commune for that postal code
    (('99999', None, None), 6),
    ((None, None, None), 6),
])
def test_quality(args, quality):
    assert geocoder.find(*args)['quality'] == quality


def test_last_street_type_of_the_table_does_not_overflow():
    """Searching a street type shared by the last streets of the table used to read past the end of the table."""
    assert geocoder.find('91400', 'Orsay', '2 rue de Paris')['quality'] == 1
    assert geocoder.find('91400', 'Orsay', '2 rue inconnue')['commune']['nom'] == 'ORSAY'


def test_invalid_input_types():
    assert geocoder.find(91120, 'Palaiseau', 12)['quality'] != 1  # postal code and address must be strings
    assert geocoder.find('abc', 'Palaiseau', None)['quality'] == 4


def test_reverse():
    output = geocoder.near((2.2099, 48.7099))
    assert output['quality'] == 1
    assert output['commune']['nom'] == 'PALAISEAU'
    assert output['voie']['nom'] == 'BOULEVARD DES MARECHAUX'
    assert output['localisation']['numero'] == 12

    assert geocoder.near((2.18601, 48.69901))['commune']['nom'] == 'ORSAY'
    assert geocoder.near((2.2861, 48.8481))['commune']['nom'] == 'PARIS'
    assert geocoder.near(None)['quality'] == 6


def test_normalize():
    assert normalize.uniform_adresse("12, Bd des Maréchaux") == "12BOULEVARDDESMARECHAUX"
    assert normalize.mine("12, Bd des Maréchaux") == (12, "BOULEVARD DES MARECHAUX", "BOULEVARD")
    assert normalize.mine("") == (None, None, None)
    assert normalize.uniform_commune("St-Étienne 2") == "SAINTETIENNE"


def test_preprocessing():
    assert search.preprocessing("91120", "Palaiseau", "12 rue X") == (91120, "PALAISEAU", 12, "RUE X", "RUE")
    assert search.preprocessing(None, None, None) == (None, None, None, None, None)


def test_database_is_loaded_lazily():
    query.reset()
    assert not query.data
    geocoder.find('91120')
    assert 'voie' in query.data
