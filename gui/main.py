# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import sys
import webbrowser

from PyQt5 import QtWidgets, QtCore

from .main_ui import Ui_PDFdir

from src.pdfdirectory import add_directory


class Main(QtWidgets.QMainWindow, Ui_PDFdir):
    def __init__(self, app, trans):
        super(Main, self).__init__()
        self.app = app
        self.trans = trans
        self.setupUi(self)
        self.setWindowTitle(u'PDFdir V0.2')
        self._set_connect()
        self._set_action()

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.export_pdf)

    def _set_action(self):
        self.home_page_action.triggered.connect(self._open_home_page)
        self.help_action.triggered.connect(self._open_help_page)
        self.update_action.triggered.connect(self._open_update_page)
        self.english_action.triggered.connect(self.to_englist)
        self.chinese_action.triggered.connect(self.to_chinese)

    @staticmethod
    def _open_home_page():
        webbrowser.open('https://github.com/chroming/pdfdir', new=1)

    @staticmethod
    def _open_help_page():
        webbrowser.open('https://github.com/chroming/pdfdir/blob/master/readme.md', new=1)

    @staticmethod
    def _open_update_page():
        webbrowser.open('https://github.com/chroming/pdfdir/releases', new=1)

    def to_englist(self):
        self.trans.load("./gui/en")
        self.app.installTranslator(self.trans)
        self.retranslateUi(self)

    def to_chinese(self):
        self.app.removeTranslator(self.trans)
        self.retranslateUi(self)

    def _get_args(self):
        pdf_path = self.pdf_path_edit.text()
        offset = int(self.offset_edit.text())
        dir_text = self.dir_text_edit.toPlainText()
        level0 = self.level0_edit.text() if self.level0_box.isChecked() else None
        level1 = self.level1_edit.text() if self.level1_box.isChecked() else None
        level2 = self.level2_edit.text() if self.level2_box.isChecked() else None
        other = self.select_level_box.currentIndex()
        return dir_text, offset, pdf_path, level0, level1, level2, other

    def open_file_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, u'select PDF', filter="PDF (*.pdf)")
        self.pdf_path_edit.setText(filename)

    def export_pdf(self):
        new_path = add_directory(*self._get_args())
        self.statusbar.showMessage(u"%s Finished！" % new_path, 3000)


def run():
    app = QtWidgets.QApplication(sys.argv)
    trans = QtCore.QTranslator()
    # trans.load("./gui/en")
    # app.installTranslator(trans)
    window = Main(app, trans)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()