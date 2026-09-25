import os
import sys

try:
    from src.version import __version__
except ImportError:
    __version__ = "0.3.0-beta"


def resource_path(relative_path):
    """Resolve bundled resources both from source and from PyInstaller."""
    base_path = getattr(
        sys,
        "_MEIPASS",
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    candidate = os.path.join(base_path, relative_path)
    packaged = os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    if not hasattr(sys, "_MEIPASS") and not os.path.exists(candidate) and os.path.exists(packaged):
        return packaged
    return candidate


RE_DICT = {
    "level0": {
        "第1章": r"第\d章",
    },
    "level1": {
        "1.1": r"\d\.\d",
        "第1节": r"第\d节",
    },
    "level2": {
        "1.1.1": r"\d\.\d\.\d",
    },
}


class Config(object):
    APP_NAME = "PDFDir"
    VERSION = __version__
    WINDOW_ICON = resource_path("pdf.ico")
    HOME_PAGE_URL = "https://github.com/chroming/pdfdir"
    HELP_PAGE_URL = "https://github.com/chroming/pdfdir/blob/master/readme.md"
    RELEASE_PAGE_URL = "https://github.com/chroming/pdfdir/releases"
    _documents_folder = os.path.join(os.path.expanduser("~"), "Documents")
    DEFAULT_FOLDER = (
        _documents_folder
        if os.path.isdir(_documents_folder)
        else os.path.expanduser("~")
    )
    SELECTED_LEVEL = 0


CONFIG = Config()
