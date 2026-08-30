# -*- coding: utf-8 -*-

"""
The main GUI model of project.

"""

import os
import re
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from pathlib import Path

import platform

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QMessageBox

from src.config import CONFIG
from src.convert import clean_clipboard_control_chars, convert_dir_text
from src.gui.base import TreeWidget
from src.gui.main_ui import Ui_PDFdir
from src.updater import check_for_update
from src.pdf.bookmark import (
    BookmarkPageError,
    add_bookmark,
    check_bookmarks,
    get_bookmarks,
    get_bookmarks_strict,
)
from src.pdf.cancellation import OperationCancelled
from src.pdf.page_offset import infer_page_offset
from src.pdf.toc import extract_toc_text

# import qdarkstyle


def dynamic_base_class(instance, cls_name, new_class, **kwargs):
    instance.__class__ = type(cls_name, (new_class, instance.__class__), kwargs)
    return instance


class ControlButtonMixin(object):
    def set_control_button(self, min_button, exit_button):
        min_button.clicked.connect(self.showMinimized)
        exit_button.clicked.connect(self.close)


class PageOffsetWorker(QtCore.QObject):
    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    progress = QtCore.Signal(int, int)

    def __init__(self, pdf_path, dir_text):
        super(PageOffsetWorker, self).__init__()
        self.pdf_path = pdf_path
        self.dir_text = dir_text
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def is_cancelled(self):
        return self._cancelled.is_set()

    @QtCore.Slot()
    def run(self):
        try:
            offset = infer_page_offset(
                self.pdf_path,
                self.dir_text,
                use_ocr=True,
                progress_callback=self.progress.emit,
                cancel_check=self.is_cancelled,
            )
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        else:
            self.finished.emit(offset)


class TocTextWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()
    progress = QtCore.Signal(int, int)

    def __init__(self, pdf_path):
        super(TocTextWorker, self).__init__()
        self.pdf_path = pdf_path
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def is_cancelled(self):
        return self._cancelled.is_set()

    @QtCore.Slot()
    def run(self):
        try:
            toc_text = extract_toc_text(
                self.pdf_path,
                use_ocr=True,
                progress_callback=self.progress.emit,
                cancel_check=self.is_cancelled,
            )
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        else:
            self.finished.emit(toc_text)


class PdfWriteWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()

    def __init__(
        self,
        pdf_path,
        index_dict,
        keep_existing=False,
        output_path=None,
    ):
        super(PdfWriteWorker, self).__init__()
        self.pdf_path = pdf_path
        self.index_dict = index_dict
        self.keep_existing = keep_existing
        self.output_path = output_path
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def is_cancelled(self):
        return self._cancelled.is_set()

    @QtCore.Slot()
    def run(self):
        try:
            new_path = add_bookmark(
                self.pdf_path,
                self.index_dict,
                self.keep_existing,
                cancel_check=self.is_cancelled,
                output_path=self.output_path,
            )
        except OperationCancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        else:
            self.finished.emit(new_path)


class UpdateCheckWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)

    def __init__(self, url, version):
        super(UpdateCheckWorker, self).__init__()
        self.url = url
        self.version = version

    @QtCore.Slot()
    def run(self):
        try:
            result = check_for_update(self.url, self.version)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)


class Main(QtWidgets.QMainWindow, Ui_PDFdir, ControlButtonMixin):
    # Minimum readable font sizes per platform
    _MIN_FONT_SIZES = {
        "Darwin": 12,   # macOS: default 8pt is too small on Retina
        "default": 8,
    }
    _MESSAGES = {
        "zh": {
            "advanced_title": "识别设置",
            "advanced_mode": "层级识别方式",
            "no_document": "尚未选择 PDF",
            "select_pdf": "选择 PDF",
            "checking_update": "正在检查更新…",
            "check_update_failed": "检查更新失败",
            "find_new_version": "发现新版本",
            "no_update": "当前已是最新版本",
            "information": "提示",
            "warning": "警告",
            "import_title": "导入已有书签",
            "replace_draft": "所选 PDF 已有书签。是否替换当前目录草稿？",
            "import_draft": "所选 PDF 已有书签。是否导入为目录草稿？",
            "import_replace_action": "导入并替换",
            "import_action": "导入为草稿",
            "keep_draft_action": "保留当前草稿",
            "skip_import_action": "暂不导入",
            "invalid_pdf": "无法打开所选 PDF：{message}",
            "switch_draft_title": "切换 PDF",
            "switch_draft": "当前目录草稿属于另一份 PDF。请选择要如何处理这份草稿。",
            "carry_draft_action": "沿用草稿",
            "clear_draft_action": "清空草稿",
            "cancel_action": "取消",
            "discard_draft_title": "放弃未生成的更改",
            "discard_draft": "目录或书签预览还有未生成的更改。",
            "discard_close_action": "放弃并关闭",
            "keep_editing_action": "继续编辑",
            "task_running": "已有后台任务正在运行",
            "select_pdf_first": "请先选择 PDF",
            "input_toc_first": "请先输入目录文本",
            "offset_working": "正在识别页差，OCR 可能需要一些时间…",
            "toc_working": "正在从 PDF 识别目录，OCR 可能需要一些时间…",
            "offset_discarded": "文档已更改，已丢弃旧的页差结果",
            "offset_failed": "页差识别失败",
            "offset_empty": "无法识别页差",
            "offset_done": "已识别页差：{value}",
            "offset_error": "页差识别失败：{message}",
            "ocr_unavailable": "当前环境未安装扫描版 OCR 可选依赖。文字版 PDF 仍可直接识别；如需识别扫描版，请在终端执行：pip install -r requirements_ocr.txt",
            "offset_progress": "正在 OCR 识别页差：{current}/{total} 页",
            "toc_discarded": "文档已更改，已丢弃旧的目录结果",
            "toc_failed": "目录识别失败",
            "toc_empty": "无法从 PDF 识别目录",
            "toc_done": "目录识别完成，可继续编辑",
            "toc_error": "目录识别失败：{message}",
            "toc_progress": "正在 OCR 识别目录：{current}/{total} 页",
            "task_cancelled": "后台任务已取消",
            "cancelling": "正在取消后台任务…",
            "ready_select_pdf": "选择 PDF，然后输入或识别目录。",
            "ready_enter_toc": "输入目录文本，或从当前 PDF 识别目录。",
            "ready_generate": "已准备好，可生成 {count} 条书签。",
            "dirty": "有未生成的更改。",
            "preview_title": "书签预览",
            "preview_title_with_count": "书签预览 (共 {count} 条)",
            "preview_empty": "输入或识别目录后，在这里校对书签标题、层级和页码。",
            "preview_edit_hint": "双击或按 F2 编辑；拖动调整顺序与层级；Delete 删除。",
            "preview_compact_hint": "编辑：F2 · 双击 · 拖动 · Delete",
            "preview_manual_hint": "预览已手工调整。编辑左侧目录或识别规则会重建并替换这些调整。",
            "preview_manual_compact_hint": "预览已手工调整；修改左侧内容会重建。",
            "preview_reset": "目录或识别规则已更改，预览已重新生成",
            "invalid_regex": "{level} 的正则表达式无效：{message}",
            "empty_title": "第 {row} 条书签缺少标题，请在预览中修正。",
            "invalid_preview_page": "第 {row} 条书签页码必须是整数，请在预览中修正。",
            "export_needs_pdf": "请先选择有效的 PDF。",
            "export_needs_toc": "请先输入可生成书签的目录文本。",
            "export_needs_valid_preview": "请先修正预览中的问题：{message}",
            "toc_needs_pdf": "选择有效的 PDF 后可识别目录。",
            "offset_needs_input": "选择有效的 PDF 并输入目录后可识别页差。",
            "keep_source_bookmarks": "保留源 PDF 书签",
            "keep_source_description": "在新书签之外保留源 PDF 中原有的书签。",
            "imported_keep_disabled": "已有书签已导入为草稿；再次保留会产生重复书签。",
            "generated_task": "正在生成 {source}\n→ {output}",
            "no_bookmarks": "没有可生成的有效书签",
            "page_below_minimum": "书签页码 {page} 小于 1，请在预览中修正",
            "page_above_maximum": "书签页码 {page} 超出 PDF 总页数 {total}，请在预览中修正",
            "output_changed": "输出位置已被其他程序占用，PDFdir 未覆盖该文件。请检查后重试，应用会改用新的编号文件名。",
            "generation_cancelled": "已取消生成 PDF",
            "generating": "正在生成带书签的 PDF…",
            "generated": "已生成：{path}",
            "generated_ready": "PDF 已生成，可立即打开。",
            "open_generated": "打开生成的 PDF",
            "open_generated_description": "使用系统默认应用打开刚生成的 PDF",
            "generated_missing": "生成的 PDF 已被移动或删除，请重新生成。",
            "generated_open_failed": "无法打开生成的 PDF，请检查系统默认 PDF 应用后重试。",
            "generation_failed": "PDF 生成失败",
            "generation_error": "生成带书签的 PDF 失败：{message}",
        },
        "en": {
            "advanced_title": "Recognition Settings",
            "advanced_mode": "Hierarchy detection",
            "no_document": "No PDF selected",
            "select_pdf": "Select PDF",
            "checking_update": "Checking for updates…",
            "check_update_failed": "Update check failed",
            "find_new_version": "A new version is available",
            "no_update": "You are up to date",
            "information": "Information",
            "warning": "Warning",
            "import_title": "Import existing bookmarks",
            "replace_draft": "The selected PDF has bookmarks. Replace the current TOC draft?",
            "import_draft": "The selected PDF has bookmarks. Import them as the TOC draft?",
            "import_replace_action": "Import and Replace",
            "import_action": "Import as Draft",
            "keep_draft_action": "Keep Current Draft",
            "skip_import_action": "Not Now",
            "invalid_pdf": "Could not open the selected PDF: {message}",
            "switch_draft_title": "Switch PDF",
            "switch_draft": "The current TOC draft belongs to another PDF. Choose how to handle this draft.",
            "carry_draft_action": "Keep Draft",
            "clear_draft_action": "Clear Draft",
            "cancel_action": "Cancel",
            "discard_draft_title": "Discard ungenerated changes",
            "discard_draft": "The TOC or bookmark preview has ungenerated changes.",
            "discard_close_action": "Discard and Close",
            "keep_editing_action": "Keep Editing",
            "task_running": "A background task is already running",
            "select_pdf_first": "Select a PDF first",
            "input_toc_first": "Enter TOC text first",
            "offset_working": "Detecting page offset; OCR may take a while…",
            "toc_working": "Recognizing the TOC; OCR may take a while…",
            "offset_discarded": "The document changed; the old offset result was discarded",
            "offset_failed": "Page offset detection failed",
            "offset_empty": "Could not detect a page offset",
            "offset_done": "Page offset detected: {value}",
            "offset_error": "Page offset detection failed: {message}",
            "ocr_unavailable": "This environment does not have the optional OCR dependencies installed. Text PDFs still work; for scans, install them via: pip install -r requirements_ocr.txt",
            "offset_progress": "Detecting page offset with OCR: {current}/{total} pages",
            "toc_discarded": "The document changed; the old TOC result was discarded",
            "toc_failed": "TOC recognition failed",
            "toc_empty": "Could not recognize a TOC from the PDF",
            "toc_done": "TOC recognized; you can keep editing",
            "toc_error": "TOC recognition failed: {message}",
            "toc_progress": "Recognizing TOC with OCR: {current}/{total} pages",
            "task_cancelled": "Background task cancelled",
            "cancelling": "Cancelling background task…",
            "ready_select_pdf": "Select a PDF, then enter or recognize its TOC.",
            "ready_enter_toc": "Enter TOC text or recognize it from the current PDF.",
            "ready_generate": "Ready to generate {count} bookmarks.",
            "dirty": "There are ungenerated changes.",
            "preview_title": "Bookmark preview",
            "preview_title_with_count": "Bookmark preview ({count})",
            "preview_empty": "Enter or recognize a TOC, then verify bookmark titles, hierarchy, and pages here.",
            "preview_edit_hint": "Double-click or press F2 to edit; drag to reorder or nest; Delete removes.",
            "preview_compact_hint": "Edit: F2 · double-click · drag · Delete",
            "preview_manual_hint": "Preview adjusted manually. Editing TOC text or recognition rules will rebuild and replace these changes.",
            "preview_manual_compact_hint": "Preview adjusted manually; changing the left side rebuilds it.",
            "preview_reset": "TOC text or recognition rules changed; the preview was rebuilt",
            "invalid_regex": "Invalid regular expression for {level}: {message}",
            "empty_title": "Bookmark {row} has no title; correct it in the preview.",
            "invalid_preview_page": "Bookmark {row} must use integer page numbers; correct it in the preview.",
            "export_needs_pdf": "Select a valid PDF first.",
            "export_needs_toc": "Enter TOC text that produces at least one bookmark.",
            "export_needs_valid_preview": "Correct the preview first: {message}",
            "toc_needs_pdf": "Select a valid PDF to recognize its TOC.",
            "offset_needs_input": "Select a valid PDF and enter a TOC to detect page offset.",
            "keep_source_bookmarks": "Keep source PDF bookmarks",
            "keep_source_description": "Keep the source PDF's existing bookmarks in addition to the new bookmarks.",
            "imported_keep_disabled": "Existing bookmarks were imported as the draft; keeping them again would create duplicates.",
            "generated_task": "Generating {source}\n→ {output}",
            "no_bookmarks": "There are no valid bookmarks to generate",
            "page_below_minimum": "Bookmark page {page} is below 1; correct it in the preview",
            "page_above_maximum": "Bookmark page {page} exceeds the PDF's {total} pages; correct it in the preview",
            "output_changed": "Another program occupied the output path. PDFdir did not overwrite it; inspect the file and retry with the next numbered name.",
            "generation_cancelled": "PDF generation cancelled",
            "generating": "Generating bookmarked PDF…",
            "generated": "Generated: {path}",
            "generated_ready": "Generated PDF is ready to open.",
            "open_generated": "Open generated PDF",
            "open_generated_description": "Open the generated PDF with the system default application",
            "generated_missing": "The generated PDF was moved or removed. Generate it again.",
            "generated_open_failed": "Could not open the generated PDF. Check the system default PDF application and retry.",
            "generation_failed": "PDF generation failed",
            "generation_error": "Could not generate bookmarked PDF: {message}",
        },
    }

    def __init__(self, app, trans):
        super(Main, self).__init__()
        # self.setWindowFlags(Qt.FramelessWindowHint)
        # self.menuBar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.app = app
        self.trans = trans
        self.setupUi(self)
        self._language = "zh"
        self._worker = None
        self._worker_thread = None
        self._worker_busy = False
        self._task_context = None
        self._close_requested = False
        self._close_retry_scheduled = False
        self._active_pdf_path = ""
        self._source_has_bookmarks = False
        self._draft_imported_from_source = False
        self._preview_manually_adjusted = False
        self._preview_validation_error = ""
        self._regex_validation_error = ""
        self._rebuilding_tree = False
        self._dirty_baseline = None
        self._update_worker = None
        self._update_thread = None
        self._task_focus_origin = None
        self._status_override_active = False
        self._action_status_message = ""
        self._last_generated_path = ""
        self._last_generated_signature = None
        self._primary_action_mode = "generate"
        self._allow_close_once = False
        self._dirty_close_box = None
        self._dirty_discard_button = None
        self._compact_shell = False
        self._regex_single_column = None
        self._build_product_shell()
        self._apply_product_style()
        self._fix_small_fonts()
        self.version = CONFIG.VERSION
        self.default_folder = CONFIG.DEFAULT_FOLDER
        self.setWindowTitle(
            "{name} {version} [*]".format(
                name=CONFIG.APP_NAME,
                version=CONFIG.VERSION,
            )
        )
        self.setWindowIcon(QtGui.QIcon("{icon}".format(icon=CONFIG.WINDOW_ICON)))
        self.dir_tree_widget = dynamic_base_class(
            self.dir_tree_widget, "TreeWidget", TreeWidget
        )
        self.dir_tree_widget.init_connect(parents=[self, self.dir_tree_widget])
        self.dir_tree_widget.set_preview_changed_callback(
            self._on_preview_changed
        )
        self.dir_tree_widget.fix_column()
        self._set_connect()
        self._set_action()
        self._set_unwritable()
        self._configure_workspace()
        self._apply_language()
        self.make_dir_tree()
        self._mark_clean()
        self._update_action_availability()

    def _configure_workspace(self):
        self.setAcceptDrops(True)
        self.workspace_splitter.setStretchFactor(0, 1)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes([500, 500])
        self.offset_edit.setValidator(QtGui.QIntValidator(-99999, 99999, self))
        self.open_button.setShortcut(QtGui.QKeySequence.Open)
        self.export_button.setShortcut(QtGui.QKeySequence("Ctrl+Return"))
        self._save_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence.Save,
            self,
        )
        self._save_shortcut.setContext(
            QtCore.Qt.WidgetWithChildrenShortcut
        )
        self._save_shortcut.activated.connect(self._on_save_shortcut)
        self._escape_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence.Cancel,
            self,
        )
        self._escape_shortcut.setContext(
            QtCore.Qt.WidgetWithChildrenShortcut
        )
        self._escape_shortcut.activated.connect(self.cancel_active_task)
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._status_timeout)
        self.dir_text_edit.installEventFilter(self)
        self.dir_tree_widget.viewport().installEventFilter(self)
        for editor in (self.dir_text_edit, self.dir_tree_widget):
            policy = editor.sizePolicy()
            policy.setVerticalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
            editor.setSizePolicy(policy)
        # Operation state is presented next to the affected action. Keeping the
        # legacy status bar visible duplicated that information and consumed
        # scarce vertical space at large system text sizes.
        self.statusbar.setVisible(False)
        self.pdf_path_edit.setAccessibleName("PDF 文件路径")
        self.dir_text_edit.setAccessibleName("可编辑目录文本")
        self.dir_tree_widget.setAccessibleName("书签层级预览")
        self.output_path_edit.setAccessibleName("输出 PDF 路径")
        self.page_title_label.setAccessibleName("PDF 书签编辑器")
        self.export_button.setAccessibleDescription(
            "根据右侧预览生成新的带书签 PDF"
        )
        self._regex_editors = [
            self.level0_edit,
            self.level1_edit,
            self.level2_edit,
            self.level3_edit,
            self.level4_edit,
            self.level5_edit,
        ]
        self._regex_boxes = [
            self.level0_box,
            self.level1_box,
            self.level2_box,
            self.level3_box,
            self.level4_box,
            self.level5_box,
        ]
        self.keep_exist_dir_box.setVisible(False)
        self.keep_exist_dir_action.setVisible(False)
        self.advanced_mode_box.setCurrentIndex(
            self.level_mode_box.currentIndex()
        )
        self.advanced_dialog.setTabOrder(
            self.advanced_mode_box,
            self.level0_box,
        )
        advanced_focus_chain = [
            self.advanced_mode_box,
            self.level0_box,
            self.level0_edit,
            self.level1_box,
            self.level1_edit,
            self.level2_box,
            self.level2_edit,
            self.level3_box,
            self.level3_edit,
            self.level4_box,
            self.level4_edit,
            self.level5_box,
            self.level5_edit,
            self.unknown_level_box,
            self.fix_non_seq_box,
            self.read_exist_dir_box,
            self.advanced_button_box.button(
                QtWidgets.QDialogButtonBox.Close
            ),
        ]
        self._advanced_focus_chain = [
            control
            for control in advanced_focus_chain
            if control is not None
        ]
        for control in self._advanced_focus_chain:
            control.installEventFilter(self)
        for current, following in zip(
            self._advanced_focus_chain,
            self._advanced_focus_chain[1:],
        ):
            self.advanced_dialog.setTabOrder(current, following)
        self._apply_type_scale()
        self._update_accessible_layout_constraints()
        self._update_level_mode(self.level_mode_box.currentIndex())
        self._update_output_path()

    def _on_save_shortcut(self):
        if self.export_button.isVisible() and self.export_button.isEnabled():
            self.export_button.click()

    def _build_product_shell(self):
        """Compose the single-task desktop shell around Designer-owned controls."""
        root = self.root_layout
        while root.count():
            root.takeAt(0)
        root.setContentsMargins(24, 16, 24, 14)
        root.setSpacing(12)

        self.page_header = QtWidgets.QWidget(self.main_widget)
        self.page_header.setObjectName("page_header")
        header_layout = QtWidgets.QVBoxLayout(self.page_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        self.page_title_label = QtWidgets.QLabel(self.page_header)
        self.page_title_label.setObjectName("page_title_label")
        self.page_subtitle_label = QtWidgets.QLabel(self.page_header)
        self.page_subtitle_label.setObjectName("page_subtitle_label")
        header_layout.addWidget(self.page_title_label)
        header_layout.addWidget(self.page_subtitle_label)
        root.addWidget(self.page_header)

        self.document_frame = QtWidgets.QFrame(self.main_widget)
        self.document_frame.setObjectName("document_frame")
        document_layout = QtWidgets.QVBoxLayout(self.document_frame)
        document_layout.setContentsMargins(14, 10, 14, 10)
        document_layout.setSpacing(7)
        self.document_name_label = QtWidgets.QLabel(self.document_frame)
        self.document_name_label.setObjectName("document_name_label")
        self.document_name_label.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored,
            QtWidgets.QSizePolicy.Preferred,
        )
        document_layout.addWidget(self.document_name_label)
        document_layout.addLayout(self.file_layout)
        root.addWidget(self.document_frame)

        self.workspace_frame = QtWidgets.QFrame(self.main_widget)
        self.workspace_frame.setObjectName("workspace_frame")
        workspace_layout = QtWidgets.QVBoxLayout(self.workspace_frame)
        workspace_layout.setContentsMargins(14, 12, 14, 0)
        workspace_layout.setSpacing(10)
        workspace_layout.addWidget(self.workspace_splitter, 1)

        self.tools_divider = QtWidgets.QFrame(self.workspace_frame)
        self.tools_divider.setObjectName("tools_divider")
        self.tools_divider.setFrameShape(QtWidgets.QFrame.HLine)
        workspace_layout.addWidget(self.tools_divider)
        self.tools_frame = QtWidgets.QWidget(self.workspace_frame)
        self.tools_frame.setObjectName("tools_frame")
        tools_layout = QtWidgets.QVBoxLayout(self.tools_frame)
        tools_layout.setContentsMargins(0, 0, 0, 10)
        while self.quick_settings_layout.count():
            self.quick_settings_layout.takeAt(0)
        self.tools_controls_layout = QtWidgets.QGridLayout()
        self.tools_controls_layout.setHorizontalSpacing(8)
        self.tools_controls_layout.setVerticalSpacing(6)
        tools_layout.addLayout(self.tools_controls_layout)
        self._tools_compact = None
        self._layout_tool_controls(False)
        workspace_layout.addWidget(self.tools_frame)
        root.addWidget(self.workspace_frame, 1)

        self.preview_empty_label = QtWidgets.QLabel(
            self.dir_tree_widget.viewport()
        )
        self.preview_empty_label.setObjectName("preview_empty_label")
        self.preview_empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_empty_label.setWordWrap(True)
        self.preview_empty_label.setMargin(8)
        self.preview_empty_label.setAttribute(
            QtCore.Qt.WA_TransparentForMouseEvents,
            True,
        )

        self.action_frame = QtWidgets.QFrame(self.main_widget)
        self.action_frame.setObjectName("action_frame")
        action_layout = QtWidgets.QVBoxLayout(self.action_frame)
        action_layout.setContentsMargins(14, 10, 14, 10)
        action_layout.setSpacing(6)
        self.action_status_label = QtWidgets.QLabel(self.action_frame)
        self.action_status_label.setObjectName("action_status_label")
        self.action_status_label.setMinimumHeight(18)
        self.action_status_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        action_layout.addWidget(self.action_status_label)
        while self.output_layout.count():
            self.output_layout.takeAt(0)
        self.action_controls_layout = QtWidgets.QGridLayout()
        self.action_controls_layout.setHorizontalSpacing(10)
        self.action_controls_layout.setVerticalSpacing(6)
        self.action_divider = QtWidgets.QFrame(self.action_frame)
        self.action_divider.setObjectName("action_divider")
        self.action_divider.setFrameShape(QtWidgets.QFrame.VLine)
        self._actions_compact = None
        self._layout_action_controls(False)
        action_layout.addLayout(self.action_controls_layout)
        root.addWidget(self.action_frame)

        self.advanced_dialog = QtWidgets.QDialog(self)
        self.advanced_dialog.setObjectName("advanced_dialog")
        self.advanced_dialog.setModal(True)
        self.advanced_dialog.setMinimumSize(680, 300)
        self.advanced_dialog.resize(720, 320)
        advanced_dialog_layout = QtWidgets.QVBoxLayout(self.advanced_dialog)
        advanced_dialog_layout.setContentsMargins(18, 16, 18, 14)
        advanced_dialog_layout.setSpacing(14)
        advanced_mode_row = QtWidgets.QHBoxLayout()
        advanced_mode_row.setSpacing(8)
        self.advanced_mode_label = QtWidgets.QLabel(self.advanced_dialog)
        self.advanced_mode_box = QtWidgets.QComboBox(self.advanced_dialog)
        self.advanced_mode_box.addItems(["", ""])
        self.advanced_mode_label.setBuddy(self.advanced_mode_box)
        advanced_mode_row.addWidget(self.advanced_mode_label)
        advanced_mode_row.addWidget(self.advanced_mode_box, 1)
        advanced_dialog_layout.addLayout(advanced_mode_row)
        self.advanced_widget.setParent(self.advanced_dialog)
        self.advanced_widget.setVisible(True)
        advanced_dialog_layout.addWidget(self.advanced_widget, 1)
        self.regex_error_label = QtWidgets.QLabel(self.advanced_dialog)
        self.regex_error_label.setObjectName("regex_error_label")
        self.regex_error_label.setWordWrap(True)
        self.regex_error_label.setVisible(False)
        advanced_dialog_layout.addWidget(self.regex_error_label)
        self.advanced_button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Close,
            parent=self.advanced_dialog,
        )
        self.advanced_button_box.rejected.connect(self.advanced_dialog.reject)
        advanced_dialog_layout.addWidget(self.advanced_button_box)
        self.advanced_dialog.finished.connect(
            lambda _result: self.advanced_button.setFocus()
        )

        while self.advanced_options_layout.count():
            self.advanced_options_layout.takeAt(0)
        self.advanced_options_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        self.advanced_options_layout.setSpacing(8)
        unmatched_row = QtWidgets.QHBoxLayout()
        unmatched_row.setSpacing(8)
        unmatched_row.addWidget(self.unknown_level_label)
        unmatched_row.addWidget(self.unknown_level_box)
        unmatched_row.addStretch(1)
        self.advanced_options_layout.addLayout(unmatched_row)
        self.advanced_options_layout.addWidget(self.fix_non_seq_box)
        self.advanced_options_layout.addWidget(self.read_exist_dir_box)
        self.advanced_options_layout.addStretch(1)
        self.advanced_layout.setContentsMargins(0, 0, 0, 8)
        self.advanced_button.setCheckable(False)
        self._layout_regex_controls(False)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            layout.takeAt(0)

    def _layout_tool_controls(self, compact):
        if self._tools_compact == compact:
            return
        self._tools_compact = compact
        layout = self.tools_controls_layout
        for widget in (
            self.level_mode_label,
            self.level_mode_box,
            self.offset_label,
            self.offset_edit,
            self.auto_offset_button,
            self.advanced_button,
        ):
            layout.removeWidget(widget)
        self._clear_layout(layout)
        for column in range(7):
            layout.setColumnStretch(column, 0)
        if compact:
            layout.addWidget(self.level_mode_label, 0, 0)
            layout.addWidget(self.level_mode_box, 0, 1)
            layout.setColumnStretch(2, 1)
            layout.addWidget(self.advanced_button, 0, 3)
            layout.addWidget(self.offset_label, 1, 0)
            layout.addWidget(self.offset_edit, 1, 1)
            layout.addWidget(self.auto_offset_button, 1, 2)
        else:
            layout.addWidget(self.level_mode_label, 0, 0)
            layout.addWidget(self.level_mode_box, 0, 1)
            layout.addWidget(self.offset_label, 0, 2)
            layout.addWidget(self.offset_edit, 0, 3)
            layout.addWidget(self.auto_offset_button, 0, 4)
            layout.setColumnStretch(5, 1)
            layout.addWidget(self.advanced_button, 0, 6)
        layout.invalidate()
        self.tools_frame.updateGeometry()
        if self.tools_frame.layout():
            self.tools_frame.layout().invalidate()
        if hasattr(self, "root_layout"):
            self.root_layout.invalidate()

    def _layout_action_controls(self, compact):
        if self._actions_compact == compact:
            return
        self._actions_compact = compact
        layout = self.action_controls_layout
        for widget in (
            self.keep_exist_dir_box,
            self.action_divider,
            self.output_label,
            self.output_path_edit,
            self.cancel_button,
            self.export_button,
        ):
            layout.removeWidget(widget)
        self._clear_layout(layout)
        for column in range(6):
            layout.setColumnStretch(column, 0)
        self.action_divider.setVisible(not compact)
        if compact:
            layout.addWidget(self.keep_exist_dir_box, 0, 0)
            layout.addWidget(self.output_label, 0, 1)
            layout.addWidget(self.output_path_edit, 0, 2, 1, 3)
            layout.setColumnStretch(2, 1)
            layout.setColumnStretch(0, 1)
            layout.addWidget(self.cancel_button, 1, 3)
            layout.addWidget(self.export_button, 1, 4)
        else:
            layout.addWidget(self.keep_exist_dir_box, 0, 0)
            layout.addWidget(self.action_divider, 0, 1)
            layout.addWidget(self.output_label, 0, 2)
            layout.addWidget(self.output_path_edit, 0, 3)
            layout.setColumnStretch(3, 1)
            layout.addWidget(self.cancel_button, 0, 4)
            layout.addWidget(self.export_button, 0, 5)
        layout.invalidate()
        self.action_frame.updateGeometry()
        if self.action_frame.layout():
            self.action_frame.layout().invalidate()
        if hasattr(self, "root_layout"):
            self.root_layout.invalidate()

    def _layout_regex_controls(self, single_column):
        if self._regex_single_column == single_column:
            return
        self._regex_single_column = single_column
        controls = tuple(
            zip(
                (
                    self.level0_box,
                    self.level1_box,
                    self.level2_box,
                    self.level3_box,
                    self.level4_box,
                    self.level5_box,
                ),
                (
                    self.level0_edit,
                    self.level1_edit,
                    self.level2_edit,
                    self.level3_edit,
                    self.level4_edit,
                    self.level5_edit,
                ),
            )
        )
        for box, editor in controls:
            self.regex_grid.removeWidget(box)
            self.regex_grid.removeWidget(editor)
        for column in range(4):
            self.regex_grid.setColumnStretch(column, 0)
        for index, (box, editor) in enumerate(controls):
            if single_column:
                row, column = index, 0
            else:
                row, column = divmod(index, 2)
                column *= 2
            self.regex_grid.addWidget(box, row, column)
            self.regex_grid.addWidget(editor, row, column + 1)
        if single_column:
            self.regex_grid.setColumnStretch(1, 1)
        else:
            self.regex_grid.setColumnStretch(1, 1)
            self.regex_grid.setColumnStretch(3, 1)
        self.regex_grid.invalidate()
        self.advanced_widget.updateGeometry()

    def _large_text_mode(self):
        return self.app.font().pointSizeF() >= 18

    def _update_accessible_layout_constraints(self):
        """Keep the two core editors usable when system text is enlarged."""
        large_text = self._large_text_mode()
        numbering_mode = self.level_mode_box.currentIndex() == 1
        if large_text:
            line_height = QtGui.QFontMetrics(self.app.font()).lineSpacing()
            self.setMinimumSize(900, 700)
            self.dir_text_edit.setMinimumHeight(line_height * 3 + 12)
            self.dir_tree_widget.setMinimumHeight(line_height * 3 + 32)
            self.advanced_dialog.setMinimumSize(
                720,
                600 if numbering_mode else 360,
            )
        else:
            self.setMinimumSize(780, 560)
            self.dir_text_edit.setMinimumHeight(0)
            self.dir_tree_widget.setMinimumHeight(0)
            self.advanced_dialog.setMinimumSize(
                680,
                360 if numbering_mode else 220,
            )
        self._layout_regex_controls(large_text)

    def _reflow_controls(self):
        if not hasattr(self, "tools_controls_layout"):
            return
        tool_controls = (
            self.level_mode_label,
            self.level_mode_box,
            self.offset_label,
            self.offset_edit,
            self.auto_offset_button,
            self.advanced_button,
        )
        action_controls = (
            self.keep_exist_dir_box,
            self.output_label,
            self.output_path_edit,
            self.cancel_button,
            self.export_button,
        )
        tool_width = sum(widget.sizeHint().width() for widget in tool_controls)
        action_width = sum(
            widget.sizeHint().width() for widget in action_controls
        )
        large_font = self._large_text_mode()
        self.document_name_label.setVisible(not large_font)
        self.action_status_label.setMinimumHeight(
            self.action_status_label.fontMetrics().lineSpacing() + 8
        )
        self._layout_tool_controls(
            large_font or self.tools_frame.width() < tool_width + 80
        )
        self._layout_action_controls(
            large_font or self.action_frame.width() < action_width + 80
        )
        self._update_tree_headers(compact=large_font)
        self.root_layout.invalidate()
        self.root_layout.activate()
        self._render_action_status()

    def _apply_product_style(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget#main_widget {
                background-color: #f5f5f7;
                color: #1d1d1f;
            }
            QLabel#page_title_label {
                font-weight: 600;
                color: #1d1d1f;
            }
            QLabel#page_subtitle_label, QLabel#editor_hint_label,
            QLabel#preview_hint_label, QLabel#pdf_path_label,
            QLabel#output_label, QLabel#level_mode_label, QLabel#offset_label {
                color: #6e6e73;
            }
            QLabel#preview_empty_label {
                color: #8e8e93;
                background: transparent;
            }
            QLabel#action_status_label {
                color: #6e6e73;
            }
            QLabel#action_status_label[statusKind="working"] {
                color: #0066cc;
                font-weight: 600;
            }
            QLabel#action_status_label[statusKind="error"],
            QLabel#regex_error_label {
                color: #b3261e;
                font-weight: 500;
            }
            QLabel#action_status_label[statusKind="success"] {
                color: #137333;
                font-weight: 600;
            }
            QLabel#document_name_label, QLabel#dir_text_label,
            QLabel#preview_label {
                font-weight: 600;
                color: #1d1d1f;
            }
            QFrame#document_frame, QFrame#action_frame {
                background-color: #ffffff;
                border: 1px solid #e1e1e6;
                border-radius: 8px;
            }
            QFrame#workspace_frame {
                background-color: #ffffff;
                border: 1px solid #dcdce2;
                border-radius: 10px;
            }
            QFrame#workspace_frame QWidget,
            QFrame#workspace_frame QSplitter {
                background-color: #ffffff;
            }
            QFrame#tools_divider {
                color: #e5e5ea;
                max-height: 1px;
            }
            QFrame#action_divider {
                color: #e1e1e6;
                max-width: 1px;
            }
            QSplitter::handle {
                background-color: #e5e5ea;
                width: 1px;
                margin: 0 6px;
            }
            QLineEdit {
                color: #1d1d1f;
                background-color: #ffffff;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 22px;
                selection-background-color: #dbeafe;
                selection-color: #1d1d1f;
            }
            QLineEdit:focus {
                border: 2px solid #0066cc;
                padding: 3px 7px;
            }
            QLineEdit:read-only {
                color: #6e6e73;
                background-color: #f7f7f9;
                border-color: #e5e5ea;
            }
            QLineEdit:disabled {
                color: #8e8e93;
                background-color: #f2f2f7;
                border-color: #e1e1e6;
            }
            QLineEdit[invalid="true"] {
                border: 2px solid #b3261e;
                background-color: #fff8f7;
            }
            QTextEdit#dir_text_edit {
                color: #1d1d1f;
                background-color: #ffffff;
                border: 1px solid #dcdce2;
                border-radius: 6px;
                padding: 8px 10px;
                selection-background-color: #dbeafe;
                selection-color: #1d1d1f;
            }
            QTextEdit#dir_text_edit:focus {
                border: 2px solid #0066cc;
                padding: 7px 9px;
            }
            QTextEdit#dir_text_edit:disabled {
                color: #8e8e93;
                background-color: #f2f2f7;
                border-color: #e1e1e6;
            }
            QTreeWidget#dir_tree_widget {
                color: #1d1d1f;
                background-color: #fafafc;
                border: 1px solid #dcdce2;
                border-radius: 6px;
                show-decoration-selected: 1;
            }
            QTreeWidget#dir_tree_widget:focus {
                border: 2px solid #0066cc;
            }
            QTreeWidget#dir_tree_widget:disabled {
                color: #8e8e93;
                background-color: #f2f2f7;
            }
            QTreeWidget#dir_tree_widget::item {
                min-height: 28px;
                padding: 2px 4px;
                border: none;
                border-radius: 4px;
            }
            QTreeWidget#dir_tree_widget::item:hover {
                background-color: #f0f4f9;
            }
            QTreeWidget#dir_tree_widget::item:selected {
                background-color: #e0edff;
                color: #004085;
                font-weight: 500;
            }
            QTreeWidget#dir_tree_widget::branch:has-children:!has-siblings:closed,
            QTreeWidget#dir_tree_widget::branch:closed:has-children:has-siblings {
                image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'><path d='M2.5 1.5l3 2.5-3 2.5' fill='none' stroke='%238e8e93' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>");
            }
            QTreeWidget#dir_tree_widget::branch:open:has-children:!has-siblings,
            QTreeWidget#dir_tree_widget::branch:open:has-children:has-siblings {
                image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'><path d='M1.5 2.5l2.5 3 2.5-3' fill='none' stroke='%238e8e93' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>");
            }
            QHeaderView::section {
                background-color: #f2f2f7;
                color: #55555c;
                border: none;
                border-bottom: 1px solid #dcdce2;
                padding: 6px 10px;
                font-weight: 600;
            }
            QComboBox {
                color: #1d1d1f;
                background-color: #ffffff;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                padding: 4px 28px 4px 10px;
                min-height: 22px;
            }
            QComboBox:hover {
                background-color: #fbfbfd;
                border-color: #b0b0b8;
            }
            QComboBox:focus {
                border: 2px solid #0066cc;
                padding: 3px 27px 3px 9px;
            }
            QComboBox:disabled {
                color: #8e8e93;
                background-color: #f2f2f7;
                border-color: #e1e1e6;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' fill='none' stroke='%236e6e73' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>");
                width: 10px;
                height: 6px;
            }
            QComboBox QAbstractItemView {
                color: #1d1d1f;
                background-color: #ffffff;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                padding: 4px;
                selection-background-color: #e0edff;
                selection-color: #004085;
            }
            QPushButton {
                min-height: 30px;
                padding: 0 14px;
                color: #1d1d1f;
                background-color: #f2f2f7;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e5e5ea;
                border-color: #c7c7cc;
            }
            QPushButton:pressed {
                background-color: #dcdce2;
                border-color: #b0b0b8;
            }
            QPushButton:focus {
                border: 2px solid #0066cc;
            }
            QPushButton:disabled {
                color: #a1a1a6;
                background-color: #f7f7f9;
                border-color: #e5e5ea;
            }
            QPushButton#export_button {
                min-height: 32px;
                padding: 0 18px;
                color: #ffffff;
                background-color: #0066cc;
                border: 1px solid #005bb5;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton#export_button:hover {
                background-color: #0055b3;
                border-color: #004999;
            }
            QPushButton#export_button:pressed {
                background-color: #004085;
                border-color: #003366;
            }
            QPushButton#export_button:focus {
                border: 2px solid #003f80;
            }
            QPushButton#export_button:disabled {
                color: #ffffff;
                background-color: #b0c4de;
                border-color: #b0c4de;
            }
            QPushButton#cancel_button {
                min-height: 32px;
                padding: 0 14px;
                color: #b3261e;
                background-color: #fdf2f2;
                border: 1px solid #f5c2c0;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton#cancel_button:hover {
                background-color: #fae5e5;
                border-color: #eb9f9d;
            }
            QPushButton#cancel_button:pressed {
                background-color: #f7d5d4;
                border-color: #de7e7b;
            }
            QPushButton#cancel_button:focus {
                border: 2px solid #b3261e;
            }
            QPushButton#advanced_button {
                color: #0066cc;
                background-color: transparent;
                border: 1px solid transparent;
                padding: 0 8px;
            }
            QPushButton#advanced_button:hover {
                color: #0055b3;
                background-color: #eef4ff;
                border-radius: 6px;
            }
            QPushButton#advanced_button:focus {
                color: #004085;
                background-color: #e0edff;
                border: 2px solid #0066cc;
                border-radius: 6px;
            }
            QPushButton#advanced_button:disabled {
                color: #9a9aa1;
                background-color: transparent;
            }
            QCheckBox:focus {
                color: #003f80;
                background-color: #e8f2ff;
                border-radius: 4px;
            }
            QStatusBar {
                color: #6e6e73;
                background-color: #f5f5f7;
                border-top: 0;
            }
            QDialog#advanced_dialog {
                background-color: #f5f5f7;
            }
            QDialog#advanced_dialog QGroupBox {
                font-weight: 600;
                background-color: #ffffff;
                border: 1px solid #dedee3;
                border-radius: 8px;
                margin-top: 10px;
                padding: 12px 10px 10px;
            }
            QDialog#advanced_dialog QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            """
        )

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
            self.dir_text_edit,
            self.dir_tree_widget,
            self.sub_dir_group,
            self.statusbar,
        ]
        for widget in widgets:
            font = widget.font()
            if font.pointSize() < min_size:
                font.setPointSize(min_size)
                widget.setFont(font)

    def _apply_type_scale(self):
        base_font = QtGui.QFont(self.app.font())
        base_size = base_font.pointSizeF()
        if base_size <= 0:
            base_size = 12

        title_font = QtGui.QFont(base_font)
        title_font.setPointSizeF(base_size + 5)
        title_font.setWeight(QtGui.QFont.DemiBold)
        self.page_title_label.setFont(title_font)

        section_font = QtGui.QFont(base_font)
        section_font.setWeight(QtGui.QFont.DemiBold)
        for label in (
            self.document_name_label,
            self.dir_text_label,
            self.preview_label,
        ):
            label.setFont(section_font)

        header_font = QtGui.QFont(base_font)
        header_font.setPointSizeF(max(base_size - 1, 10))
        header_font.setWeight(QtGui.QFont.DemiBold)
        self.dir_tree_widget.header().setFont(header_font)

        for editor in (self.dir_text_edit, self.dir_tree_widget):
            editor_font = editor.font()
            if abs(editor_font.pointSizeF() - base_size) > 0.1:
                editor.setFont(base_font)

    def _set_connect(self):
        self.open_button.clicked.connect(self.open_file_dialog)
        self.export_button.clicked.connect(self._run_primary_action)
        self.cancel_button.clicked.connect(self.cancel_active_task)
        self.auto_offset_button.clicked.connect(self.fill_offset)
        self.auto_toc_button.clicked.connect(self.fill_toc_text)
        self.advanced_button.clicked.connect(self._open_advanced_dialog)
        self.level_mode_box.currentIndexChanged.connect(
            self._update_level_mode
        )
        self.level_mode_box.currentIndexChanged.connect(
            self.advanced_mode_box.setCurrentIndex
        )
        self.advanced_mode_box.currentIndexChanged.connect(
            self.level_mode_box.setCurrentIndex
        )
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
            self.level_mode_box.currentIndexChanged,
            self.fix_non_seq_box.stateChanged,
        ):
            act.connect(self.make_dir_tree)
        self.pdf_path_edit.textChanged.connect(self._update_output_path)
        self.pdf_path_edit.editingFinished.connect(
            self._commit_typed_pdf_path
        )
        self.dir_text_edit.textChanged.connect(self._update_action_availability)
        self.fix_non_seq_action.toggled.connect(
            self.fix_non_seq_box.setChecked
        )
        self.keep_exist_dir_action.toggled.connect(
            self.keep_exist_dir_box.setChecked
        )
        self.read_exist_dir_action.toggled.connect(
            self.read_exist_dir_box.setChecked
        )
        self.fix_non_seq_box.toggled.connect(
            self.fix_non_seq_action.setChecked
        )
        self.keep_exist_dir_box.toggled.connect(
            self.keep_exist_dir_action.setChecked
        )
        self.read_exist_dir_box.toggled.connect(
            self.read_exist_dir_action.setChecked
        )
        self.keep_exist_dir_box.toggled.connect(self._refresh_dirty_state)

    def _open_advanced_dialog(self):
        self._update_accessible_layout_constraints()
        self.advanced_dialog.show()
        self._resize_advanced_dialog()
        self.advanced_dialog.raise_()
        self.advanced_dialog.activateWindow()
        QtCore.QTimer.singleShot(0, self.advanced_mode_box.setFocus)

    def _update_level_mode(self, index):
        numbering_mode = index == 1
        self.sub_dir_group.setVisible(numbering_mode)
        self.sub_dir_group.setEnabled(numbering_mode)
        self._update_accessible_layout_constraints()
        if self.advanced_dialog.isVisible():
            QtCore.QTimer.singleShot(0, self._resize_advanced_dialog)
        self._validate_regex_settings()
        self._update_action_availability()

    def _resize_advanced_dialog(self):
        self.advanced_dialog.adjustSize()
        screen = self.advanced_dialog.screen() or self.screen()
        available = screen.availableGeometry().size()
        maximum = QtCore.QSize(
            max(320, available.width() - 48),
            max(240, available.height() - 72),
        )
        target = self.advanced_dialog.size().boundedTo(maximum)
        target = target.expandedTo(self.advanced_dialog.minimumSize())
        self.advanced_dialog.resize(target)

    def _update_output_path(self):
        source = self.pdf_path.strip()
        if source:
            self._document_display_name = os.path.basename(source)
            self._refresh_document_name()
            self.document_name_label.setToolTip(source)
        else:
            self.output_path_edit.clear()
            self._document_display_name = self._t("no_document")
            self._refresh_document_name()
            self.document_name_label.setToolTip("")
        self._refresh_dirty_state()
        self._update_action_availability()

    @staticmethod
    def _canonical_source_path(path):
        if not str(path).strip():
            return ""
        return os.path.normcase(
            os.path.abspath(os.path.expanduser(str(path).strip()))
        )

    def _generation_signature(
        self,
        pdf_path=None,
        index_dict=None,
        keep_existing=None,
    ):
        source = self._canonical_source_path(
            self.pdf_path if pdf_path is None else pdf_path
        )
        if not source:
            return None
        if index_dict is None:
            index_dict = self.tree_to_dict()
        if not index_dict:
            return None
        records = []
        try:
            for key in sorted(index_dict):
                record = index_dict[key]
                records.append(
                    (
                        str(record.get("title", "")),
                        int(record.get("real_num", 1)),
                        record.get("parent"),
                    )
                )
        except (TypeError, ValueError):
            return None
        if keep_existing is None:
            keep_existing = self.keep_exist_dir
        return (source, bool(keep_existing), tuple(records))

    def _current_generation_signature(self):
        return self._generation_signature()

    def _has_current_generated_result(self):
        return bool(
            self._last_generated_path
            and self._last_generated_signature is not None
            and os.path.isfile(self._last_generated_path)
            and self._current_generation_signature()
            == self._last_generated_signature
        )

    def _clear_generated_result(self, clear_feedback=False):
        self._last_generated_path = ""
        self._last_generated_signature = None
        if clear_feedback:
            self._status_timer.stop()
            self._status_override_active = False

    def _sync_action_surface(self):
        task_kind = (self._task_context or {}).get("kind")
        if self._has_active_task() and task_kind == "write":
            output = (self._task_context or {}).get("output_path")
            if output:
                self.output_path_edit.setText(output)
            self._primary_action_mode = "generate"
            return

        has_result = self._has_current_generated_result()
        self._primary_action_mode = "open" if has_result else "generate"
        if has_result:
            self.output_path_edit.setText(self._last_generated_path)
            self.export_button.setText(self._t("open_generated"))
            self.export_button.setAccessibleDescription(
                self._t("open_generated_description")
            )
        else:
            source = self.pdf_path.strip()
            if source:
                self.output_path_edit.setText(
                    self._next_available_output_path(source)
                )
            else:
                self.output_path_edit.clear()
            self.export_button.setText(
                "Generate bookmarked PDF"
                if self._language == "en"
                else "生成带书签的 PDF"
            )
            self.export_button.setAccessibleDescription(
                "Generate a new PDF from the editable bookmark preview"
                if self._language == "en"
                else "根据可编辑的书签预览生成一份新 PDF"
            )

    def _run_primary_action(self):
        if self._primary_action_mode == "open":
            self._open_generated_pdf()
        else:
            self.write_tree_to_pdf()

    def _open_generated_pdf(self):
        path = self._last_generated_path
        if not path or not os.path.isfile(path):
            self._clear_generated_result()
            self._sync_action_surface()
            self.show_status(self._t("generated_missing"), 5000)
            return False
        url = QtCore.QUrl.fromLocalFile(path)
        if not QtGui.QDesktopServices.openUrl(url):
            self.show_status(self._t("generated_open_failed"), 5000)
            return False
        return True

    @staticmethod
    def _next_available_output_path(source):
        stem, suffix = os.path.splitext(source)
        candidate = stem + "_new" + suffix
        sequence = 2
        while os.path.lexists(candidate):
            candidate = "{}_new_{}{}".format(stem, sequence, suffix)
            sequence += 1
        return candidate

    def _refresh_document_name(self):
        available_width = max(self.document_name_label.width(), 240)
        self.document_name_label.setText(
            self.document_name_label.fontMetrics().elidedText(
                self._document_display_name,
                QtCore.Qt.ElideMiddle,
                available_width,
            )
        )

    def _update_action_availability(self):
        source_path = Path(self.pdf_path.strip()) if self.pdf_path.strip() else None
        has_pdf = bool(
            source_path
            and source_path.is_file()
            and source_path.suffix.lower() == ".pdf"
        )
        validation_error = self._validate_preview_tree()
        has_required_input = bool(
            has_pdf
            and self.dir_text.strip()
            and self.dir_tree_widget.topLevelItemCount()
            and not validation_error
            and self.offset_edit.hasAcceptableInput()
        )
        task_running = self._has_active_task()
        self._escape_shortcut.setEnabled(task_running)
        task_kind = (self._task_context or {}).get("kind")
        write_running = task_running and task_kind == "write"

        self.pdf_path_edit.setEnabled(not task_running)
        self.open_button.setEnabled(not task_running)
        for control in (
            self.dir_text_edit,
            self.dir_tree_widget,
            self.level_mode_box,
            self.offset_edit,
            self.advanced_button,
        ):
            control.setEnabled(not write_running)

        self.export_button.setEnabled(has_required_input and not task_running)
        self.export_button.setVisible(not task_running)
        self.auto_toc_button.setEnabled(has_pdf and not task_running)
        self.auto_offset_button.setEnabled(has_required_input and not task_running)
        self.cancel_button.setVisible(task_running)
        keep_visible = bool(
            self._source_has_bookmarks
            and not self._draft_imported_from_source
        )
        self.keep_exist_dir_box.setVisible(keep_visible)
        self.keep_exist_dir_action.setVisible(keep_visible)
        self.keep_exist_dir_box.setEnabled(keep_visible and not write_running)
        self._sync_action_surface()

        if not has_pdf:
            export_tip = self._t("export_needs_pdf")
        elif validation_error:
            export_tip = self._t(
                "export_needs_valid_preview",
                message=validation_error,
            )
        elif not self.dir_text.strip() or not self.dir_tree_widget.topLevelItemCount():
            export_tip = self._t("export_needs_toc")
        else:
            export_tip = self.export_button.accessibleDescription()
        self.export_button.setToolTip(export_tip)
        self.auto_toc_button.setToolTip(
            "" if has_pdf else self._t("toc_needs_pdf")
        )
        self.auto_offset_button.setToolTip(
            "" if has_required_input else self._t("offset_needs_input")
        )
        self._refresh_action_status()

    def _has_active_task(self):
        """Cover the short start/finish gaps around the QThread lifecycle."""
        return self._worker_busy or bool(
            self._worker_thread and self._worker_thread.isRunning()
        )

    def _has_active_update(self):
        return bool(self._update_thread and self._update_thread.isRunning())

    def _resume_pending_close(self):
        """Retry a deferred close only after every background thread is idle."""
        if (
            self._close_requested
            and not self._close_retry_scheduled
            and not self._has_active_task()
            and not self._has_active_update()
        ):
            self._close_retry_scheduled = True
            QtCore.QTimer.singleShot(0, self._retry_pending_close)

    def _retry_pending_close(self):
        self._close_retry_scheduled = False
        if (
            self._close_requested
            and not self._has_active_task()
            and not self._has_active_update()
        ):
            self.close()

    def _validate_preview_tree(self):
        if self._regex_validation_error:
            return self._regex_validation_error
        row = 0
        for item in self.dir_tree_widget.all_items:
            row += 1
            if not item.text(0).strip():
                return self._t("empty_title", row=row)
            for column in (1, 2):
                try:
                    int(item.text(column))
                except (TypeError, ValueError):
                    return self._t("invalid_preview_page", row=row)
        return self._preview_validation_error

    def _preview_item_count(self):
        return sum(1 for _item in self.dir_tree_widget.all_items)

    def _set_action(self):
        self.home_page_action.triggered.connect(self._open_home_page)
        self.help_action.triggered.connect(self._open_help_page)
        self.update_action.triggered.connect(self._open_update_page)
        self.english_action.triggered.connect(self.to_english)
        self.chinese_action.triggered.connect(self.to_chinese)

    def _t(self, key, **values):
        text = self._MESSAGES[self._language][key]
        return text.format(**values) if values else text

    def _apply_language(self):
        english = self._language == "en"
        static_text = {
            self.page_title_label: (
                "PDF Bookmark Editor",
                "PDF 书签编辑器",
            ),
            self.page_subtitle_label: (
                "Edit the table of contents, verify page mapping, and export a new PDF.",
                "编辑目录、确认页码映射，然后安全生成一份新 PDF。",
            ),
            self.pdf_path_label: ("PDF file", "PDF 文件"),
            self.open_button: ("Select PDF…", "选择 PDF…"),
            self.dir_text_label: ("TOC text", "目录文本"),
            self.editor_hint_label: (
                "Enter a title and printed page on each line; recognition results stay editable.",
                "每行输入标题和标注页码；可直接编辑识别结果。",
            ),
            self.auto_toc_button: (
                "Recognize TOC",
                "从 PDF 识别目录",
            ),
            self.preview_label: ("Bookmark preview", "书签预览"),
            self.preview_hint_label: (
                "Double-click or press F2 to edit; drag to reorder or nest; Delete removes.",
                "双击或按 F2 编辑；拖动调整顺序与层级；Delete 删除。",
            ),
            self.level_mode_label: ("Hierarchy", "层级识别"),
            self.offset_label: ("Page offset", "页差"),
            self.auto_offset_button: (
                "Detect",
                "识别页差",
            ),
            self.advanced_button: (
                "Recognition rules…",
                "识别设置…",
            ),
            self.advanced_mode_label: (
                "Hierarchy detection",
                "层级识别方式",
            ),
            self.sub_dir_group: (
                "Numbering rules (regular expressions)",
                "编号规则（正则表达式）",
            ),
            self.level0_box: ("Level 1", "首层"),
            self.level1_box: ("Level 2", "二层"),
            self.level2_box: ("Level 3", "三层"),
            self.level3_box: ("Level 4", "四层"),
            self.level4_box: ("Level 5", "五层"),
            self.level5_box: ("Level 6", "六层"),
            self.unknown_level_label: (
                "Unmatched lines become",
                "未识别行作为",
            ),
            self.fix_non_seq_box: (
                "Reuse the last valid page for missing or reversed pages",
                "沿用上一有效页码，修复乱序或缺失页码",
            ),
            self.read_exist_dir_box: (
                "Ask before importing existing bookmarks",
                "打开 PDF 时询问是否导入已有书签",
            ),
            self.keep_exist_dir_box: (
                "Keep source PDF bookmarks",
                "保留源 PDF 书签",
            ),
            self.output_label: ("Output", "输出"),
            self.cancel_button: ("Cancel task", "取消任务"),
            self.export_button: (
                "Generate bookmarked PDF",
                "生成带书签的 PDF",
            ),
            self.help_menu: ("Help", "帮助"),
            self.language_menu: ("Language", "语言"),
            self.home_page_action: ("Project home", "项目主页"),
            self.help_action: ("User guide", "使用说明"),
            self.update_action: ("Check for updates", "检查更新"),
        }
        for target, variants in static_text.items():
            translated = variants[0] if english else variants[1]
            if hasattr(target, "setText"):
                target.setText(translated)
            else:
                target.setTitle(translated)

        self.advanced_dialog.setWindowTitle(self._t("advanced_title"))
        close_button = self.advanced_button_box.button(
            QtWidgets.QDialogButtonBox.Close
        )
        if close_button:
            close_button.setText("Close" if english else "关闭")
        self.pdf_path_edit.setPlaceholderText(
            "Choose the PDF to bookmark"
            if english
            else "选择要添加书签的 PDF"
        )
        self.dir_text_edit.setPlaceholderText(
            "Example:\nChapter 1  1\n  1.1 Installation  3"
            if english
            else "示例：\n第 1 章 入门  1\n  1.1 安装  3"
        )
        self.output_path_edit.setPlaceholderText(
            "The output location appears after selecting a PDF"
            if english
            else "选择 PDF 后显示输出位置"
        )
        self.level_mode_box.setItemText(
            0, "Indentation" if english else "按缩进识别层级"
        )
        self.level_mode_box.setItemText(
            1, "Numbering rules" if english else "按编号规则识别层级"
        )
        self.advanced_mode_box.setItemText(
            0, "Indentation" if english else "按缩进识别层级"
        )
        self.advanced_mode_box.setItemText(
            1, "Numbering rules" if english else "按编号规则识别层级"
        )
        for index in range(self.unknown_level_box.count()):
            self.unknown_level_box.setItemText(
                index,
                "Level {}".format(index + 1)
                if english
                else ("首层", "二层", "三层", "四层", "五层", "六层")[index],
            )
        self._update_tree_headers(
            compact=self.app.font().pointSizeF() >= 18
        )
        self._update_output_path()
        self.pdf_path_edit.setAccessibleName(
            "PDF file path" if english else "PDF 文件路径"
        )
        self.dir_text_edit.setAccessibleName(
            "Editable TOC text" if english else "可编辑目录文本"
        )
        self.dir_tree_widget.setAccessibleName(
            "Bookmark hierarchy preview" if english else "书签层级预览"
        )
        self.output_path_edit.setAccessibleName(
            "Output PDF path" if english else "输出 PDF 路径"
        )
        self.auto_toc_button.setAccessibleName(
            "Recognize TOC from PDF" if english else "从 PDF 识别目录"
        )
        self.auto_offset_button.setAccessibleName(
            "Detect page offset" if english else "识别页差"
        )
        self.advanced_button.setAccessibleName(
            "Open recognition rule settings"
            if english
            else "打开识别规则设置"
        )
        self.page_title_label.setAccessibleName(
            "PDF Bookmark Editor" if english else "PDF 书签编辑器"
        )
        self.export_button.setAccessibleDescription(
            "Generate a new PDF from the editable bookmark preview"
            if english
            else "根据可编辑的书签预览生成一份新 PDF"
        )
        self.cancel_button.setAccessibleDescription(
            "Cancel the running background task"
            if english
            else "取消当前正在运行的后台任务"
        )
        self.action_status_label.setAccessibleName(
            "Task status" if english else "任务状态"
        )
        self.offset_edit.setToolTip(
            "PDF page minus printed page"
            if english
            else "PDF 页码减去书上标注页码"
        )
        self.keep_exist_dir_box.setAccessibleDescription(
            self._t("keep_source_description")
        )
        self.keep_exist_dir_box.setToolTip(
            self._t(
                "imported_keep_disabled"
                if self._draft_imported_from_source
                else "keep_source_description"
            )
        )
        self.dir_tree_widget.set_delete_action_label(
            "Delete" if english else "删除"
        )
        for index, editor in enumerate(self._regex_editors):
            level_name = (
                "Level {}".format(index + 1)
                if english
                else ("首层", "二层", "三层", "四层", "五层", "六层")[index]
            )
            editor.setAccessibleName(
                "{} regular expression".format(level_name)
                if english
                else "{}正则表达式".format(level_name)
            )
            editor.setAccessibleDescription(
                "Pattern used to identify {} bookmarks".format(
                    level_name.lower()
                )
                if english
                else "用于识别{}书签的规则".format(level_name)
            )
            editor.setToolTip(editor.accessibleDescription())
        self._refresh_preview_hint()
        self._validate_regex_settings()
        self._update_action_availability()
        self._update_preview_empty_state()
        QtCore.QTimer.singleShot(0, self._reflow_controls)

    def _update_tree_headers(self, compact=False):
        if self._language == "en":
            full_headers = ("Bookmark title", "Printed page", "PDF page")
            headers = ("Title", "Print", "PDF") if compact else full_headers
        else:
            full_headers = ("书签标题", "标注页码", "PDF 页码")
            headers = ("标题", "标页", "PDF 页") if compact else full_headers
        header_item = self.dir_tree_widget.headerItem()
        for index, (header, full_header) in enumerate(
            zip(headers, full_headers)
        ):
            header_item.setText(index, header)
            header_item.setToolTip(index, full_header)

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
        if self._has_active_update():
            self.show_status(self._t("checking_update"))
            return
        url = CONFIG.RELEASE_PAGE_URL
        self.update_action.setEnabled(False)
        self.show_status(self._t("checking_update"))
        self._update_thread = QtCore.QThread(self)
        self._update_worker = UpdateCheckWorker(url, self.version)
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._update_check_finished)
        self._update_worker.failed.connect(self._update_check_failed)
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_worker.failed.connect(self._update_thread.quit)
        self._update_worker.finished.connect(self._update_worker.deleteLater)
        self._update_worker.failed.connect(self._update_worker.deleteLater)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.finished.connect(self._update_check_complete)
        self._update_thread.start()

    def _update_check_finished(self, result):
        if self._close_requested:
            return
        if result == "update":
            self.show_status(self._t("find_new_version"), 3000)
            webbrowser.open(CONFIG.RELEASE_PAGE_URL, new=1)
        else:
            self.show_status(self._t("no_update"), 3000)
            self.alert_msg(self._t("no_update"))

    def _update_check_failed(self, _message):
        if self._close_requested:
            return
        self.show_status(self._t("check_update_failed"), 5000)
        self.alert_msg(self._t("check_update_failed"), level="warn")

    def _update_check_complete(self):
        self._update_worker = None
        self._update_thread = None
        self.update_action.setEnabled(True)
        self._resume_pending_close()

    def show_status(self, msg, timeout=10 * 3600 * 1000):
        """Show an operation message next to the action it explains."""
        self._status_override_active = True
        self._set_action_status(msg, self._status_kind_for_message(msg))
        if 0 < timeout < 10 * 3600 * 1000:
            self._status_timer.start(timeout)
        else:
            self._status_timer.stop()
        return self.statusbar.showMessage(msg, timeout)

    def _status_timeout(self):
        self._status_override_active = False
        self._refresh_action_status()

    def _status_kind_for_message(self, message):
        lowered = message.lower()
        if any(
            marker in lowered
            for marker in (
                "失败",
                "无效",
                "移动或删除",
                "无法打开",
                "could not",
                "failed",
                "error",
                "moved or removed",
            )
        ):
            return "error"
        if any(
            marker in lowered
            for marker in ("已生成", "完成", "generated", "ready")
        ):
            return "success"
        if any(
            marker in lowered
            for marker in ("正在", "cancelling", "detecting", "recognizing", "generating")
        ):
            return "working"
        return "normal"

    def _set_action_status(self, message, kind="normal"):
        self._action_status_message = str(message)
        self.action_status_label.setProperty("statusKind", kind)
        self.action_status_label.style().unpolish(self.action_status_label)
        self.action_status_label.style().polish(self.action_status_label)
        self._render_action_status()
        QtCore.QTimer.singleShot(0, self._render_action_status)

    def _render_action_status(self):
        if not hasattr(self, "action_status_label"):
            return
        message = self._action_status_message
        metrics = self.action_status_label.fontMetrics()
        available_width = self.action_status_label.contentsRect().width()
        if available_width < 120 and hasattr(self, "action_frame"):
            available_width = max(self.action_frame.width() - 28, 120)
        rendered_lines = [
            metrics.elidedText(
                line,
                QtCore.Qt.ElideMiddle,
                available_width,
            )
            for line in message.splitlines() or [""]
        ]
        rendered = "\n".join(rendered_lines)
        self.action_status_label.setText(rendered)
        self.action_status_label.setToolTip(message)
        self.action_status_label.setAccessibleDescription(
            message.replace("\n", " ")
        )
        self.action_status_label.setMinimumHeight(
            metrics.lineSpacing() * max(len(rendered_lines), 1) + 8
        )
        self.action_status_label.updateGeometry()
        self.action_status_label.update()

    def _refresh_action_status(self):
        if self._status_override_active and self._status_timer.isActive():
            return
        if not self._has_active_task():
            self._status_override_active = False
        task_kind = (self._task_context or {}).get("kind")
        if self._has_active_task():
            if task_kind == "write":
                source = os.path.basename(self.pdf_path)
                output = os.path.basename(self.output_path_edit.text())
                self._set_action_status(
                    self._t(
                        "generated_task",
                        source=source,
                        output=output,
                    ),
                    "working",
                )
            return
        validation_error = self._validate_preview_tree()
        source_path = Path(self.pdf_path.strip()) if self.pdf_path.strip() else None
        has_pdf = bool(
            source_path
            and source_path.is_file()
            and source_path.suffix.lower() == ".pdf"
        )
        if validation_error:
            self._set_action_status(validation_error, "error")
        elif self._has_current_generated_result():
            self._set_action_status(
                self._t("generated_ready"),
                "success",
            )
        elif self._is_dirty():
            self._set_action_status(self._t("dirty"), "normal")
        elif not has_pdf:
            self._set_action_status(self._t("ready_select_pdf"), "normal")
        elif not self.dir_text.strip():
            self._set_action_status(self._t("ready_enter_toc"), "normal")
        else:
            self._set_action_status(
                self._t(
                    "ready_generate",
                    count=self._preview_item_count(),
                ),
                "success",
            )

    def alert_msg(self, msg, level="info", ok_action=None):
        box = QMessageBox(self)
        if level == "info":
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle(self._t("information"))
        else:
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle(self._t("warning"))
        if ok_action:
            box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            box.buttonClicked.connect(ok_action)
        box.setText(msg)
        box.exec()

    def to_english(self):
        self._language = "en"
        self._apply_language()

    def to_chinese(self):
        self._language = "zh"
        self._apply_language()

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
        return self.level_mode_box.currentIndex() == 0

    @property
    def fix_non_seq(self):
        return self.fix_non_seq_box.isChecked()

    @property
    def keep_exist_dir(self):
        return self.keep_exist_dir_box.isChecked()

    @property
    def read_exist_dir(self):
        return self.read_exist_dir_box.isChecked()

    def eventFilter(self, watched, event):
        if (
            watched in getattr(self, "_advanced_focus_chain", ())
            and event.type() == QtCore.QEvent.KeyPress
            and event.key() in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab)
            and not event.modifiers() & QtCore.Qt.ControlModifier
        ):
            backwards = bool(
                event.modifiers() & QtCore.Qt.ShiftModifier
                or event.key() == QtCore.Qt.Key_Backtab
            )
            if self._focus_advanced_relative(watched, not backwards):
                return True
        if (
            watched is self.dir_tree_widget.viewport()
            and event.type() == QtCore.QEvent.Resize
        ):
            QtCore.QTimer.singleShot(0, self._update_preview_empty_state)
        if (
            watched is self.dir_text_edit
            and event.type() == QtCore.QEvent.KeyPress
        ):
            if (
                event.key() in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab)
                and event.modifiers() & QtCore.Qt.ControlModifier
            ):
                backwards = bool(
                    event.modifiers() & QtCore.Qt.ShiftModifier
                    or event.key() == QtCore.Qt.Key_Backtab
                )
                self.focusNextPrevChild(not backwards)
                return True
        return super(Main, self).eventFilter(watched, event)

    def _focus_advanced_relative(self, current, forwards):
        controls = getattr(self, "_advanced_focus_chain", ())
        if current not in controls:
            return False
        step = 1 if forwards else -1
        start = controls.index(current)
        for distance in range(1, len(controls) + 1):
            candidate = controls[(start + step * distance) % len(controls)]
            if (
                candidate.isEnabled()
                and candidate.isVisible()
                and candidate.focusPolicy() & QtCore.Qt.TabFocus
            ):
                candidate.setFocus(QtCore.Qt.TabFocusReason)
                return True
        return False

    def _tree_snapshot(self):
        snapshot = []

        def append_item(item, depth):
            snapshot.append(
                (
                    depth,
                    item.text(0),
                    item.text(1),
                    item.text(2),
                )
            )
            for index in range(item.childCount()):
                append_item(item.child(index), depth + 1)

        for index in range(self.dir_tree_widget.topLevelItemCount()):
            append_item(self.dir_tree_widget.topLevelItem(index), 0)
        return tuple(snapshot)

    def _current_draft_signature(self):
        tree = self._tree_snapshot()
        if not self.dir_text.strip() and not tree:
            return None
        numbering_mode = self.level_mode_box.currentIndex() == 1
        regex_settings = (
            tuple(
                (box.isChecked(), editor.text())
                for box, editor in zip(
                    self._regex_boxes,
                    self._regex_editors,
                )
            )
            if numbering_mode
            else None
        )
        return (
            self.pdf_path.strip(),
            self.dir_text,
            self.offset_edit.text(),
            self.level_mode_box.currentIndex(),
            regex_settings,
            self.unknown_level_box.currentIndex() if numbering_mode else None,
            self.fix_non_seq_box.isChecked(),
            self.keep_exist_dir_box.isChecked(),
            tree,
        )

    def _is_dirty(self):
        return self._current_draft_signature() != self._dirty_baseline

    def _mark_clean(self):
        self._dirty_baseline = self._current_draft_signature()
        self.setWindowModified(False)
        self._refresh_action_status()

    def _refresh_dirty_state(self):
        if not hasattr(self, "_dirty_baseline"):
            return
        self.setWindowModified(self._is_dirty())
        self._sync_action_surface()
        self._refresh_action_status()

    def _on_preview_changed(self):
        if self._rebuilding_tree:
            return
        self._preview_manually_adjusted = True
        self._preview_validation_error = ""
        self._refresh_preview_hint()
        self._update_preview_empty_state()
        self._refresh_dirty_state()
        self._update_action_availability()

    def _refresh_preview_hint(self):
        if self._compact_shell:
            key = (
                "preview_manual_compact_hint"
                if self._preview_manually_adjusted
                else "preview_compact_hint"
            )
        else:
            key = (
                "preview_manual_hint"
                if self._preview_manually_adjusted
                else "preview_edit_hint"
            )
        self.preview_hint_label.setText(self._t(key))

    def _update_preview_empty_state(self):
        item_count = sum(1 for _ in getattr(self.dir_tree_widget, "all_items", []))
        if item_count > 0:
            self.preview_label.setText(
                self._t("preview_title_with_count", count=item_count)
            )
        else:
            self.preview_label.setText(self._t("preview_title"))
        is_empty = item_count == 0
        self.preview_empty_label.setText(self._t("preview_empty"))
        self.preview_empty_label.setGeometry(
            self.dir_tree_widget.viewport().rect()
        )
        has_room = (
            self.dir_tree_widget.viewport().height()
            >= self.preview_empty_label.fontMetrics().height() + 16
        )
        self.preview_empty_label.setVisible(is_empty and has_room)
        if is_empty and has_room:
            self.preview_empty_label.raise_()

    def _validate_regex_settings(self):
        if not hasattr(self, "_regex_editors"):
            return True
        self._regex_validation_error = ""
        for index, (box, editor) in enumerate(
            zip(self._regex_boxes, self._regex_editors)
        ):
            invalid = False
            if self.level_mode_box.currentIndex() == 1 and box.isChecked():
                try:
                    re.compile(editor.text())
                except re.error as exc:
                    invalid = True
                    level_name = (
                        "Level {}".format(index + 1)
                        if self._language == "en"
                        else ("首层", "二层", "三层", "四层", "五层", "六层")[
                            index
                        ]
                    )
                    self._regex_validation_error = self._t(
                        "invalid_regex",
                        level=level_name,
                        message=str(exc),
                    )
            editor.setProperty("invalid", invalid)
            editor.style().unpolish(editor)
            editor.style().polish(editor)
        self.regex_error_label.setText(self._regex_validation_error)
        self.regex_error_label.setVisible(bool(self._regex_validation_error))
        return not self._regex_validation_error

    def _build_choice_box(
        self,
        title_key,
        message_key,
        choices,
        default_choice,
        escape_choice,
        icon=QMessageBox.Question,
    ):
        """Build a choice dialog whose buttons name their data effect."""
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(self._t(title_key))
        box.setText(self._t(message_key))
        buttons = {}
        for choice, label_key, role in choices:
            buttons[choice] = box.addButton(self._t(label_key), role)
        box.setDefaultButton(buttons[default_choice])
        box.setEscapeButton(buttons[escape_choice])
        return box, buttons

    def _prompt_import_bookmarks(self, has_draft):
        accept_label = "import_replace_action" if has_draft else "import_action"
        safe_label = "keep_draft_action" if has_draft else "skip_import_action"
        default_choice = "keep" if has_draft else "import"
        box, buttons = self._build_choice_box(
            "import_title",
            "replace_draft" if has_draft else "import_draft",
            (
                ("import", accept_label, QMessageBox.AcceptRole),
                ("keep", safe_label, QMessageBox.RejectRole),
            ),
            default_choice=default_choice,
            escape_choice="keep",
        )
        box.exec()
        return box.clickedButton() is buttons["import"]

    def _prompt_document_switch(self):
        box, buttons = self._build_choice_box(
            "switch_draft_title",
            "switch_draft",
            (
                ("keep", "carry_draft_action", QMessageBox.AcceptRole),
                ("clear", "clear_draft_action", QMessageBox.DestructiveRole),
                ("cancel", "cancel_action", QMessageBox.RejectRole),
            ),
            default_choice="cancel",
            escape_choice="cancel",
        )
        box.exec()
        clicked = box.clickedButton()
        for choice, button in buttons.items():
            if clicked is button:
                return choice
        return "cancel"

    def _reset_draft(self):
        self._preview_manually_adjusted = False
        self._draft_imported_from_source = False
        self.dir_text_edit.clear()
        self.offset_edit.setText("0")
        self.keep_exist_dir_box.setChecked(False)

    def _activate_document(self, filename):
        candidate = os.path.abspath(os.path.expanduser(filename))
        source_path = Path(candidate)
        try:
            if (
                not source_path.is_file()
                or source_path.suffix.lower() != ".pdf"
            ):
                raise ValueError(self._t("select_pdf_first"))
            bookmarks = get_bookmarks_strict(candidate)
        except Exception as exc:
            self.alert_msg(
                self._t("invalid_pdf", message=str(exc)),
                level="warn",
            )
            return False

        switching = bool(
            self._active_pdf_path
            and os.path.abspath(self._active_pdf_path) != candidate
        )
        has_draft = bool(
            self.dir_text.strip()
            or self.dir_tree_widget.topLevelItemCount()
        )
        switch_choice = "keep"
        if switching and has_draft:
            switch_choice = self._prompt_document_switch()
            if switch_choice == "cancel":
                return False
            if switch_choice == "clear":
                self._reset_draft()
                has_draft = False

        if switching or not self._active_pdf_path:
            self._clear_generated_result(clear_feedback=True)
        self._active_pdf_path = candidate
        self.pdf_path_edit.setText(candidate)
        self._source_has_bookmarks = bool(bookmarks)
        self._draft_imported_from_source = False
        self.default_folder = os.path.dirname(candidate)

        imported = False
        if bookmarks and self.read_exist_dir:
            if self._prompt_import_bookmarks(has_draft):
                bookmark_text = clean_clipboard_control_chars(
                    "\n".join(bookmarks)
                )
                self.dir_text_edit.setPlainText(bookmark_text)
                self.level_mode_box.setCurrentIndex(0)
                self.keep_exist_dir_box.setChecked(False)
                self._draft_imported_from_source = True
                imported = True

        if switch_choice == "clear" or imported or not has_draft:
            self._mark_clean()
        else:
            self._refresh_dirty_state()
        self._update_action_availability()
        return True

    def _commit_typed_pdf_path(self):
        if self._close_requested or self._allow_close_once:
            return
        candidate = self.pdf_path.strip()
        if not candidate:
            self._clear_generated_result(clear_feedback=True)
            self._active_pdf_path = ""
            self._source_has_bookmarks = False
            self._sync_action_surface()
            self._update_action_availability()
            return
        if self._active_pdf_path and os.path.abspath(candidate) == os.path.abspath(
            self._active_pdf_path
        ):
            return
        previous = self._active_pdf_path
        if not self._activate_document(candidate) and previous:
            self.pdf_path_edit.setText(previous)

    def open_file_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self._t("select_pdf"),
            self.default_folder,
            "PDF (*.pdf)",
        )
        if not filename:
            return
        self._activate_document(filename)

    def tree_to_dict(self):
        return self.dir_tree_widget.to_dict()

    def make_dir_tree(self):
        if not hasattr(self, "preview_empty_label"):
            return
        had_manual_adjustments = self._preview_manually_adjusted
        self._rebuilding_tree = True
        self._preview_manually_adjusted = False
        self._preview_validation_error = ""
        try:
            self.dir_tree_widget.clear()
            if not self._validate_regex_settings():
                return
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
                if not str(con.get("title", "")).strip() and not self._preview_validation_error:
                    self._preview_validation_error = self._t(
                        "empty_title",
                        row=i + 1,
                    )
                if "parent" in con:
                    children[i] = con
                else:
                    tree_item = self._tree_item_from_record(con)
                    self.dir_tree_widget.insertTopLevelItem(
                        top_idx,
                        tree_item,
                    )
                    inserted_items[i] = tree_item
                    top_idx += 1
            last_children_count = len(children) + 1
            while children and len(children) < last_children_count:
                last_children_count = len(children)
                for key in list(children):
                    con = children[key]
                    parent_index = con["parent"]
                    if parent_index in inserted_items:
                        tree_item = self._tree_item_from_record(con)
                        inserted_items[parent_index].addChild(tree_item)
                        children.pop(key)
                        inserted_items[key] = tree_item
            for item in inserted_items.values():
                item.setExpanded(True)
        finally:
            self._rebuilding_tree = False
            self._refresh_preview_hint()
            self._update_preview_empty_state()
            self._refresh_dirty_state()
            self._update_action_availability()
        if had_manual_adjustments:
            self.show_status(self._t("preview_reset"), 4000)

    def _tree_item_from_record(self, record):
        item = QtWidgets.QTreeWidgetItem(
            [
                str(record.get("title", "")),
                str(record.get("num", 1)),
                str(record.get("real_num", 1)),
            ]
        )
        if not item.text(0).strip():
            item.setForeground(0, QtGui.QBrush(QtGui.QColor("#b3261e")))
        return item

    def fill_offset(self):
        if self._has_active_task():
            self.alert_msg(self._t("task_running"), level="warn")
            return
        source_path = Path(self.pdf_path.strip()) if self.pdf_path.strip() else None
        if not source_path or not source_path.is_file() or source_path.suffix.lower() != ".pdf":
            self.alert_msg(self._t("select_pdf_first"), level="warn")
            return
        if not self.dir_text.strip():
            self.alert_msg(self._t("input_toc_first"), level="warn")
            return

        self._task_focus_origin = self.focusWidget()
        self.auto_offset_button.setEnabled(False)
        self.show_status(self._t("offset_working"))
        self._task_context = {
            "kind": "offset",
            "pdf_path": self.pdf_path,
            "dir_text": self.dir_text,
        }
        self._worker_busy = True

        self._worker_thread = QtCore.QThread(self)
        self._worker = PageOffsetWorker(self.pdf_path, self.dir_text)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._offset_inferred)
        self._worker.failed.connect(self._offset_failed)
        self._worker.cancelled.connect(self._task_cancelled)
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
        self._update_action_availability()
        QtCore.QTimer.singleShot(0, self.cancel_button.setFocus)

    def fill_toc_text(self):
        if self._has_active_task():
            self.alert_msg(self._t("task_running"), level="warn")
            return
        source_path = Path(self.pdf_path.strip()) if self.pdf_path.strip() else None
        if not source_path or not source_path.is_file() or source_path.suffix.lower() != ".pdf":
            self.alert_msg(self._t("select_pdf_first"), level="warn")
            return

        self._task_focus_origin = self.focusWidget()
        self.auto_toc_button.setEnabled(False)
        self.show_status(self._t("toc_working"))
        self._task_context = {
            "kind": "toc",
            "pdf_path": self.pdf_path,
            "dir_text": self.dir_text,
        }
        self._worker_busy = True

        self._worker_thread = QtCore.QThread(self)
        self._worker = TocTextWorker(self.pdf_path)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._toc_text_inferred)
        self._worker.failed.connect(self._toc_text_failed)
        self._worker.cancelled.connect(self._task_cancelled)
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
        self._update_action_availability()
        QtCore.QTimer.singleShot(0, self.cancel_button.setFocus)

    def _offset_inferred(self, offset):
        if self._close_requested:
            return
        context = self._task_context or {}
        if (
            context.get("kind") != "offset"
            or context.get("pdf_path") != self.pdf_path
            or context.get("dir_text") != self.dir_text
        ):
            self.show_status(
                self._t("offset_discarded"),
                5000,
            )
            return
        if offset is None:
            self.show_status(self._t("offset_failed"), 5000)
            self.alert_msg(self._t("offset_empty"), level="warn")
            return
        display_offset = offset
        self.offset_edit.setText(str(display_offset))
        self.show_status(self._t("offset_done", value=display_offset), 3000)

    def _offset_failed(self, message):
        if self._close_requested:
            return
        self.show_status(self._t("offset_failed"), 5000)
        self.alert_msg(
            self._t(
                "offset_error",
                message=self._friendly_recognition_error(message),
            ),
            level="warn",
        )

    def _offset_progress(self, current, total):
        self.show_status(
            self._t("offset_progress", current=current, total=total)
        )

    def _offset_worker_finished(self):
        self.auto_offset_button.setEnabled(True)
        self._background_task_finished()

    def _toc_text_inferred(self, toc_text):
        if self._close_requested:
            return
        context = self._task_context or {}
        if (
            context.get("kind") != "toc"
            or context.get("pdf_path") != self.pdf_path
            or context.get("dir_text") != self.dir_text
        ):
            self.show_status(
                self._t("toc_discarded"),
                5000,
            )
            return
        if not toc_text:
            self.show_status(self._t("toc_failed"), 5000)
            self.alert_msg(self._t("toc_empty"), level="warn")
            return
        self.dir_text_edit.setPlainText(toc_text)
        self.show_status(self._t("toc_done"), 3000)

    def _toc_text_failed(self, message):
        if self._close_requested:
            return
        self.show_status(self._t("toc_failed"), 5000)
        self.alert_msg(
            self._t(
                "toc_error",
                message=self._friendly_recognition_error(message),
            ),
            level="warn",
        )

    def _friendly_recognition_error(self, message):
        lowered = str(message).lower()
        if any(
            marker in lowered
            for marker in (
                "ocr fallback requires",
                "ocr requires",
                "paddleocr backend requires",
                "tesseract",
                "pymupdf",
            )
        ):
            return self._t("ocr_unavailable")
        return str(message)

    def _toc_progress(self, current, total):
        self.show_status(
            self._t("toc_progress", current=current, total=total)
        )

    def _toc_worker_finished(self):
        self.auto_toc_button.setEnabled(True)
        self._background_task_finished()

    def _task_cancelled(self):
        self.show_status(self._t("task_cancelled"), 3000)

    def _background_task_finished(self):
        focus_origin = self._task_focus_origin
        self._worker = None
        self._worker_thread = None
        self._worker_busy = False
        self._task_context = None
        self._task_focus_origin = None
        self._update_action_availability()
        if (
            not self._close_requested
            and focus_origin
            and focus_origin.isEnabled()
            and focus_origin.isVisible()
        ):
            QtCore.QTimer.singleShot(0, focus_origin.setFocus)
        self._resume_pending_close()

    def cancel_active_task(self):
        if self._worker and self._worker_thread and self._worker_thread.isRunning():
            self._worker.cancel()
            if hasattr(self._worker_thread, "requestInterruption"):
                self._worker_thread.requestInterruption()
            self.show_status(self._t("cancelling"))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(".pdf"):
                    self._activate_document(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def closeEvent(self, event):
        task_running = self._has_active_task()
        update_running = self._has_active_update()
        if task_running or update_running:
            self._close_requested = True
            if task_running:
                self.cancel_active_task()
            event.ignore()
            return
        self._close_requested = False
        if self._allow_close_once:
            self._allow_close_once = False
            event.accept()
            return
        if self._is_dirty():
            event.ignore()
            self._show_dirty_close_prompt()
            return
        event.accept()

    def _show_dirty_close_prompt(self):
        if self._dirty_close_box and self._dirty_close_box.isVisible():
            self._dirty_close_box.raise_()
            return
        box, buttons = self._build_choice_box(
            "discard_draft_title",
            "discard_draft",
            (
                (
                    "discard",
                    "discard_close_action",
                    QMessageBox.DestructiveRole,
                ),
                ("keep", "keep_editing_action", QMessageBox.RejectRole),
            ),
            default_choice="keep",
            escape_choice="keep",
            icon=QMessageBox.Warning,
        )
        box.setWindowModality(QtCore.Qt.WindowModal)
        box.finished.connect(self._dirty_close_answered)
        self._dirty_close_box = box
        self._dirty_discard_button = buttons["discard"]
        box.open()

    def _dirty_close_answered(self, _result):
        box = self._dirty_close_box
        should_close = bool(
            box
            and box.clickedButton()
            is getattr(self, "_dirty_discard_button", None)
        )
        self._dirty_close_box = None
        self._dirty_discard_button = None
        if box:
            box.deleteLater()
        if should_close:
            self._allow_close_once = True
            QtCore.QTimer.singleShot(0, self.close)

    def resizeEvent(self, event):
        compact = event.size().height() < 620 or self._large_text_mode()
        self._compact_shell = compact
        self.root_layout.setContentsMargins(
            16 if compact else 24,
            10 if compact else 16,
            16 if compact else 24,
            8 if compact else 14,
        )
        self.root_layout.setSpacing(8 if compact else 12)
        self.editor_hint_label.setVisible(not compact)
        # Even the minimum-size shell keeps one concise affordance line for
        # the otherwise non-obvious editable/drag-enabled preview.
        self.preview_hint_label.setVisible(True)
        self.page_subtitle_label.setVisible(not compact)
        self._refresh_preview_hint()
        self._reflow_controls()
        if hasattr(self, "_document_display_name"):
            self._refresh_document_name()
        super(Main, self).resizeEvent(event)

    def changeEvent(self, event):
        if event.type() in (
            QtCore.QEvent.FontChange,
            QtCore.QEvent.ApplicationFontChange,
        ):
            self._apply_type_scale()
            self._update_accessible_layout_constraints()
            QtCore.QTimer.singleShot(0, self._reflow_controls)
        super(Main, self).changeEvent(event)

    def pre_check(self, path, index_dict):
        check_bookmarks(path, index_dict, self.keep_exist_dir)

    def write_tree_to_pdf(self):
        if self._has_active_task():
            return
        try:
            validation_error = self._validate_preview_tree()
            if validation_error:
                raise ValueError(validation_error)
            index_dict = self.tree_to_dict()
            if not index_dict:
                raise ValueError(self._t("no_bookmarks"))
            self.pre_check(self.pdf_path, index_dict)
        except BookmarkPageError as e:
            key = (
                "page_below_minimum"
                if e.reason == "below_minimum"
                else "page_above_maximum"
            )
            values = {"page": e.page_number}
            if e.page_count is not None:
                values["total"] = e.page_count
            self.alert_msg(self._t(key, **values), level="warn")
            return
        except ValueError as e:
            self.alert_msg(
                str(e) if str(e) else self._t("no_bookmarks"),
                level="warn",
            )
            return

        output_path = self._next_available_output_path(self.pdf_path)
        self.output_path_edit.setText(output_path)

        self._task_focus_origin = self.focusWidget()
        self.show_status(
            self._t(
                "generated_task",
                source=os.path.basename(self.pdf_path),
                output=os.path.basename(output_path),
            )
        )
        self._task_context = {
            "kind": "write",
            "pdf_path": self.pdf_path,
            "index_dict": index_dict,
            "keep_exist_dir": self.keep_exist_dir,
            "output_path": output_path,
            "generation_signature": self._generation_signature(
                self.pdf_path,
                index_dict,
                self.keep_exist_dir,
            ),
            "draft_signature": self._current_draft_signature(),
        }
        self._worker_busy = True
        self._worker_thread = QtCore.QThread(self)
        self._worker = PdfWriteWorker(
            self.pdf_path,
            index_dict,
            self.keep_exist_dir,
            output_path,
        )
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._pdf_write_finished)
        self._worker.failed.connect(self._pdf_write_failed)
        self._worker.cancelled.connect(self._task_cancelled)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker.cancelled.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._worker.cancelled.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._background_task_finished)
        self._worker_thread.start()
        self._update_action_availability()
        QtCore.QTimer.singleShot(0, self.cancel_button.setFocus)

    def _pdf_write_finished(self, new_path):
        if self._close_requested:
            return
        context = self._task_context or {}
        generated_signature = context.get("generation_signature")
        if generated_signature is None:
            generated_signature = self._generation_signature(
                context.get("pdf_path", self.pdf_path),
                context.get("index_dict"),
                context.get("keep_exist_dir", self.keep_exist_dir),
            )
        self._last_generated_path = self._canonical_source_path(new_path)
        self._last_generated_signature = generated_signature
        self._status_timer.stop()
        self._status_override_active = False
        if (
            not context
            or context.get("draft_signature")
            == self._current_draft_signature()
        ):
            self._mark_clean()
        self._sync_action_surface()
        self._refresh_action_status()
        if self.export_button.isVisible() and self.export_button.isEnabled():
            QtCore.QTimer.singleShot(0, self.export_button.setFocus)

    def _pdf_write_failed(self, message):
        if self._close_requested:
            return
        self.show_status(self._t("generation_failed"), 5000)
        if "Output target changed" in message:
            message = self._t("output_changed")
        self.alert_msg(
            self._t("generation_error", message=message),
            level="warn",
        )

    @staticmethod
    def dict_to_pdf(
        pdf_path, index_dict, keep_exist_dir=False, cancel_check=None
    ):
        return add_bookmark(
            pdf_path,
            index_dict,
            keep_exist_dir,
            cancel_check=cancel_check,
        )

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
    if "--smoke-test" in sys.argv:
        QtCore.QTimer.singleShot(
            0,
            lambda: _start_packaged_smoke_test(app, window),
        )
    else:
        window.show()
    exit_code = app.exec()
    smoke_tempdir = getattr(window, "_smoke_tempdir", None)
    if smoke_tempdir:
        smoke_tempdir.cleanup()
    sys.exit(exit_code)


def _start_packaged_smoke_test(app, window):
    """Exercise the frozen GUI-to-PDF path and exit with a machine result."""
    from pypdf import PdfReader, PdfWriter

    window._smoke_tempdir = tempfile.TemporaryDirectory(
        prefix="pdfdir-packaged-smoke-"
    )
    smoke_root = Path(window._smoke_tempdir.name)
    source_path = smoke_root / "source.pdf"
    output_path = smoke_root / "source_new.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as handle:
        writer.write(handle)

    window.alert_msg = lambda *_args, **_kwargs: None
    window.read_exist_dir_box.setChecked(False)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Packaged smoke bookmark 1")
    window.show()
    started_at = time.monotonic()

    def poll_result():
        task_running = bool(
            window._worker_thread and window._worker_thread.isRunning()
        )
        if output_path.exists() and not task_running:
            try:
                reader = PdfReader(output_path)
                destination = reader.outline[0]
                valid = (
                    destination.title == "Packaged smoke bookmark"
                    and reader.get_destination_page_number(destination) == 0
                )
            except Exception:
                valid = False
            if valid and os.environ.get("PDFDIR_SMOKE_OPEN_RESULT") == "1":
                valid = window._open_generated_pdf()
                QtCore.QTimer.singleShot(
                    750,
                    lambda: app.exit(0 if valid else 4),
                )
                return
            app.exit(0 if valid else 2)
            return
        if time.monotonic() - started_at > 20:
            app.exit(3)
            return
        QtCore.QTimer.singleShot(50, poll_result)

    window.write_tree_to_pdf()
    QtCore.QTimer.singleShot(50, poll_result)


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
