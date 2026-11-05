import pytest

import firebase_client
from firebase_client import FirebaseError


def test_reads_and_writes_json(firebase):
    firebase_client.request("games_meta/a", "PUT", {"title": "A"})
    assert firebase_client.request("games_meta/a") == {"title": "A"}
    assert firebase.read("games_meta/a") == {"title": "A"}


def test_missing_data_is_none_and_not_an_error(firebase):
    assert firebase_client.request("games_meta/missing") is None


def test_refused_requests_raise_with_the_status(firebase):
    firebase.deny = lambda method, path, auth: True
    with pytest.raises(FirebaseError) as caught:
        firebase_client.request("reports/x", "PUT", {"a": 1})
    assert caught.value.status == 401
    assert caught.value.denied


def test_unreachable_database_raises_without_a_status(firebase_down):
    with pytest.raises(FirebaseError) as caught:
        firebase_client.request("games_meta", timeout=1.0)
    assert caught.value.status is None
    assert caught.value.unreachable


def test_admin_key_is_sent_to_the_server_but_never_appears_in_errors(firebase):
    firebase.deny = lambda method, path, auth: True
    with pytest.raises(FirebaseError) as caught:
        firebase_client.request("reports/x", "DELETE", auth="super-secret-value")
    assert firebase.requests[-1]["auth"] == "super-secret-value"
    assert "super-secret-value" not in str(caught.value)


@pytest.mark.parametrize("key", ["../secret", "a/b", "a.b", "a#b", "a$b", "a[b]", "", "a b"])
def test_unsafe_database_keys_are_rejected(key):
    assert firebase_client.safe_key(key) is None


@pytest.mark.parametrize("key", ["rep_1700000000_ab12cd", "c_1_ff", "god-of-war-ragnarok"])
def test_normal_database_keys_are_accepted(key):
    assert firebase_client.safe_key(key) == key


def test_database_url_comes_from_settings_with_a_default(app_data_dir):
    import utils

    assert firebase_client.database_url() == firebase_client.DEFAULT_DATABASE_URL
    utils.save_settings({"community_firebase_url": "https://other.example/"})
    assert firebase_client.database_url() == "https://other.example"
