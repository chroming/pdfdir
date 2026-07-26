"""
The main GUI model of project.

"""

import logging
import os
import platform
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import ClassVar

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QMessageBox

from src.config import CONFIG
from src.convert import clean_clipboard_control_chars, convert_dir_text
from src.gui.base import TreeWidgetController
from src.gui.main_ui import Ui_PDFdir
from src.pdf.bookmark import add_bookmark, get_bookmarks
from src.updater import is_updated

# import qdarkstyle

logger = logging.getLogger(__name__)
_original_excepthook = sys.excepthook


class ControlButtonMixin:
    def set_control_button(self, min_button, exit_button):
        min_button.clicked.connect(self.showMinimized)
        exit_button.clicked.connect(self.close)


class BookmarkWorkerThread(QtCore.QThread):
    result = QtCore.Signal(bool, str)

    def __init__(self, pdf_path, index_dict, keep_existing=False, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.index_dict = index_dict
        self.keep_existing = keep_existing

    def run(self):
        try:
            output_path = add_bookmark(
                self.pdf_path, self.index_dict, self.keep_existing
            )
        except PermissionError:
            self.result.emit(False, "Permission denied!")
        except Exception as error:
            logger.exception("Writing PDF bookmarks failed")
            self.result.emit(False, str(error) or type(error).__name__)
        else:
            self.result.emit(True, f"{output_path} Finished!")


class Main(QtWidgets.QMainWindow, Ui_PDFdir, ControlButtonMixin):
    # Minimum readable font sizes per platform
    _MIN_FONT_SIZES: ClassVar[dict[str, int]] = {
        "Darwin": 12,  # macOS: default 8pt is too small on Retina
        "default": 8,
    }

    def __init__(self, app, trans):
        super().__init__()
        # self.setWindowFlags(Qt.FramelessWindowHint)
        # self.menuBar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.app = app
        self.trans = trans
        self.setupUi(self)
        self._fix_small_fonts()
        self.version = CONFIG.VERSION
        self.default_folder = CONFIG.DEFAULT_FOLDER
        self.setWindowTitle(f"{CONFIG.APP_NAME} {CONFIG.VERSION}")
        self.setWindowIcon(QtGui.QIcon(str(self._resource_path(CONFIG.WINDOW_ICON))))
        self.dir_tree_controller = TreeWidgetController(
            self.dir_tree_widget, parents=[self, self.dir_tree_widget]
        )
        self.dir_tree_controller.fix_column()
        self._set_connect()
        self._set_action()
        self._set_unwritable()
        self._worker = None

    def _fix_small_fonts(self):
        """Override hardcoded small font sizes from main_ui.py for readability.

        The auto-generated UI file uses 7-10pt fonts which are unreadably small
        on macOS (especially Retina displays). This method ensures all widget
        fonts meet a minimum readable size for the current platform.
        """
        system = platform.system()
        min_size = self._MIN_FONT_SIZES.get(system, self._MIN_FONT_SIZES["default"])

        # Widgets whose hardcoded font sizes need fixing
        widgets = [
            self.dir_text_edit,  # 8pt in .ui
            self.dir_tree_widget,  # 8pt in .ui
            self.space_level_box,  # 10pt in .ui
            self.sub_dir_group,  # 10pt in .ui
            self.statusbar,  # 7pt in .ui
        ]
        for widget in widgets:
            font = widget.font()
            if font.pointSize() < min_size:
                font.setPointSize(min_size)
                widget.setFont(font)

                # If it's a QTextEdit, it might have inline HTML styles like font-size:8pt.
                # Setting this explicitly ensures readability isn't broken by those inline styles.
                if isinstance(widget, QtWidgets.QTextEdit):
                    widget.setStyleSheet(f"QTextEdit {{ font-size: {min_size}pt; }}")

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.write_tree_to_pdf)
        self.level0_box.clicked.connect(self._change_level0_writable)
        self.level1_box.clicked.connect(self._change_level1_writable)
        self.level2_box.clicked.connect(self._change_level2_writable)
        self.level3_box.clicked.connect(self._change_level3_writable)
        self.level4_box.clicked.connect(self._change_level4_writable)
        self.level5_box.clicked.connect(self._change_level5_writable)
        for act in (
            self.dir_text_edit.textChanged,
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
            self.space_level_box.stateChanged,
            self.fix_non_seq_action.changed,
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
        self.level0_edit.setEnabled(self.level0_box.isChecked())

    def _change_level1_writable(self):
        self.level1_edit.setEnabled(self.level1_box.isChecked())

    def _change_level2_writable(self):
        self.level2_edit.setEnabled(self.level2_box.isChecked())

    def _change_level3_writable(self):
        self.level3_edit.setEnabled(self.level3_box.isChecked())

    def _change_level4_writable(self):
        self.level4_edit.setEnabled(self.level4_box.isChecked())

    def _change_level5_writable(self):
        self.level5_edit.setEnabled(self.level5_box.isChecked())

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
        except Exception:  # noqa: BLE001 - an update check must never crash the GUI
            self.alert_msg("Check update failed", level="warn")
        else:
            if updated:
                self.show_status("Find new version", 3000)
                webbrowser.open(url, new=1)
            else:
                self.show_status("No update", 3000)
                self.alert_msg("No update")

    def show_status(self, msg, timeout=10 * 3600 * 1000):
        """Show message in status bar"""
        return self.statusbar.showMessage(msg, timeout)

    @staticmethod
    def alert_msg(msg, level="info", ok_action=None):
        box = QMessageBox()
        if level == "info":
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Information")
        else:
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Warning")
        if ok_action:
            box.setStandardButtons(
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            box.buttonClicked.connect(ok_action)
        box.setText(msg)
        box.exec()

    @staticmethod
    def _resource_path(relative_path):
        bundle_root = getattr(sys, "_MEIPASS", None)
        candidates = []
        if bundle_root:
            candidates.append(Path(bundle_root) / "src" / relative_path)
            candidates.append(Path(bundle_root) / relative_path)
        source_root = Path(__file__).resolve().parents[2]
        package_root = Path(__file__).resolve().parents[1]
        candidates.extend((source_root / relative_path, package_root / relative_path))
        return next((path for path in candidates if path.exists()), candidates[0])

    def _load_translation(self, language_code):
        translation_name = f"{language_code}.qm"
        candidates = (
            self._resource_path(f"language/{translation_name}"),
            Path(self.app.applicationDirPath()) / "language" / translation_name,
            Path(__file__).resolve().parent / translation_name,
        )
        return any(
            candidate.exists() and self.trans.load(str(candidate))
            for candidate in candidates
        )

    def to_english(self):
        if self._load_translation("en"):
            self.app.installTranslator(self.trans)
            self.retranslateUi(self)
        else:
            self.alert_msg("English translation file not found", level="warn")

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
        try:
            return int(offset)
        except (TypeError, ValueError):
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

    @property
    def fix_non_seq(self):
        return self.fix_non_seq_action.isChecked()

    @property
    def keep_exist_dir(self):
        return self.keep_exist_dir_action.isChecked()

    @property
    def read_exist_dir(self):
        return self.read_exist_dir_action.isChecked()

    def open_file_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "select PDF", directory=self.default_folder, filter="PDF (*.pdf)"
        )
        if not filename:
            return
        self.default_folder = os.path.dirname(filename)
        self.pdf_path_edit.setText(filename)

        exist_bookmarks = self.read_pdf_dir_text(filename)
        if exist_bookmarks and self.read_exist_dir:
            exist_bookmarks = clean_clipboard_control_chars(exist_bookmarks)
            self.dir_text_edit.setText(exist_bookmarks)
            self.space_level_box.setChecked(True)

    def tree_to_dict(self):
        return self.dir_tree_controller.to_dict()

    def make_dir_tree(self):
        self.dir_tree_controller.clear()
        index_dict = convert_dir_text(
            self.dir_text,
            self.offset_num,
            self.level0_text,
            self.level1_text,
            self.level2_text,
            self.level3_text,
            self.level4_text,
            self.level5_text,
            other=self.other_level_index,
            level_by_space=self.level_by_space,
            fix_non_seq=self.fix_non_seq,
        )
        top_idx = 0
        inserted_items = {}
        children = {}
        for i, con in index_dict.items():
            if "parent" in con:
                children[i] = con
            else:
                # Insert all top items
                tree_item = QtWidgets.QTreeWidgetItem(
                    [
                        con.get("title"),
                        str(con.get("num", 1)),
                        str(con.get("real_num", 1)),
                    ]
                )
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
                    tree_item = QtWidgets.QTreeWidgetItem(
                        [
                            con.get("title"),
                            str(con.get("num", 1)),
                            str(con.get("real_num", 1)),
                        ]
                    )
                    p_item.addChild(tree_item)
                    children.pop(k)
                    inserted_items[k] = tree_item
        for item in inserted_items.values():
            item.setExpanded(1)

    def write_tree_to_pdf(self):
        if self._worker is not None and self._worker.isRunning():
            return
        if not self.pdf_path:
            self.alert_msg("Please select a PDF file first.", level="warn")
            return

        self.show_status("Writing bookmarks to PDF...")
        self.export_button.setEnabled(False)
        self._worker = BookmarkWorkerThread(
            self.pdf_path,
            self.tree_to_dict(),
            self.keep_exist_dir,
            parent=self,
        )
        self._worker.result.connect(self._write_pdf_result)
        self._worker.finished.connect(self._write_pdf_finished)
        self._worker.start()

    def _write_pdf_result(self, succeeded, message):
        self.alert_msg(message, level="info" if succeeded else "warn")

    def _write_pdf_finished(self):
        self.show_status("Done", timeout=1000)
        self.export_button.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self.show_status("Please wait for the PDF write to finish.")
            event.ignore()
            return
        super().closeEvent(event)

    @staticmethod
    def read_pdf_dir_text(pdf_path):
        return "\n".join(get_bookmarks(pdf_path))


def run():
    app = QtWidgets.QApplication(sys.argv)
    sys.excepthook = exception_hook
    # app.setStyle('fusion')
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    trans = QtCore.QTranslator()
    # trans.load("./gui/en")
    # app.installTranslator(trans)
    window = Main(app, trans)
    window.show()
    sys.exit(app.exec())


def exception_hook(exctype, value, exc_traceback):
    error_message = "".join(traceback.format_exception(exctype, value, exc_traceback))
    if QtWidgets.QApplication.instance() is not None:
        QMessageBox.critical(None, "Unhandled Exception", error_message)
    _original_excepthook(exctype, value, exc_traceback)


if __name__ == "__main__":
    run()
