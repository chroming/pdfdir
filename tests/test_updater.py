from unittest.mock import patch

import pytest

from src.updater import Release, _compare_tag, is_updated


@pytest.mark.parametrize(
    ("latest", "current", "expected"),
    [
        ("v0.10.0", "v0.9.9", True),
        ("v1.0", "v1.0.0", False),
        ("v0.3.0-beta41", "v0.3.0-beta40", True),
        ("v0.3.0", "v0.3.0-beta40", True),
        ("invalid", "v1.0", False),
        (None, "v1.0", False),
    ],
)
def test_compare_tag_uses_pep440_versions(latest, current, expected):
    assert _compare_tag(latest, current) is expected


class _FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_release_builds_api_url_and_parses_json():
    with patch(
        "src.updater.request.urlopen",
        return_value=_FakeResponse(b'{"tag_name": "v1.2.3"}'),
    ) as urlopen:
        release = Release("https://github.com/example/project")

    assert release.base_api_url == "https://api.github.com/repos/example/project/releases"
    assert release.latest_tag == "v1.2.3"
    request = urlopen.call_args.args[0]
    assert request.full_url.endswith("/releases/latest")
    assert request.headers["User-agent"] == "pdfdir"


@pytest.mark.parametrize(
    "failure",
    [
        OSError("offline"),
        _FakeResponse(b"not json"),
    ],
)
def test_release_network_and_json_failures_return_empty_response(failure):
    release = Release.__new__(Release)
    release.base_api_url = "https://example.com"
    context = (
        patch("src.updater.request.urlopen", side_effect=failure)
        if isinstance(failure, Exception)
        else patch("src.updater.request.urlopen", return_value=failure)
    )

    with context:
        assert release._get_response("/latest") == {}


def test_is_updated_supports_boolean_and_download_results():
    response = {
        "tag_name": "v2.0.0",
        "assets": [
            {
                "name": "pdfdir.zip",
                "browser_download_url": "https://example.com/pdfdir.zip",
            }
        ],
    }
    with patch.object(Release, "_get_response", return_value=response):
        assert is_updated("https://github.com/example/project", "v1.0.0") is True
        assert (
            is_updated(
                "https://github.com/example/project",
                "v1.0.0",
                with_dl=True,
            )
            == "https://example.com/pdfdir.zip"
        )
        assert is_updated("https://github.com/example/project", "v2.0.0") is False


def test_is_updated_returns_false_when_latest_release_is_unavailable():
    with patch.object(Release, "_get_response", return_value={}):
        assert is_updated("https://github.com/example/project", "v1.0.0") is False


def test_download_selection_handles_names_and_out_of_range_indexes():
    response = {
        "assets": [
            {"name": "one.zip", "browser_download_url": "https://example.com/one"},
            {"name": "two.zip", "browser_download_url": "https://example.com/two"},
        ]
    }

    assert Release._get_download_url(response, name="two.zip") == (
        "https://example.com/two"
    )
    assert Release._get_download_url(response, name="missing.zip") is None
    assert Release._get_download_url(response, order_num=5) is None
    assert Release._get_download_url(response, order_num=-1) is None
    assert Release._get_download_url({}, order_num=0) is None
