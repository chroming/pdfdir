
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
    VERSION = 'v0.3.0-beta'
    WINDOW_ICON = 'pdf.ico'
    HOME_PAGE_URL = 'https://github.com/chroming/pdfdir'
    HELP_PAGE_URL = 'https://github.com/chroming/pdfdir/blob/master/readme.md'
    RELEASE_PAGE_URL = 'https://github.com/chroming/pdfdir/releases'


CONFIG = Config()