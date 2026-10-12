import gzip
import os

import pytest
import requests

from geocoder.geocoding import download


class FakeResponse:
    def __init__(self, content=b"", status=200, headers=None):
        self.content = content
        self.status_code = status
        self.ok = status < 400
        self.headers = headers if headers is not None else {"content-length": str(len(content))}

    def iter_content(self, size):
        for i in range(0, len(self.content), size):
            yield self.content[i:i + size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeSession:
    def __init__(self, files, listing=b"listing v1"):
        self.files = files
        self.listing = listing
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        assert kwargs.get("timeout"), "every request needs a timeout"
        name = url.rsplit("/", 1)[-1]
        if name == "":
            return FakeResponse(self.listing)
        if name not in self.files:
            return FakeResponse(status=404)
        if self.files[name] is None:
            raise requests.exceptions.ConnectionError("boom")
        return FakeResponse(self.files[name])


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    content = tmp_path / "content"
    monkeypatch.setattr(download, "raw_data_folder_path", str(raw))
    monkeypatch.setattr(download, "content_folder_path", str(content))
    monkeypatch.setattr(download, "server_content_file_name", str(content / "server.txt"))
    monkeypatch.setattr(download, "local_content_file_name", str(content / "local.txt"))
    monkeypatch.setattr(download, "database", str(tmp_path / "database"))
    monkeypatch.setattr(download, "dpt_list", ["01", "2A"])
    (tmp_path / "database").mkdir()
    return tmp_path


def gz(text):
    return gzip.compress(text.encode())


def fake_ban(**overrides):
    files = {"adresses-01.csv.gz": gz("a1"), "lieux-dits-01-beta.csv.gz": gz("l1"),
             "adresses-2A.csv.gz": gz("a2"), "lieux-dits-2A-beta.csv.gz": gz("l2")}
    files.update(overrides)
    return FakeSession(files)


def test_tls_is_verified_by_default():
    assert download.SSL_VERIFICATION is True
    assert download._session().verify is True


def test_download_and_decompress(workdir, monkeypatch):
    session = fake_ban()
    monkeypatch.setattr(download, "_session", lambda: session)

    assert download.check_ban_version() is True
    assert sorted(os.listdir(workdir / "raw")) == sorted(
        ["adresses-01.csv.gz", "lieux-dits-01-beta.csv.gz", "adresses-2A.csv.gz", "lieux-dits-2A-beta.csv.gz"])
    assert (workdir / "content" / "local.txt").read_bytes() == b"listing v1"

    assert download.decompress() is True
    assert (workdir / "raw" / "adresses-2A.csv").read_text() == "a2"
    assert not (workdir / "raw" / "adresses-2A.csv.gz").exists()

    assert download.remove_downloaded_raw_ban_files() is True
    assert not (workdir / "raw").exists()


def test_no_download_when_up_to_date(workdir, monkeypatch):
    session = fake_ban()
    monkeypatch.setattr(download, "_session", lambda: session)
    assert download.check_ban_version() is True
    n_calls = len(session.calls)
    assert download.check_ban_version() is False
    assert len(session.calls) == n_calls + 1  # only the listing is fetched again
    assert not (workdir / "content" / "server.txt").exists()

    session.listing = b"listing v2"
    assert download.check_ban_version() is True


def test_partial_download_is_retried_next_time(workdir, monkeypatch):
    session = fake_ban(**{"adresses-2A.csv.gz": None})  # connection error
    monkeypatch.setattr(download, "_session", lambda: session)
    with pytest.raises(RuntimeError, match="adresses-2A"):
        download.check_ban_version()
    assert not (workdir / "content" / "local.txt").exists()
    assert not [f for f in os.listdir(workdir / "raw") if f.endswith(".part")]

    session.files["adresses-2A.csv.gz"] = gz("a2")
    assert download.check_ban_version() is True


def test_http_error_is_a_failure(workdir, monkeypatch):
    session = fake_ban()
    del session.files["lieux-dits-01-beta.csv.gz"]
    monkeypatch.setattr(download, "_session", lambda: session)
    with pytest.raises(RuntimeError, match="lieux-dits-01"):
        download.check_ban_version()


def test_truncated_download_is_rejected(workdir, monkeypatch):
    class Truncated(FakeSession):
        def get(self, url, **kwargs):
            response = super().get(url, **kwargs)
            if url.endswith("adresses-01.csv.gz"):
                response.headers = {"content-length": str(len(response.content) + 10)}
            return response

    session = Truncated(fake_ban().files)
    monkeypatch.setattr(download, "_session", lambda: session)
    with pytest.raises(RuntimeError, match="adresses-01"):
        download.check_ban_version()
    assert not (workdir / "raw" / "adresses-01.csv.gz").exists()


def test_chunked_response_without_content_length(workdir, monkeypatch):
    session = fake_ban()
    original = session.get

    def get(url, **kwargs):
        response = original(url, **kwargs)
        response.headers = {}
        return response

    session.get = get
    monkeypatch.setattr(download, "_session", lambda: session)
    assert download.check_ban_version() is True
