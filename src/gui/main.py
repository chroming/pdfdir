# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import sys
import webbrowser

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt
# import qdarkstyle


from src.gui.main_ui import Ui_PDFdir
from src.pdfdirectory import add_directory
from src.isupdated import is_updated
from src.config import RE_DICT
from src.gui.base import TreeWidget
from src.convert import text_to_list, split_page_num
from src.pdf.bookmark import add_bookmark


QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


def dynamic_base_class(instance, cls_name, new_class):
    instance.__class__ = type(cls_name, (new_class, instance.__class__), {})
    return instance


class WindowDragMixin(object):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, QMouseEvent):
        if QMouseEvent.buttons() and Qt.LeftButton:
            self.move(QMouseEvent.globalPos() - self.m_DragPosition)
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_drag = False


class ControlButtonMixin(object):
    def set_control_button(self, min_button, exit_button):
        min_button.clicked.connect(self.showMinimized)
        exit_button.clicked.connect(self.close)


class Main(QtWidgets.QMainWindow, Ui_PDFdir, ControlButtonMixin):
    def __init__(self, app, trans):
        super(Main, self).__init__()
        # self.setWindowFlags(Qt.FramelessWindowHint)
        # self.menuBar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.app = app
        self.trans = trans
        self.setupUi(self)
        self.version = 'v0.2.2'
        self.setWindowTitle(u'PDFdir %s' % self.version)
        self.dir_tree_widget = dynamic_base_class(self.dir_tree_widget, 'TreeWidget', TreeWidget)
        self.dir_tree_widget.init_connect(parents=[self, self.dir_tree_widget])
        self._set_connect()
        self._set_action()
        self._set_unwritable()

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.export_pdf)
        self.export_button.clicked.connect(self.write_tree_to_pdf)

        self.dir_text_edit.textChanged.connect(self.to_tree_widget)

        self.level0_box.clicked.connect(self._change_level0_writable)
        self.level1_box.clicked.connect(self._change_level1_writable)
        self.level2_box.clicked.connect(self._change_level2_writable)

        self.level0_button.clicked.connect(lambda: self._level_button_clicked('level0'))
        self.level1_button.clicked.connect(lambda: self._level_button_clicked('level1'))
        self.level2_button.clicked.connect(lambda: self._level_button_clicked('level2'))

    def _set_action(self):
        self.home_page_action.triggered.connect(self._open_home_page)
        self.help_action.triggered.connect(self._open_help_page)
        self.update_action.triggered.connect(self._open_update_page)
        self.english_action.triggered.connect(self.to_englist)
        self.chinese_action.triggered.connect(self.to_chinese)

    def _set_unwritable(self):
        self.level0_edit.setEnabled(False)
        self.level1_edit.setEnabled(False)
        self.level2_edit.setEnabled(False)

    def _level_button_clicked(self, level_str):
        context_menu = QtWidgets.QMenu()
        for k, v in RE_DICT.get(level_str).items():
            context_menu.addAction(k, lambda v=v: self._insert_to_editor(level_str, v))
        context_menu.exec_(QtGui.QCursor.pos())

    def _insert_to_editor(self, level_str, text):
        editor = getattr(self, level_str + '_edit')
        if editor.isEnabled():
            editor.insert(text)

    def _change_level0_writable(self):
        self.level0_edit.setEnabled(True if self.level0_box.isChecked() else False)

    def _change_level1_writable(self):
        self.level1_edit.setEnabled(True if self.level1_box.isChecked() else False)

    def _change_level2_writable(self):
        self.level2_edit.setEnabled(True if self.level2_box.isChecked() else False)

    @staticmethod
    def _open_home_page():
        webbrowser.open('https://github.com/chroming/pdfdir', new=1)

    @staticmethod
    def _open_help_page():
        webbrowser.open('https://github.com/chroming/pdfdir/blob/master/readme.md', new=1)

    def _open_update_page(self):
        url = 'https://github.com/chroming/pdfdir/releases'
        try:
            updated = is_updated(url, self.version)
        except Exception:
            self.statusbar.showMessage(u"Check update failed", 3000)
        else:
            if updated:
                self.statusbar.showMessage(u"Find new version", 3000)
                webbrowser.open(url, new=1)
            else:
                self.statusbar.showMessage(u"No update", 3000)

    def to_englist(self):
        self.trans.load("./language/en")
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

    @property
    def pdf_path(self):
        return self.pdf_path_edit.text()

    def open_file_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, u'select PDF', filter="PDF (*.pdf)")
        self.pdf_path_edit.setText(filename)

    def tree_to_dict(self):
        return self.dir_tree_widget.to_dict()

    def to_tree_widget(self):
        self.dir_tree_widget.clear()
        last_num = 0
        for line in text_to_list(self.dir_text_edit.toPlainText()):
            title, num = split_page_num(line)
            num = max(num, last_num)
            self.dir_tree_widget.insertTopLevelItem(self.dir_tree_widget.topLevelItemCount(), QtWidgets.QTreeWidgetItem([title, str(num)]))
            last_num = num

    def export_pdf(self):
        new_path = add_directory(*self._get_args())
        self.statusbar.showMessage(u"%s Finished！" % new_path, 3000)

    def write_tree_to_pdf(self):
        return self.dict_to_pdf(self.pdf_path, self.tree_to_dict())

    @staticmethod
    def dict_to_pdf(pdf_path, index_dict):
        return add_bookmark(pdf_path, index_dict)

def run():
    app = QtWidgets.QApplication(sys.argv)
    # app.setStyle('fusion')
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    trans = QtCore.QTranslator()
    # trans.load("./gui/en")
    # app.installTranslator(trans)
    window = Main(app, trans)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run()