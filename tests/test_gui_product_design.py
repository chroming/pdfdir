import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfWriter
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from src.gui.main import Main
from tests.gui_test_utils import track_main_window


def _write_blank_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, main_window)
    main_window.show()
    return main_window


def test_primary_workspace_has_readable_default_geometry(window):
    assert window.width() >= 960
    assert window.height() >= 680
    assert window.minimumWidth() >= 780
    assert window.minimumHeight() >= 560
    assert window.dir_text_edit.isVisible()
    assert window.dir_tree_widget.isVisible()
    assert window.page_title_label.text() == "PDF 书签编辑器"
    assert window.workspace_frame.isVisible()
    assert not window.dir_tree_widget.alternatingRowColors()


def test_primary_action_and_status_remain_visible_at_minimum_window(window):
    window.resize(window.minimumSize())
    window.app.processEvents()
    window.window().layout().activate()

    visible_rect = window.centralWidget().rect()
    action_rect = QtCore.QRect(
        window.export_button.mapTo(window.centralWidget(), QtCore.QPoint()),
        window.export_button.size(),
    )

    assert visible_rect.contains(action_rect)
    assert window.export_button.isVisible()
    assert not window.statusbar.isVisible()
    assert window.action_status_label.isVisible()
    assert window.dir_text_edit.isVisible()
    assert window.dir_tree_widget.isVisible()

    window.to_english()
    window.app.processEvents()
    window.window().layout().activate()
    tools_rect = QtCore.QRect(
        window.advanced_button.mapTo(window.workspace_frame, QtCore.QPoint()),
        window.advanced_button.size(),
    )
    english_action_rect = QtCore.QRect(
        window.export_button.mapTo(window.centralWidget(), QtCore.QPoint()),
        window.export_button.size(),
    )

    assert window.workspace_frame.rect().contains(tools_rect)
    assert visible_rect.contains(english_action_rect)


def test_working_actions_remain_visible_at_minimum_window(window):
    class RunningThread:
        @staticmethod
        def isRunning():
            return True

    window.resize(window.minimumSize())
    window._worker_thread = RunningThread()
    window.show_status(window._t("generating"))
    window._update_action_availability()
    window.app.processEvents()
    window.window().layout().activate()

    visible_rect = window.centralWidget().rect()
    cancel_rect = QtCore.QRect(
        window.cancel_button.mapTo(window.centralWidget(), QtCore.QPoint()),
        window.cancel_button.size(),
    )
    assert visible_rect.contains(cancel_rect)
    assert window.cancel_button.isVisible()
    assert not window.export_button.isVisible()
    assert "正在生成" in window.action_status_label.text()

    window._worker_thread = None
    window._update_action_availability()


def test_recognition_rules_open_in_dialog_without_resizing_main_shell(
    window, qtbot
):
    window.resize(window.minimumSize())
    shell_size = window.size()
    action_position = window.export_button.mapToGlobal(QtCore.QPoint())

    assert not window.advanced_widget.isVisible()
    assert not window.advanced_button.isCheckable()

    window.advanced_button.click()

    dialog = window.advanced_dialog
    qtbot.waitUntil(dialog.isVisible)
    assert window.advanced_widget.isVisible()
    assert isinstance(dialog, QtWidgets.QDialog)
    assert window.advanced_widget.window() is dialog
    assert not window.level0_edit.isVisible()
    assert window.fix_non_seq_box.isVisible()
    assert window.sub_dir_group.isHidden()
    assert window.size() == shell_size
    assert window.export_button.mapToGlobal(QtCore.QPoint()) == action_position
    assert window.export_button.isVisible()

    window.level_mode_box.setCurrentIndex(1)

    assert window.level0_edit.isVisible()
    assert window.sub_dir_group.isEnabled()
    qtbot.keyClick(dialog, QtCore.Qt.Key_Escape)
    qtbot.waitUntil(lambda: not dialog.isVisible())
    assert window.advanced_button.hasFocus()


def test_core_actions_use_specific_user_facing_verbs(window):
    assert window.auto_toc_button.text() == "从 PDF 识别目录"
    assert window.auto_offset_button.text() == "识别页差"
    assert window.export_button.text() == "生成带书签的 PDF"
    assert window.level_mode_box.currentText() == "按缩进识别层级"


def test_output_path_is_visible_before_generation(window, tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    window.pdf_path_edit.setText(str(source_path))

    assert window.output_path_edit.text() == str(
        tmp_path / "source_new.pdf"
    )
    assert window.output_path_edit.isReadOnly()


def test_language_switch_translates_dynamic_controls_and_preview_columns(
    window,
):
    window.to_english()

    assert window.auto_toc_button.text() == "Recognize TOC"
    assert window.auto_offset_button.text() == "Detect"
    assert window.export_button.text() == "Generate bookmarked PDF"
    assert window.level_mode_box.itemText(0) == "Indentation"
    assert window.dir_tree_widget.headerItem().text(0) == "Bookmark title"
    assert window.dir_tree_widget.headerItem().text(2) == "PDF page"
    assert window.advanced_button.text() == "Recognition rules…"
    assert window.page_title_label.text() == "PDF Bookmark Editor"

    window.to_chinese()

    assert window.auto_toc_button.text() == "从 PDF 识别目录"
    assert window.dir_tree_widget.headerItem().text(0) == "书签标题"
    assert window.advanced_button.text() == "识别设置…"


def test_labels_shortcuts_and_accessible_names_support_keyboard_use(window):
    assert window.pdf_path_label.buddy() is window.pdf_path_edit
    assert window.dir_text_label.buddy() is window.dir_text_edit
    assert window.preview_label.buddy() is window.dir_tree_widget
    assert window.pdf_path_edit.accessibleName()
    assert window.dir_text_edit.accessibleName()
    assert window.dir_tree_widget.accessibleName()
    assert window.open_button.shortcut().toString() == "Ctrl+O"
    assert window.export_button.shortcut().toString() == "Ctrl+Return"
    assert window._save_shortcut.key().toString() in ("Ctrl+S", "Ctrl+S, ...")


def test_drag_and_drop_loads_pdf_and_ignores_other_files(window, tmp_path):
    pdf_file = tmp_path / "book.pdf"
    _write_blank_pdf(pdf_file)
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("not a pdf", encoding="utf-8")

    # Non-pdf drag should not accept
    txt_mime = QtCore.QMimeData()
    txt_mime.setUrls([QtCore.QUrl.fromLocalFile(str(txt_file))])
    drag_enter_txt = QtGui.QDragEnterEvent(
        QtCore.QPoint(10, 10),
        QtCore.Qt.CopyAction,
        txt_mime,
        QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier,
    )
    window.dragEnterEvent(drag_enter_txt)
    assert not drag_enter_txt.isAccepted()

    # PDF drag should accept and load on drop
    pdf_mime = QtCore.QMimeData()
    pdf_mime.setUrls([QtCore.QUrl.fromLocalFile(str(pdf_file))])
    drag_enter_pdf = QtGui.QDragEnterEvent(
        QtCore.QPoint(10, 10),
        QtCore.Qt.CopyAction,
        pdf_mime,
        QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier,
    )
    window.dragEnterEvent(drag_enter_pdf)
    assert drag_enter_pdf.isAccepted()

    drop_pdf = QtGui.QDropEvent(
        QtCore.QPointF(10, 10),
        QtCore.Qt.CopyAction,
        pdf_mime,
        QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier,
    )
    window.dropEvent(drop_pdf)
    assert window.pdf_path_edit.text() == str(pdf_file)


def test_bookmark_count_in_preview_title_updates_dynamically(window, qapp):
    assert window.preview_label.text() == "书签预览"

    window.dir_text_edit.setPlainText("Chapter 1 1\nChapter 2 5")
    qapp.processEvents()

    assert "共 2 条" in window.preview_label.text()

    window.to_english()
    assert "(2)" in window.preview_label.text()

    window.dir_text_edit.clear()
    qapp.processEvents()
    assert window.preview_label.text() == "Bookmark preview"


def test_save_shortcut_triggers_generation(window, tmp_path, monkeypatch):
    source_path = tmp_path / "book.pdf"
    _write_blank_pdf(source_path)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Chapter 1 1")

    clicked = []
    monkeypatch.setattr(window.export_button, "click", lambda: clicked.append(True))

    window._save_shortcut.activated.emit()
    assert clicked == [True]


def test_ocr_unavailable_message_provides_actionable_install_command(window):
    msg_zh = window._friendly_recognition_error("OCR fallback requires paddleocr")
    assert "pip install -r requirements_ocr.txt" in msg_zh

    window.to_english()
    msg_en = window._friendly_recognition_error("OCR fallback requires paddleocr")
    assert "pip install -r requirements_ocr.txt" in msg_en

