# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import os
import sys
import traceback
import webbrowser

import platform

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from src.config import CONFIG
from src.convert import clean_clipboard_control_chars, convert_dir_text
from src.gui.base import TreeWidget
from src.gui.main_ui import Ui_PDFdir
from src.updater import is_updated
from src.pdf.bookmark import add_bookmark, check_bookmarks, get_bookmarks
from src.pdf.page_offset import OcrCancelledError, infer_page_offset
from src.pdf.page_labels import PageLabelPlan
from src.pdf.toc import extract_toc_text
from pypdf import PdfReader

# import qdarkstyle


def dynamic_base_class(instance, cls_name, new_class, **kwargs):
    instance.__class__ = type(cls_name, (new_class, instance.__class__), kwargs)
    return instance


class ControlButtonMixin(object):
    def set_control_button(self, min_button, exit_button):
        min_button.clicked.connect(self.showMinimized)
        exit_button.clicked.connect(self.close)


class PageOffsetWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int, int)

    def __init__(self, pdf_path, dir_text):
        super(PageOffsetWorker, self).__init__()
        self.pdf_path = pdf_path
        self.dir_text = dir_text

    @QtCore.pyqtSlot()
    def run(self):
        try:
            offset = infer_page_offset(
                self.pdf_path,
                self.dir_text,
                use_ocr=True,
                progress_callback=self.progress.emit,
                cancel_callback=QtCore.QThread.currentThread().isInterruptionRequested,
            )
        except OcrCancelledError:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        else:
            self.finished.emit(offset)


class TocTextWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(int, int)

    def __init__(self, pdf_path):
        super(TocTextWorker, self).__init__()
        self.pdf_path = pdf_path

    @QtCore.pyqtSlot()
    def run(self):
        try:
            toc_text = extract_toc_text(
                self.pdf_path,
                use_ocr=True,
                progress_callback=self.progress.emit,
                cancel_callback=QtCore.QThread.currentThread().isInterruptionRequested,
            )
        except OcrCancelledError:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        else:
            self.finished.emit(toc_text)


class Main(QtWidgets.QMainWindow, Ui_PDFdir, ControlButtonMixin):
    # Minimum readable font sizes per platform
    _MIN_FONT_SIZES = {
        "Darwin": 12,   # macOS: default 8pt is too small on Retina
        "default": 8,
    }

    def __init__(self, app, trans):
        super(Main, self).__init__()
        # self.setWindowFlags(Qt.FramelessWindowHint)
        # self.menuBar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.app = app
        self.trans = trans
        self.setupUi(self)
        self._active_pdf_path = self.pdf_path_edit.text()
        self.setMinimumSize(760, 580)
        self._pdf_page_count = 0
        self._page_label_language = "zh"
        self._init_auto_offset_button()
        self._init_auto_toc_button()
        self._init_page_label_controls()
        self._fix_small_fonts()
        self.version = CONFIG.VERSION
        self.default_folder = CONFIG.DEFAULT_FOLDER
        self.setWindowTitle(
            "{name} {version}".format(name=CONFIG.APP_NAME, version=CONFIG.VERSION)
        )
        self.setWindowIcon(QtGui.QIcon("{icon}".format(icon=CONFIG.WINDOW_ICON)))
        self.dir_tree_widget = dynamic_base_class(
            self.dir_tree_widget, "TreeWidget", TreeWidget
        )
        self.dir_tree_widget.init_connect(parents=[self, self.dir_tree_widget])
        self.dir_tree_widget.fix_column()
        self._set_connect()
        self._set_action()
        self._set_unwritable()
        self._worker = None
        self._worker_thread = None
        self._worker_busy = False
        self._close_pending = False
        self._loaded_draft = self._draft_snapshot()
        self._update_page_label_summary()

    def _draft_snapshot(self):
        return (
            self.dir_text,
            self.offset_edit.text(),
            self.tree_to_dict(),
            self.page_label_mode.currentIndex(),
            self.page_label_auto.isChecked(),
            self.body_start_page.value(),
        )

    def _has_unsaved_draft(self):
        return self._draft_snapshot() != self._loaded_draft

    def _init_page_label_controls(self):
        self.page_label_group = QtWidgets.QGroupBox(self.main_widget)
        self.page_label_group.setObjectName("page_label_group")
        layout = QtWidgets.QVBoxLayout(self.page_label_group)
        self.page_label_mode = QtWidgets.QComboBox(self.page_label_group)
        self.page_label_mode.setObjectName("page_label_mode")
        layout.addWidget(self.page_label_mode)
        self.page_label_auto = QtWidgets.QCheckBox(self.page_label_group)
        self.page_label_auto.setObjectName("page_label_auto")
        self.page_label_auto.setChecked(True)
        self.body_start_page = QtWidgets.QSpinBox(self.page_label_group)
        self.body_start_page.setObjectName("body_start_page")
        self.body_start_page.setMinimum(1)
        self.body_start_page.setMaximum(999999)
        start_row = QtWidgets.QHBoxLayout()
        start_row.addWidget(self.page_label_auto)
        start_row.addWidget(self.body_start_page)
        layout.addLayout(start_row)
        self.page_label_summary = QtWidgets.QLabel(self.page_label_group)
        self.page_label_summary.setObjectName("page_label_summary")
        self.page_label_summary.setWordWrap(True)
        layout.addWidget(self.page_label_summary)
        self.verticalLayout_3.insertWidget(
            self.verticalLayout_3.indexOf(self.sub_dir_group), self.page_label_group
        )
        self._translate_page_label_controls()

    def _translate_page_label_controls(self):
        zh = self._page_label_language == "zh"
        self.page_label_group.setTitle("阅读器页码" if zh else "Reader page numbers")
        self.page_label_mode.blockSignals(True)
        selected = self.page_label_mode.currentIndex()
        self.page_label_mode.clear()
        self.page_label_mode.addItems(
            ["保留原文件页码", "前置页罗马，正文从 1 开始"]
            if zh else ["Preserve source labels", "Roman front, body from 1"]
        )
        self.page_label_mode.setCurrentIndex(max(selected, 0))
        self.page_label_mode.blockSignals(False)
        self.page_label_auto.setText("根据页差" if zh else "Use page offset")
        self.body_start_page.setPrefix("PDF 第 " if zh else "PDF page ")
        self.body_start_page.setSuffix(" 页" if zh else "")
        self._update_page_label_summary()

    def _update_page_label_summary(self):
        if not hasattr(self, "page_label_mode"):
            return
        generated = self.page_label_mode.currentIndex() == 1
        self.page_label_auto.setVisible(generated)
        self.body_start_page.setVisible(generated)
        self.body_start_page.setEnabled(generated and not self.page_label_auto.isChecked())
        if generated and self.page_label_auto.isChecked():
            suggested = self.offset_num + 1
            if suggested > 0:
                self.body_start_page.blockSignals(True)
                self.body_start_page.setValue(suggested)
                self.body_start_page.blockSignals(False)
        zh = getattr(self, "_page_label_language", "zh") == "zh"
        if not generated:
            msg = "导出时保留原 PDF 的页码规则" if zh else "Keep the source PDF page labels"
        elif self.page_label_auto.isChecked() and self.offset_num < 0:
            msg = "页差不能推导正文起始页，请手动指定" if zh else "Set body start manually for a negative offset"
        elif self._pdf_page_count and (
            (self.page_label_auto.isChecked() and self.offset_num + 1 > self._pdf_page_count)
            or self.body_start_page.value() > self._pdf_page_count
        ):
            msg = "正文起始页超过 PDF 总页数" if zh else "Body start exceeds the PDF page count"
        else:
            start = self.body_start_page.value()
            if zh:
                msg = "PDF 第 1–{} 页：i…；第 {} 页起：1…".format(start - 1, start) if start > 1 else "PDF 第 1 页起：1…"
                msg += "；将替换原有页码规则"
            else:
                msg = "PDF pages 1–{}: i…; page {} onward: 1…".format(start - 1, start) if start > 1 else "PDF page 1 onward: 1…"
                msg += "; replaces source labels"
        self.page_label_summary.setText(msg)

    def _refresh_pdf_page_count(self):
        self._pdf_page_count = 0
        if os.path.isfile(self.pdf_path):
            try:
                self._pdf_page_count = len(PdfReader(self.pdf_path).pages)
            except Exception:
                pass
        self._update_page_label_summary()

    @property
    def page_label_plan(self):
        if self.page_label_mode.currentIndex() == 0:
            return PageLabelPlan()
        if self.page_label_auto.isChecked() and self.offset_num < 0:
            raise ValueError("A negative offset cannot infer the body start page")
        start = self.offset_num + 1 if self.page_label_auto.isChecked() else self.body_start_page.value()
        return PageLabelPlan("roman-body", start)

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
            self.dir_text_edit,       # 8pt in .ui
            self.dir_tree_widget,     # 8pt in .ui
            self.space_level_box,     # 10pt in .ui
            self.sub_dir_group,       # 10pt in .ui
            self.statusbar,           # 7pt in .ui
        ]
        for widget in widgets:
            font = widget.font()
            if font.pointSize() < min_size:
                font.setPointSize(min_size)
                widget.setFont(font)
                
                # If it's a QTextEdit, it might have inline HTML styles like font-size:8pt.
                # Setting this explicitly ensures readability isn't broken by those inline styles.
                if isinstance(widget, QtWidgets.QTextEdit):
                    widget.setStyleSheet("QTextEdit { font-size: " + str(min_size) + "pt; }")

    def _init_auto_offset_button(self):
        self.auto_offset_button = QtWidgets.QPushButton(self.main_widget)
        self.auto_offset_button.setObjectName("auto_offset_button")
        self.auto_offset_button.setText("自动填充页差")
        self.verticalLayout_3.insertWidget(
            self.verticalLayout_3.indexOf(self.sub_dir_group), self.auto_offset_button
        )

    def _init_auto_toc_button(self):
        self.auto_toc_button = QtWidgets.QPushButton(self.main_widget)
        self.auto_toc_button.setObjectName("auto_toc_button")
        self.auto_toc_button.setText("自动读取目录")
        self.verticalLayout_3.insertWidget(
            self.verticalLayout_3.indexOf(self.sub_dir_group), self.auto_toc_button
        )

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self.write_tree_to_pdf)
        self.auto_offset_button.clicked.connect(self.fill_offset)
        self.auto_toc_button.clicked.connect(self.fill_toc_text)
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
        self.offset_edit.textChanged.connect(self._update_page_label_summary)
        self.page_label_mode.currentIndexChanged.connect(self._update_page_label_summary)
        self.page_label_auto.stateChanged.connect(self._update_page_label_summary)
        self.body_start_page.valueChanged.connect(self._update_page_label_summary)
        self.pdf_path_edit.editingFinished.connect(self._on_pdf_path_edited)

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
        return self.statusbar.showMessage(msg, msecs=timeout)

    @staticmethod
    def alert_msg(msg, level="info", ok_action=None):
        box = QMessageBox()
        if level == "info":
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
        if not self.trans.load("./language/en"):
            self.trans.load(os.path.join(os.path.dirname(__file__), "..", "language", "en.qm"))
        self.app.installTranslator(self.trans)
        self._retranslate_preserving_draft()
        self._page_label_language = "en"
        self._translate_page_label_controls()

    def to_chinese(self):
        self.app.removeTranslator(self.trans)
        self._retranslate_preserving_draft()
        self._page_label_language = "zh"
        self._translate_page_label_controls()

    def _retranslate_preserving_draft(self):
        editable = [
            self.dir_text_edit,
            self.offset_edit,
            self.level0_edit,
            self.level1_edit,
            self.level2_edit,
            self.level3_edit,
            self.level4_edit,
            self.level5_edit,
            self.unknown_level_box,
            self.fix_non_seq_action,
        ]
        blockers = [QtCore.QSignalBlocker(widget) for widget in editable]
        directory = self.dir_text
        offset = self.offset_edit.text()
        levels = [widget.text() for widget in editable[2:8]]
        unknown_level = self.unknown_level_box.currentIndex()
        try:
            self.retranslateUi(self)
            self.dir_text_edit.setPlainText(directory)
            self.offset_edit.setText(offset)
            for widget, value in zip(editable[2:8], levels):
                widget.setText(value)
            self.unknown_level_box.setCurrentIndex(unknown_level)
        finally:
            del blockers

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
        if filename:
            self._open_pdf(filename)

    def _on_pdf_path_edited(self):
        filename = self.pdf_path_edit.text().strip()
        if filename == self._active_pdf_path:
            return True
        # Restore the current document while its draft and possible export are
        # resolved; the new path is accepted only after that decision.
        blocker = QtCore.QSignalBlocker(self.pdf_path_edit)
        self.pdf_path_edit.setText(self._active_pdf_path)
        del blocker
        return self._open_pdf(filename)

    def _open_pdf(self, filename):
        if filename == self._active_pdf_path:
            return True
        previous_path = self._active_pdf_path
        if previous_path and self._has_unsaved_draft():
            zh = self._page_label_language == "zh"
            box = QMessageBox(self)
            box.setWindowTitle("未导出的目录修改" if zh else "Unsaved directory edits")
            box.setText(
                "打开其他文件前，如何处理当前修改？"
                if zh else "What should happen to the current edits?"
            )
            export = box.addButton("导出当前 PDF" if zh else "Export current PDF", QMessageBox.AcceptRole)
            discard = box.addButton("放弃修改" if zh else "Discard edits", QMessageBox.DestructiveRole)
            cancel = box.addButton("取消" if zh else "Cancel", QMessageBox.RejectRole)
            box.setDefaultButton(cancel)
            box.exec_()
            if box.clickedButton() == cancel:
                return False
            if box.clickedButton() == export and not self.write_tree_to_pdf():
                return False
            if box.clickedButton() != discard and box.clickedButton() != export:
                return False
        if filename:
            self.default_folder = os.path.dirname(filename)
        if previous_path:
            self.dir_text_edit.clear()
            self.offset_edit.setText("0")
        self.pdf_path_edit.setText(filename)
        self._active_pdf_path = filename
        self.page_label_mode.setCurrentIndex(0)
        self.page_label_auto.setChecked(True)
        self._refresh_pdf_page_count()

        exist_bookmarks = self.read_pdf_dir_text(filename)
        if exist_bookmarks and self.read_exist_dir:
            exist_bookmarks = clean_clipboard_control_chars(exist_bookmarks)
            self.dir_text_edit.setText(exist_bookmarks)
            self.space_level_box.setChecked(True)
        self._loaded_draft = self._draft_snapshot()
        return True

    def tree_to_dict(self):
        return self.dir_tree_widget.to_dict()

    def make_dir_tree(self):
        self.dir_tree_widget.clear()
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

    def fill_offset(self):
        if self._worker_busy:
            self.alert_msg("A background task is already running", level="warn")
            return
        if not self.pdf_path:
            self.alert_msg("Please select PDF first", level="warn")
            return
        if not self.dir_text.strip():
            self.alert_msg("Please input directory text first", level="warn")
            return

        self._worker_busy = True
        self.auto_offset_button.setEnabled(False)
        self.show_status("Inferring page offset, OCR may take a while...")

        self._worker_thread = QtCore.QThread(self)
        self._worker = PageOffsetWorker(self.pdf_path, self.dir_text)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._offset_inferred)
        self._worker.failed.connect(self._offset_failed)
        self._worker.progress.connect(self._offset_progress)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker.cancelled.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._worker.cancelled.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._offset_worker_finished)
        self._worker_thread.start()

    def fill_toc_text(self):
        if self._worker_busy:
            self.alert_msg("A background task is already running", level="warn")
            return
        if not self.pdf_path:
            self.alert_msg("Please select PDF first", level="warn")
            return

        self._worker_busy = True
        self.auto_toc_button.setEnabled(False)
        self.show_status("Reading table of contents, OCR may take a while...")

        self._worker_thread = QtCore.QThread(self)
        self._worker = TocTextWorker(self.pdf_path)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._toc_text_inferred)
        self._worker.failed.connect(self._toc_text_failed)
        self._worker.progress.connect(self._toc_progress)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker.cancelled.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._worker.cancelled.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._toc_worker_finished)
        self._worker_thread.start()

    def _offset_inferred(self, offset):
        if self._close_pending:
            return
        if offset is None:
            self.alert_msg("Could not infer page offset", level="warn")
            return
        display_offset = offset
        self.offset_edit.setText(str(display_offset))
        self.show_status(
            "Page offset inferred: {}".format(display_offset), 3000
        )

    def _offset_failed(self, message):
        if self._close_pending:
            return
        self.alert_msg("Infer page offset failed: {}".format(message), level="warn")

    def _offset_progress(self, current, total):
        self.show_status(
            "Inferring page offset with OCR: {}/{} pages".format(current, total)
        )

    def _offset_worker_finished(self):
        self.auto_offset_button.setEnabled(True)
        self._worker = None
        self._worker_thread = None
        self._worker_busy = False
        self._close_after_worker()

    def _toc_text_inferred(self, toc_text):
        if self._close_pending:
            return
        if not toc_text:
            self.alert_msg("Could not read table of contents", level="warn")
            return
        self.dir_text_edit.setPlainText(toc_text)
        self.show_status("Table of contents loaded", 3000)

    def _toc_text_failed(self, message):
        if self._close_pending:
            return
        self.alert_msg("Read table of contents failed: {}".format(message), level="warn")

    def _toc_progress(self, current, total):
        self.show_status(
            "Reading table of contents with OCR: {}/{} pages".format(current, total)
        )

    def _toc_worker_finished(self):
        self.auto_toc_button.setEnabled(True)
        self._worker = None
        self._worker_thread = None
        self._worker_busy = False
        self._close_after_worker()

    def _close_after_worker(self):
        if self._close_pending:
            QtCore.QTimer.singleShot(0, self.close)

    def closeEvent(self, event):
        if self._worker_thread and self._worker_thread.isRunning():
            self._close_pending = True
            self._worker_thread.requestInterruption()
            self.show_status("Cancelling background task...")
            event.ignore()
            return
        super(Main, self).closeEvent(event)

    def pre_check(self, path, index_dict):
        check_bookmarks(path, index_dict, self.keep_exist_dir)
        self.page_label_plan.validate(len(PdfReader(path).pages))

    def write_tree_to_pdf(self):
        if self.pdf_path != self._active_pdf_path:
            self._on_pdf_path_edited()
            return False
        try:
            index_dict = self.tree_to_dict()
            self.pre_check(self.pdf_path, index_dict)
            name, ext = os.path.splitext(self.pdf_path)
            output_path = name + "_new" + ext
            if os.path.exists(output_path):
                zh = self._page_label_language == "zh"
                box = QMessageBox(self)
                box.setWindowTitle("替换导出的 PDF" if zh else "Replace exported PDF")
                box.setText(
                    ("替换已有文件？\n{}" if zh else "Replace the existing file?\n{}").format(
                        output_path
                    )
                )
                replace = box.addButton("替换" if zh else "Replace", QMessageBox.DestructiveRole)
                cancel = box.addButton("取消" if zh else "Cancel", QMessageBox.RejectRole)
                box.setDefaultButton(cancel)
                box.exec_()
                if box.clickedButton() != replace:
                    return False
            self.export_button.setEnabled(False)
            self.show_status("Writing PDF..." if self._page_label_language == "en" else "正在写入 PDF…")
            QtWidgets.QApplication.processEvents()
            new_path = self.dict_to_pdf(
                self.pdf_path, index_dict, self.keep_exist_dir, self.page_label_plan
            )
            self.show_status(
                ("Exported: " if self._page_label_language == "en" else "已导出：")
                + new_path,
                5000,
            )
            self.alert_msg("%s Finished！" % new_path)
            self._loaded_draft = self._draft_snapshot()
            return True
        except Exception as exc:
            self.show_status(
                ("Export failed: " if self._page_label_language == "en" else "导出失败：")
                + str(exc),
                5000,
            )
            self.alert_msg(str(exc), level="warn")
            return False
        finally:
            self.export_button.setEnabled(True)

    @staticmethod
    def dict_to_pdf(pdf_path, index_dict, keep_exist_dir=False, page_label_plan=None):
        return add_bookmark(pdf_path, index_dict, keep_exist_dir, page_label_plan)

    @staticmethod
    def read_pdf_dir_text(pdf_path):
        return "\n".join(get_bookmarks(pdf_path))


def run():
    # High DPI must be set before QApplication creation
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

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


def exception_hook(exctype, value, exc_traceback):
    sys._excepthook(exctype, value, exc_traceback)
    error_message = "".join(traceback.format_exception(exctype, value, exc_traceback))
    QMessageBox.critical(None, "Unhandled Exception", error_message)
    # Optionally, call the original excepthook
    if hasattr(sys, "_excepthook"):
        sys._excepthook(exctype, value, exc_traceback)


sys.excepthook = exception_hook


if __name__ == "__main__":
    run()
