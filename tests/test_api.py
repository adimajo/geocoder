import json

import pytest

from geocoder import __version__

ADDRESS = {"address": "12, Bd des Maréchaux", "postal_code": "91120", "city": "Palaiseau"}


def strict_loads(data):
    """json.loads that rejects NaN / Infinity, which are not valid JSON"""
    def refuse(value):
        raise ValueError(f"invalid JSON constant {value}")
    return json.loads(data, parse_constant=refuse)


def test_version(client):
    response = client.get('/version')
    assert response.status_code == 200
    assert strict_loads(response.data)["version"] == __version__


def test_geocode_one(client):
    response = client.get('/geocode/12, Bd des Maréchaux/91120/Palaiseau')
    assert response.status_code == 200
    body = strict_loads(response.data)
    assert body["api_version"] == __version__
    assert body["quality"]["1"] == "Successful"
    row = body["data"][0]
    assert row["quality"] == 1
    assert row["code_insee"] == "91477"
    assert row["lon"] == pytest.approx(2.2099, abs=1e-3)
    assert row["lat"] == pytest.approx(48.7099, abs=1e-3)


def test_geocode_file(client):
    rows = [ADDRESS, {**ADDRESS, "extra": "kept"}, {"address": "x", "postal_code": None, "city": None}]
    response = client.post('/geocode_file', json=rows)
    assert response.status_code == 200
    body = strict_loads(response.data)
    assert len(body["data"]) == 3
    assert body["data"][1]["extra"] == "kept"
    assert body["data"][0]["lon"] == body["data"][1]["lon"]


def test_nothing_found_is_valid_json(client):
    response = client.post('/geocode_file', json=[{"address": None, "postal_code": None, "city": None}])
    row = strict_loads(response.data)["data"][0]
    assert row["quality"] == 6
    assert row["lon"] is None and row["lat"] is None and row["code_insee"] is None


def test_legacy_json_string_body(client):
    response = client.post('/geocode_file', json=json.dumps([ADDRESS]))
    assert response.status_code == 200
    assert strict_loads(response.data)["data"][0]["quality"] == 1


def test_numeric_postal_code(client):
    response = client.post('/geocode_file', json=[{**ADDRESS, "postal_code": 91120}])
    assert strict_loads(response.data)["data"][0]["quality"] == 1


def test_monaco_is_skipped(client):
    response = client.post('/geocode_file', json=[{**ADDRESS, "postal_code": "98000"}])
    assert strict_loads(response.data)["data"][0]["lon"] is None


@pytest.mark.parametrize("body", [
    {"address": "x"},
    "not json at all",
    '"just a string"',
    [1, 2, 3],
    [{"address": "x", "postal_code": "91120"}],  # city column missing
])
def test_invalid_input(client, body):
    kwargs = {"json": body} if not isinstance(body, str) else {"data": body, "content_type": "application/json"}
    response = client.post('/geocode_file', **kwargs)
    assert response.status_code == 400
    assert strict_loads(response.data)["errors"]


def test_too_many_rows(client):
    from geocoder.api.provider import app
    app.config["GEOCODER_MAX_ROWS"] = 2
    try:
        response = client.post('/geocode_file', json=[ADDRESS] * 3)
        assert response.status_code == 413
        assert client.post('/geocode_file', json=[ADDRESS] * 2).status_code == 200
    finally:
        app.config["GEOCODER_MAX_ROWS"] = 10_000


def test_body_too_large(client):
    from geocoder.api.provider import app
    app.config["MAX_CONTENT_LENGTH"] = 100
    try:
        assert client.post('/geocode_file', json=[ADDRESS] * 10).status_code == 413
    finally:
        app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def test_pages_and_redirections(client):
    assert client.get('/').status_code == 302
    assert client.get('/home').status_code == 200
    assert client.get('/use').status_code == 200
    assert client.get('/doc').status_code == 200
    assert client.get('/swagger.json').status_code == 200


def test_unknown_route(client):
    response = client.get('/nope', headers={"Accept": "application/json"})
    assert response.status_code == 404
    assert strict_loads(response.data)["errors"]
    response = client.get('/nope', headers={"Accept": "text/html"})
    assert response.status_code == 302


def test_security_headers(client):
    response = client.get('/home')
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert "Content-Security-Policy" not in client.get('/version').headers


def test_debug_is_off_by_default():
    from geocoder.api.provider import app
    assert not app.debug
