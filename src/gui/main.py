# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import sys
import webbrowser

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QErrorMessage
# import qdarkstyle


from src.gui.main_ui import Ui_PDFdir
from src.pdfdirectory import add_directory
from src.isupdated import is_updated
from src.config import RE_DICT, CONFIG
from src.gui.base import TreeWidget
from src.convert import convert_dir_text
from src.pdf.bookmark import add_bookmark


QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)


def dynamic_base_class(instance, cls_name, new_class, **kwargs):
    instance.__class__ = type(cls_name, (new_class, instance.__class__), kwargs)
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
        self.version = CONFIG.VERSION
        self.setWindowTitle(u'{name} {version}'.format(name=CONFIG.APP_NAME, version=CONFIG.VERSION))
        self.setWindowIcon(QtGui.QIcon('{icon}'.format(icon=CONFIG.WINDOW_ICON)))
        self.error_message = QErrorMessage()
        self.dir_tree_widget = dynamic_base_class(self.dir_tree_widget, 'TreeWidget', TreeWidget)
        self.dir_tree_widget.init_connect(parents=[self, self.dir_tree_widget])
        # self.add_pagenum_box.setMinimum(-1000)
        self._set_connect()
        self._set_action()
        # self._set_unwritable()

        # self.adv_group.setEnabled(False)

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.write_tree_to_pdf)
        for act in (self.dir_text_edit.textChanged,
                    self.offset_edit.textChanged,
                    self.level0_box.stateChanged,
                    self.level1_box.stateChanged,
                    self.level2_box.stateChanged,
                    self.level0_edit.textChanged,
                    self.level1_edit.textChanged,
                    self.level2_edit.textChanged,
                    self.unknown_level_box.currentIndexChanged
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

    def _add_pagenum_to_item(self, item):
        current_num = int(item.text(1))
        add_num = self.add_pagenum_box.value()
        self.dir_tree_widget.set_pagenum(item, max(current_num + add_num, 0), )

    def _add_selected_pagenum(self):
        selected_items = self.dir_tree_widget.selectedItems()
        for item in selected_items:
            self._add_pagenum_to_item(item)

    def _add_all_pagenum(self):
        for item in self.dir_tree_widget.all_items:
            self._add_pagenum_to_item(item)

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
            self.statusbar.showMessage(u"Check update failed", 3000)
        else:
            if updated:
                self.statusbar.showMessage(u"Find new version", 3000)
                webbrowser.open(url, new=1)
            else:
                self.statusbar.showMessage(u"No update", 3000)

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
    def other_level_index(self):
        return self.unknown_level_box.currentIndex()

    def open_file_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, u'select PDF', filter="PDF (*.pdf)")
        self.pdf_path_edit.setText(filename)

    def tree_to_dict(self):
        return self.dir_tree_widget.to_dict()

    def make_dir_tree(self):
        self.dir_tree_widget.clear()
        index_dict = convert_dir_text(self.dir_text,
                                      self.offset_num,
                                      self.level0_text,
                                      self.level1_text,
                                      self.level2_text,
                                      self.other_level_index)
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

    def export_pdf(self):
        new_path = add_directory(*self._get_args())
        self.statusbar.showMessage(u"%s Finished！" % new_path, 3000)

    def write_tree_to_pdf(self):
        try:
            new_path = self.dict_to_pdf(self.pdf_path, self.tree_to_dict())
            self.statusbar.showMessage(u"%s Finished！" % new_path, 3000)
        except PermissionError:
            self.error_message.showMessage(u"Permission denied！")

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


sys._excepthook = sys.excepthook
def exception_hook(exctype, value, traceback):
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = exception_hook


if __name__ == '__main__':
    run()