import os
from configparser import ConfigParser

RE_DICT = {
    'level0': {
        '第1章': '第\d章',
    },

    'level1': {
        '1.1': '\d\.\d',
        '第1节': '第\d节',
    },
    'level2': {
        '1.1.1': '\d\.\d\.\d',
    }

}


class Config(object):
    APP_NAME = 'PDFDir'
    VERSION = 'v0.3.0-beta28'
    WINDOW_ICON = 'pdf.ico'
    HOME_PAGE_URL = 'https://github.com/chroming/pdfdir'
    HELP_PAGE_URL = 'https://github.com/chroming/pdfdir/blob/master/readme.md'
    RELEASE_PAGE_URL = 'https://github.com/chroming/pdfdir/releases'

    cp = ConfigParser()
    config_file = "config.ini"

    # Check if config.ini exist
    if not os.path.exists(config_file):
        with open(config_file, 'w') as configfile:
            cp['LEVEL'] = {'selected_level': '0'}
            cp.write(configfile)

    cp.read('config.ini', encoding='utf-8')
    SELECTED_LEVEL = cp['LEVEL']['selected_level']


CONFIG = Config()