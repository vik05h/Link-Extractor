"""Shared fixtures. Every test runs offline and writes only inside a temp folder."""

import pathlib
import socket
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fake_firebase import FakeFirebase  # noqa: E402

_real_getaddrinfo = socket.getaddrinfo


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """Fail loudly if code under test tries to reach anything but localhost."""

    def guarded(host, *args, **kwargs):
        if host not in ("127.0.0.1", "localhost"):
            raise OSError(f"Tests may not reach the network: {host}")
        return _real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded)
    monkeypatch.setenv("no_proxy", "*")
    monkeypatch.setenv("NO_PROXY", "*")


@pytest.fixture(autouse=True)
def app_data_dir(tmp_path, monkeypatch):
    """Point all app data at a temp folder so real history and settings are never touched."""
    import utils

    monkeypatch.setattr(utils, "get_app_data_dir", lambda: str(tmp_path))
    return tmp_path


@pytest.fixture
def firebase(app_data_dir):
    """A running local Firebase stand-in that the app is configured to use."""
    import utils

    server = FakeFirebase()
    server.start()
    utils.save_settings({"community_firebase_url": server.url})
    yield server
    server.stop()


@pytest.fixture
def firebase_down(app_data_dir):
    """The app is configured to use a database that cannot be reached."""
    import utils

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]
    utils.save_settings({"community_firebase_url": f"http://127.0.0.1:{closed_port}"})
    return closed_port
