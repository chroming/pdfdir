import os
from configparser import ConfigParser

try:
    from src.version import __version__
except ImportError:
    __version__ = "0.3.0-beta"

RE_DICT = {
    "level0": {
        "第1章": "第\d章",
    },
    "level1": {
        "1.1": "\d\.\d",
        "第1节": "第\d节",
    },
    "level2": {
        "1.1.1": "\d\.\d\.\d",
    },
}


class Config(object):
    APP_NAME = "PDFDir"
    VERSION = __version__ if __version__.startswith("v") else "v0.3.0-beta"
    WINDOW_ICON = "pdf.ico"
    HOME_PAGE_URL = "https://github.com/chroming/pdfdir"
    HELP_PAGE_URL = "https://github.com/chroming/pdfdir/blob/master/readme.md"
    RELEASE_PAGE_URL = "https://github.com/chroming/pdfdir/releases"
    DEFAULT_FOLDER = os.getcwd()

    cp = ConfigParser()
    config_file = os.path.join(os.getcwd(), "config.ini")

    # TODO: In macOS, there will be "OSError: Read-only file system: '/config.ini'" When create config_file
    # Check if config.ini exist
    # if not os.path.exists(config_file):
    #     with open(config_file, 'w') as configfile:
    #         cp['LEVEL'] = {'selected_level': '0'}
    #         cp.write(configfile)

    if os.path.exists(config_file):
        cp.read("config.ini", encoding="utf-8")
        SELECTED_LEVEL = cp["LEVEL"]["selected_level"]
    else:
        SELECTED_LEVEL = 0


CONFIG = Config()
