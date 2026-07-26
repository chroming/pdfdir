from unittest.mock import patch

from src.updater import Release, _compare_tag


def test_compare_tag_uses_numeric_components():
    assert _compare_tag("v0.10.0", "v0.9.9") is True
    assert _compare_tag("v1.0", "v1.0.0") is False
    assert _compare_tag("v0.3.0-beta41", "v0.3.0-beta40") is True
    assert _compare_tag("v0.3.0", "v0.3.0-beta40") is True
    assert _compare_tag("invalid", "v1.0") is False


def test_release_get_response_parses_json():
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"tag_name": "v1.2.3"}'

    release = Release.__new__(Release)
    release.base_api_url = "https://example.com"
    with patch("src.updater.request.urlopen", return_value=FakeResponse()):
        assert release._get_response("/latest") == {"tag_name": "v1.2.3"}
