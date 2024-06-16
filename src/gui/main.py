# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import sys
import webbrowser

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
# import qdarkstyle


from src.gui.main_ui import Ui_PDFdir
from src.isupdated import is_updated
from src.config import RE_DICT, CONFIG
from src.gui.base import TreeWidget
from src.convert import convert_dir_text
from src.pdf.bookmark import add_bookmark, get_bookmarks


QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


def dynamic_base_class(instance, cls_name, new_class, **kwargs):
    instance.__class__ = type(cls_name, (new_class, instance.__class__), kwargs)
    return instance


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
        self.version = CONFIG.VERSION
        self.setWindowTitle(u'{name} {version}'.format(name=CONFIG.APP_NAME, version=CONFIG.VERSION))
        self.setWindowIcon(QtGui.QIcon('{icon}'.format(icon=CONFIG.WINDOW_ICON)))
        self.dir_tree_widget = dynamic_base_class(self.dir_tree_widget, 'TreeWidget', TreeWidget)
        self.dir_tree_widget.init_connect(parents=[self, self.dir_tree_widget])
        self.dir_tree_widget.fix_column()
        self._set_connect()
        self._set_action()
        self._set_unwritable()
        self._worker = None

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.write_tree_to_pdf)
        self.level0_box.clicked.connect(self._change_level0_writable)
        self.level1_box.clicked.connect(self._change_level1_writable)
        self.level2_box.clicked.connect(self._change_level2_writable)
        self.level3_box.clicked.connect(self._change_level3_writable)
        self.level4_box.clicked.connect(self._change_level4_writable)
        self.level5_box.clicked.connect(self._change_level5_writable)
        for act in (self.dir_text_edit.textChanged,
                    self.offset_edit.textChanged,
                    self.level0_box.stateChanged,
                    self.level1_box.stateChanged,
                    self.level2_box.stateChanged,
                    self.level3_box.stateChanged,
                    self.level4_box.stateChanged,
                    self.level5_box.stateChanged,
                    self.level0_edit.textChanged,
                    self.level1_edit.textChanged,
                    self.level2_edit.textChanged,
                    self.level3_edit.textChanged,
                    self.level4_edit.textChanged,
                    self.level5_edit.textChanged,
                    self.unknown_level_box.currentIndexChanged,
                    self.space_level_box.stateChanged
                    ):
            act.connect(self.make_dir_tree)

    def _set_action(self):
        self.home_page_action.triggered.connect(self._open_home_page)
        self.help_action.triggered.connect(self._open_help_page)
        self.update_action.triggered.connect(self._open_update_page)
        self.english_action.triggered.connect(self.to_english)
        self.chinese_action.triggered.connect(self.to_chinese)

    def _set_unwritable(self):
        self.level0_edit.setEnabled(False)
        self.level1_edit.setEnabled(False)
        self.level2_edit.setEnabled(False)
        self.level3_edit.setEnabled(False)
        self.level4_edit.setEnabled(False)
        self.level5_edit.setEnabled(False)

    def _change_level0_writable(self):
        self.level0_edit.setEnabled(True if self.level0_box.isChecked() else False)

    def _change_level1_writable(self):
        self.level1_edit.setEnabled(True if self.level1_box.isChecked() else False)

    def _change_level2_writable(self):
        self.level2_edit.setEnabled(True if self.level2_box.isChecked() else False)

    def _change_level3_writable(self):
        self.level3_edit.setEnabled(True if self.level3_box.isChecked() else False)

    def _change_level4_writable(self):
        self.level4_edit.setEnabled(True if self.level4_box.isChecked() else False)

    def _change_level5_writable(self):
        self.level5_edit.setEnabled(True if self.level5_box.isChecked() else False)

    @staticmethod
    def _open_home_page():
        webbrowser.open(CONFIG.HOME_PAGE_URL, new=1)

    @staticmethod
    def _open_help_page():
        webbrowser.open(CONFIG.HELP_PAGE_URL, new=1)

    def _open_update_page(self):
        url = CONFIG.RELEASE_PAGE_URL
        try:
            updated = is_updated(url, self.version)
        except Exception:
            self.alert_msg(u"Check update failed", level="warn")
        else:
            if updated:
                self.show_status(u"Find new version", 3000)
                webbrowser.open(url, new=1)
            else:
                self.show_status(u"No update", 3000)
                self.alert_msg(u"No update")

    def show_status(self, msg, timeout=10*3600*1000):
        """Show message in status bar"""
        return self.statusbar.showMessage(msg, msecs=timeout)

    @staticmethod
    def alert_msg(msg, level="info", ok_action=None):
        box = QMessageBox()
        if level == "warn":
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("Infomation")
        else:
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Warning")
        if ok_action:
            box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            box.buttonClicked.connect(ok_action)
        box.setText(msg)
        box.exec_()

    def to_english(self):
        self.trans.load("./language/en")
        self.app.installTranslator(self.trans)
        self.retranslateUi(self)

    def to_chinese(self):
        self.app.removeTranslator(self.trans)
        self.retranslateUi(self)

    @property
    def pdf_path(self):
        return self.pdf_path_edit.text()

    @property
    def dir_text(self):
        return self.dir_text_edit.toPlainText()

    @property
    def offset_num(self):
        offset = self.offset_edit.text()
        if isinstance(offset, str) and offset.lstrip("-").isdigit():
            return int(offset)
        return 0

    @property
    def level0_text(self):
        return self.level0_edit.text() if self.level0_box.isChecked() else None

    @property
    def level1_text(self):
        return self.level1_edit.text() if self.level1_box.isChecked() else None

    @property
    def level2_text(self):
        return self.level2_edit.text() if self.level2_box.isChecked() else None

    @property
    def level3_text(self):
        return self.level3_edit.text() if self.level3_box.isChecked() else None

    @property
    def level4_text(self):
        return self.level4_edit.text() if self.level4_box.isChecked() else None

    @property
    def level5_text(self):
        return self.level5_edit.text() if self.level5_box.isChecked() else None

    @property
    def other_level_index(self):
        return self.unknown_level_box.currentIndex()

    @property
    def level_by_space(self):
        return self.space_level_box.isChecked()

    def open_file_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, u'select PDF', filter="PDF (*.pdf)")
        self.pdf_path_edit.setText(filename)
        self.dir_text_edit.setText(self.read_pdf_dir_text(filename))

    def tree_to_dict(self):
        return self.dir_tree_widget.to_dict()

    def make_dir_tree(self):
        self.dir_tree_widget.clear()
        index_dict = convert_dir_text(self.dir_text,
                                      self.offset_num,
                                      self.level0_text,
                                      self.level1_text,
                                      self.level2_text,
                                      self.level3_text,
                                      self.level4_text,
                                      self.level5_text,
                                      other=self.other_level_index,
                                      level_by_space=self.level_by_space)
        top_idx = 0
        inserted_items = {}
        children = {}
        for i, con in index_dict.items():
            if "parent" in con:
                children[i] = con
            else:
                # Insert all top items
                tree_item = QtWidgets.QTreeWidgetItem([con.get("title"),
                                                       str(con.get("num", 1)),
                                                       str(con.get("real_num", 1))])
                self.dir_tree_widget.insertTopLevelItem(top_idx, tree_item)
                inserted_items[i] = tree_item
                top_idx += 1
        # Insert all children items
        last_children_count = len(children) + 1
        while children and len(children) < last_children_count:
            keys = set(children.keys())
            for k in keys:
                con = children[k]
                p_idx = con["parent"]
                if p_idx in inserted_items:
                    p_item = inserted_items[p_idx]
                    tree_item = QtWidgets.QTreeWidgetItem([con.get("title"),
                                                           str(con.get("num", 1)),
                                                           str(con.get("real_num", 1))])
                    p_item.addChild(tree_item)
                    children.pop(k)
                    inserted_items[k] = tree_item
        for item in inserted_items.values():
            item.setExpanded(1)

    def write_tree_to_pdf(self):
        try:
            new_path = self.dict_to_pdf(self.pdf_path, self.tree_to_dict())
            self.alert_msg(u"%s Finished！" % new_path)
        except PermissionError:
            self.alert_msg(u"Permission denied！", level="warn")

    @staticmethod
    def dict_to_pdf(pdf_path, index_dict):
        return add_bookmark(pdf_path, index_dict)

    @staticmethod
    def read_pdf_dir_text(pdf_path):
        return "\n".join(get_bookmarks(pdf_path))


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


sys._excepthook = sys.excepthook
def exception_hook(exctype, value, traceback):
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = exception_hook


if __name__ == '__main__':
    run()
