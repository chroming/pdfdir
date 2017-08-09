# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import sys
import webbrowser

from PyQt4 import QtGui

from main_ui import Ui_MainWindow
from src.pdfdirectory import add_directory


class Main(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Main, self).__init__()
        self.setupUi(self)
        self.setWindowTitle(u'PDF目录添加工具 V0.1')
        self._set_connect()
        self._set_action()

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.export_pdf)

    def _set_action(self):
        self.home_page_action.triggered.connect(self._open_home_page)
        self.help_action.triggered.connect(self._open_help_page)
        self.update_action.triggered.connect(self._open_update_page)

    @staticmethod
    def _open_home_page():
        webbrowser.open('http://www.baidu.com', new=1)

    @staticmethod
    def _open_help_page():
        webbrowser.open('http://www.google.com', new=1)

    @staticmethod
    def _open_update_page():
        webbrowser.open('http://www.z.cn', new=1)

    def _get_args(self):
        pdf_path = self.pdf_path_edit.text().toUtf8().data().decode('utf-8')
        offset = int(self.offset_edit.text().toUtf8().data())
        dir_text = self.dir_text_edit.toPlainText().toUtf8().data().decode('utf-8')
        return dir_text, offset, pdf_path

    def open_file_dialog(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, u'选择PDF', filter="PDF (*.pdf)")
        self.pdf_path_edit.setText(filename)

    def export_pdf(self):
        new_path = add_directory(*self._get_args())
        self.statusbar.showMessage(u"%s 生成成功！" % new_path)


def run():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    run()