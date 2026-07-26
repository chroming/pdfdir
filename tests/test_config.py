from src.config import CONFIG
from src.version import __version__


def test_display_version_matches_package_version():
    assert CONFIG.VERSION == __version__
