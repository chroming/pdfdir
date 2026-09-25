import pytest
import requests
from packaging.version import InvalidVersion

from src.updater import (
    check_for_update,
    is_updated,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_update_check_handles_multi_digit_version_segments(monkeypatch):
    monkeypatch.setattr(
        "src.updater.requests.get",
        lambda *_args, **_kwargs: FakeResponse(
            {"tag_name": "v0.3.10", "assets": []}
        ),
    )

    state = check_for_update(
        "https://github.com/chroming/pdfdir/releases",
        "v0.3.9",
    )

    assert state == "update"


def test_update_check_distinguishes_current_version(monkeypatch):
    monkeypatch.setattr(
        "src.updater.requests.get",
        lambda *_args, **_kwargs: FakeResponse(
            {"tag_name": "v0.3.10", "assets": []}
        ),
    )

    state = check_for_update(
        "https://github.com/chroming/pdfdir/releases",
        "v0.3.10",
    )

    assert state == "current"


def test_update_check_orders_beta_release_numbers(monkeypatch):
    monkeypatch.setattr(
        "src.updater.requests.get",
        lambda *_args, **_kwargs: FakeResponse(
            {"tag_name": "v0.3.0-beta40", "assets": []}
        ),
    )

    state = check_for_update(
        "https://github.com/chroming/pdfdir/releases",
        "v0.3.0-beta",
    )

    assert state == "update"


def test_update_check_reports_network_failure(monkeypatch):
    def fail_request(*_args, **_kwargs):
        raise requests.ConnectionError("network unavailable")

    monkeypatch.setattr("src.updater.requests.get", fail_request)

    with pytest.raises(requests.ConnectionError, match="network unavailable"):
        check_for_update(
            "https://github.com/chroming/pdfdir/releases",
            "v0.3.9",
        )


def test_legacy_boolean_api_preserves_update_check_errors(monkeypatch):
    def fail_request(*_args, **_kwargs):
        raise requests.Timeout("request timed out")

    monkeypatch.setattr("src.updater.requests.get", fail_request)

    with pytest.raises(requests.Timeout, match="request timed out"):
        is_updated(
            "https://github.com/chroming/pdfdir/releases",
            "v0.3.9",
        )


def test_update_check_reports_invalid_remote_version(monkeypatch):
    monkeypatch.setattr(
        "src.updater.requests.get",
        lambda *_args, **_kwargs: FakeResponse(
            {"tag_name": "not-a-version", "assets": []}
        ),
    )

    with pytest.raises(InvalidVersion, match="not-a-version"):
        check_for_update(
            "https://github.com/chroming/pdfdir/releases",
            "v0.3.9",
        )


def test_legacy_download_api_returns_release_asset(monkeypatch):
    download_url = "https://example.invalid/pdfdir.zip"
    monkeypatch.setattr(
        "src.updater.requests.get",
        lambda *_args, **_kwargs: FakeResponse(
            {
                "tag_name": "v0.3.10",
                "assets": [
                    {
                        "name": "pdfdir.zip",
                        "browser_download_url": download_url,
                    }
                ],
            }
        ),
    )

    assert (
        is_updated(
            "https://github.com/chroming/pdfdir/releases",
            "v0.3.9",
            with_dl=True,
        )
        == download_url
    )
