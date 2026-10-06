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
    assert not window.pdf_path_edit.isVisible()
    assert window.output_name_edit.isVisible()
    assert window.dir_text_edit.line_number_area_width() > 0
    assert window.level_mode_box.parentWidget() is window.left_tools
    assert window.offset_edit.parentWidget() is window.calibration_direct
    assert not window.calibration_panel.isVisible()


def test_related_controls_stay_grouped_at_default_and_minimum_width(window):
    for size in (QtCore.QSize(1200, 760), window.minimumSize()):
        window.resize(size)
        window.app.processEvents()
        window._reflow_controls()

        hierarchy = window.level_mode_box.geometry()
        rules = window.advanced_button.geometry()
        assert rules.center().y() == hierarchy.center().y()
        assert 0 <= rules.left() - hierarchy.right() <= 16
        assert window.calibrate_button.parentWidget() is window.right_tools
        assert window.offset_summary.parentWidget() is window.right_tools

    window.to_english()
    window.app.processEvents()
    window._reflow_controls()
    assert window.advanced_button.geometry().center().y() == (
        window.level_mode_box.geometry().center().y()
    )


def test_file_entry_starts_header_and_workspaces_share_reading_size(window):
    assert window.open_button.geometry().right() < (
        window.document_name_label.geometry().left()
    )
    assert window.dir_text_edit.fontMetrics().height() == (
        window.dir_tree_widget.fontMetrics().height()
    )


def test_fields_and_commands_share_a_control_track(window):
    for size in (window.size(), window.minimumSize()):
        window.resize(size)
        window.app.processEvents()
        controls = (
            window.open_button, window.level_mode_box, window.advanced_button,
            window.calibrate_button, window.hierarchy_button,
            window.output_name_edit, window.output_folder_button,
            window.export_button,
        )
        assert len({control.height() for control in controls}) == 1
        assert window.level_mode_box.mapTo(
            window, window.level_mode_box.rect().center()
        ).y() == window.calibrate_button.mapTo(
            window, window.calibrate_button.rect().center()
        ).y()


@pytest.mark.parametrize("name", ["level_mode_box", "unknown_level_box"])
def test_select_popup_shows_current_option_and_supports_keyboard(window, qtbot, name):
    if name == "unknown_level_box":
        window.advanced_button.click()
        window.rules_options_button.click()
        qtbot.waitUntil(window.rules_options.isVisible)
    combo = getattr(window, name)
    combo.setFocus()
    combo.showPopup()
    view = combo.view()
    qtbot.waitUntil(view.isVisible)
    assert view.selectionModel().isSelected(view.currentIndex())
    assert view.window().width() >= combo.width()
    qtbot.keyClick(view, QtCore.Qt.Key_Down)
    assert view.currentIndex().row() == 1
    assert view.selectionModel().isSelected(view.currentIndex())
    qtbot.keyClick(view, QtCore.Qt.Key_Escape)
    assert combo.currentIndex() == 0
    combo.showPopup()
    qtbot.keyClick(view, QtCore.Qt.Key_Down)
    qtbot.keyClick(view, QtCore.Qt.Key_Return)
    assert combo.currentIndex() == 1


def test_output_destination_details_align_with_filename_at_minimum_width(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.resize(window.minimumSize())
    window.app.processEvents()

    assert window.output_feedback_stack.currentWidget() is window.output_location_widget
    assert window.output_location_label.text()
    assert window.output_location_button.text() == "查看路径"
    assert window.output_location_widget.mapTo(
        window.action_frame, QtCore.QPoint()
    ).x() == window.output_name_edit.mapTo(
        window.action_frame, QtCore.QPoint()
    ).x()

    window.to_english()
    window.app.processEvents()
    assert window.output_location_button.text() == "View path"
    assert window.output_location_label.text().startswith("Source folder")

    destination = tmp_path / ("destination-" + "long-name-" * 8)
    destination.mkdir()
    window._output_directory_override = str(destination)
    window._update_action_availability()
    window.app.processEvents()
    location = window.output_location_button.mapTo(
        window.output_feedback_stack, QtCore.QPoint()
    )
    assert "…" in window.output_location_label.text()
    assert location.x() + window.output_location_button.width() <= (
        window.output_feedback_stack.width()
    )
    assert window.output_location_label.toolTip() == window.output_path_edit.text()


def test_workspace_does_not_frame_sparse_editors_as_full_height_cards(window):
    """The two task surfaces share one canvas, including while editing."""
    style = window.styleSheet()
    assert style.count("QTreeWidget#dir_tree_widget {") == 1
    assert style.count("QHeaderView::section {") == 1
    assert "QTextEdit#dir_text_edit" not in style

    window.dir_text_edit.setFocus()
    window.app.processEvents()
    for editor in (window.dir_text_edit, window.dir_tree_widget):
        image = editor.grab().toImage()
        right_edge = image.pixelColor(image.width() - 2, image.height() // 2)
        assert min(right_edge.red(), right_edge.green(), right_edge.blue()) > 235

    window.dir_tree_widget.setFocus()
    window.app.processEvents()
    tree_image = window.dir_tree_widget.grab().toImage()
    left_edge = tree_image.pixelColor(1, tree_image.height() // 2)
    assert left_edge.blue() - left_edge.red() < 20


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


def test_recognition_rules_expand_inline_without_moving_preview_or_output(
    window, qtbot
):
    window.resize(window.minimumSize())
    shell_size = window.size()
    action_position = window.export_button.mapToGlobal(QtCore.QPoint())
    preview_rect = window.dir_tree_widget.geometry()

    assert not window.advanced_widget.isVisible()
    assert window.advanced_button.isCheckable()

    window.advanced_button.click()

    qtbot.waitUntil(window.rules_scroll.isVisible)
    assert window.advanced_widget.isVisible()
    assert window.advanced_widget.window() is window
    assert not window.level0_edit.isVisible()
    assert not window.fix_non_seq_box.isVisible()
    assert window.sub_dir_group.isHidden()
    assert window.size() == shell_size
    assert window.export_button.mapToGlobal(QtCore.QPoint()) == action_position
    assert window.export_button.isVisible()
    assert window.dir_tree_widget.geometry() == preview_rect

    window.level_mode_box.setCurrentIndex(1)
    window._add_rule_level(0)
    assert window.level0_edit.isVisible()
    assert window.sub_dir_group.isEnabled()
    qtbot.keyClick(window.level0_box, QtCore.Qt.Key_Escape)
    qtbot.waitUntil(lambda: not window.rules_scroll.isVisible())
    assert window.advanced_button.hasFocus()


def test_core_actions_use_specific_user_facing_verbs(window):
    assert window.auto_toc_button.text() == "从 PDF 识别"
    assert window.auto_offset_button.text() == "识别页差"
    assert window.export_button.text() == "生成 PDF"
    assert window.level_mode_box.currentText() == "按缩进"


def test_recognize_button_disabled_state_does_not_look_available(
    window, tmp_path
):
    def dark_pixel_count():
        image = window.auto_toc_button.grab().toImage()
        return sum(
            max(image.pixelColor(x, y).getRgb()[:3]) < 140
            for y in range(image.height())
            for x in range(image.width())
        )

    assert not window.auto_toc_button.isEnabled()
    disabled_dark = dark_pixel_count()

    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.app.processEvents()

    assert window.auto_toc_button.isEnabled()
    assert dark_pixel_count() > disabled_dark + 20


def test_output_path_is_visible_before_generation(window, tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    window.pdf_path_edit.setText(str(source_path))

    assert window.output_path_edit.text() == str(
        tmp_path / "source_new.pdf"
    )
    assert window.output_path_edit.isReadOnly()
    assert window.output_name_edit.text() == "source_new.pdf"
    assert "source.pdf" in window.document_name_label.toolTip()
    assert "1 页" in window.document_name_label.text()


def test_large_font_document_identity_elides_without_clipping_page_count(
    window, qapp, tmp_path
):
    original_font = qapp.font()
    large_font = QtGui.QFont(original_font)
    large_font.setPointSize(24)
    source = tmp_path / ("long-document-title-" + "section-" * 12 + ".pdf")
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    writer.write(str(source))
    try:
        qapp.setFont(large_font)
        window.to_english()
        window.resize(window.minimumSize())
        window.pdf_path_edit.setText(str(source))
        for _ in range(3):
            qapp.processEvents()

        label = window.document_name_label
        assert label.accessibleDescription().endswith("2 pages")
        assert label.text().endswith("2 pages")
        assert "…" in label.text()
        assert (
            label.fontMetrics().horizontalAdvance(label.text())
            <= label.contentsRect().width()
        )
    finally:
        qapp.setFont(original_font)


def test_output_name_and_folder_are_editable_without_overwriting(window, tmp_path, qtbot, monkeypatch):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    folder = tmp_path / "results"
    folder.mkdir()
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Chapter 1")

    window.output_name_edit.setFocus()
    window.output_name_edit.selectAll()
    qtbot.keyClicks(window.output_name_edit, "reviewed.pdf")
    assert window.output_path_edit.text() == str(tmp_path / "reviewed.pdf")

    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getExistingDirectory",
        lambda *_args, **_kwargs: str(folder),
    )
    window.output_folder_button.click()
    assert window.output_path_edit.text() == str(folder / "reviewed.pdf")
    assert window.export_button.isEnabled()

    (folder / "reviewed.pdf").write_bytes(b"occupied")
    window._update_action_availability()
    assert not window.export_button.isEnabled()
    assert window.output_feedback_stack.currentWidget() is window.output_error_label
    assert "已存在" in window.output_error_label.text()
    assert "已存在" in window.output_name_edit.accessibleDescription()

    window.output_name_edit.selectAll()
    qtbot.keyClicks(window.output_name_edit, "source.pdf")
    assert window.export_button.isEnabled()  # Different output folder is safe.
    window._output_directory_override = ""
    window._update_action_availability()
    assert not window.export_button.isEnabled()
    assert "不能覆盖" in window.output_error_label.text()
    assert "不能覆盖" in window.output_name_edit.accessibleDescription()


def test_output_error_is_complete_beside_field_at_english_minimum(
    window, tmp_path, qtbot
):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.to_english()
    window.resize(window.minimumSize())
    window.output_name_edit.setFocus()
    window.output_name_edit.selectAll()
    qtbot.keyClicks(window.output_name_edit, "bad.txt")
    window.app.processEvents()

    assert window.output_error_label.isVisible()
    assert window.output_error_label.text() == "The output filename must end in .pdf."
    assert window.output_error_label.buddy() is window.output_name_edit
    assert ".pdf" in window.output_name_edit.accessibleDescription()
    assert not window.export_button.isEnabled()
    assert not window.action_status_label.text()

    window.output_name_edit.selectAll()
    qtbot.keyClicks(window.output_name_edit, "good.pdf")
    assert window.output_feedback_stack.currentWidget() is window.output_location_widget
    assert window.output_name_edit.accessibleDescription() == ""


def test_missing_output_folder_error_belongs_to_folder_control(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    folder = tmp_path / "results"
    _write_blank_pdf(source)
    folder.mkdir()
    window.pdf_path_edit.setText(str(source))
    window._output_directory_override = str(folder)
    window._update_action_availability()
    folder.rmdir()

    window._update_action_availability()

    assert window.output_error_label.buddy() is window.output_folder_button
    assert "文件夹不可用" in window.output_error_label.text()
    assert "文件夹不可用" in window.output_folder_button.accessibleDescription()
    assert not window.output_name_edit.property("invalid")
    assert not window.export_button.isEnabled()


def test_changing_pdf_resets_output_name_even_while_field_has_focus(window, tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    _write_blank_pdf(first)
    _write_blank_pdf(second)
    window.pdf_path_edit.setText(str(first))
    window.output_name_edit.setFocus()

    window.pdf_path_edit.setText(str(second))

    assert window.output_name_edit.text() == "second_new.pdf"
    assert window.output_path_edit.text() == str(tmp_path / "second_new.pdf")


def test_paste_preserves_existing_directory_draft(window, qtbot):
    clipboard = window.app.clipboard()
    previous = clipboard.text()
    try:
        window.dir_text_edit.setPlainText("Chapter 1")
        window.dir_text_edit.moveCursor(QtGui.QTextCursor.End)
        clipboard.setText("\n  Section 2")
        window.paste_button.click()
        assert window.dir_text_edit.toPlainText() == "Chapter 1\n  Section 2"
        assert window.dir_text_edit.blockCount() == 2
    finally:
        clipboard.setText(previous)


def test_language_switch_translates_dynamic_controls_and_preview_columns(
    window,
):
    window.to_english()

    assert window.auto_toc_button.text() == "Recognize from PDF"
    assert window.auto_offset_button.text() == "Detect"
    assert window.export_button.text() == "Generate PDF"
    assert window.level_mode_box.itemText(0) == "Indentation"
    assert window.dir_tree_widget.headerItem().text(0) == "Bookmark title"
    assert window.dir_tree_widget.headerItem().text(2) == "PDF page"
    assert window.advanced_button.text() == "Rules"
    assert window.page_title_label.text() == "PDF Bookmark Editor"

    window.to_chinese()

    assert window.auto_toc_button.text() == "从 PDF 识别"
    assert window.dir_tree_widget.headerItem().text(0) == "书签标题"
    assert window.advanced_button.text() == "规则"


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


@pytest.mark.parametrize("english,minimum", [(False, False), (True, True)])
def test_tab_order_follows_visible_bookmark_workflow(
    window, tmp_path, english, minimum
):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Chapter 1")
    if english:
        window.to_english()
    if minimum:
        window.resize(window.minimumSize())
        window.app.processEvents()
    clipboard = window.app.clipboard()
    previous = clipboard.text()
    try:
        clipboard.setText("Next chapter 2")
        window.open_button.setFocus()
        visited = []
        for _ in range(20):
            window.focusNextChild()
            visited.append(window.focusWidget())
            if window.focusWidget() is window.help_button:
                break
        expected = (
            window.source_tabs,
            window.source_import_button,
            window.level_mode_box,
            window.advanced_button,
            window.dir_text_edit,
            window.hierarchy_button,
            window.calibrate_button,
            window.dir_tree_widget,
            window.output_name_edit,
            window.output_folder_button,
            window.output_location_button,
            window.export_button,
            window.document_info_button,
            window.help_button,
        )
        assert [control for control in visited if control in expected] == list(expected)
    finally:
        clipboard.setText(previous)


def test_tab_and_shift_tab_reach_recognition_actions(window, tmp_path, qtbot):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    window.pdf_path_edit.setText(str(source))
    clipboard = window.app.clipboard()
    previous = clipboard.text()
    try:
        clipboard.setText("Chapter 1")
        window.open_button.setFocus()
        qtbot.keyClick(window.open_button, QtCore.Qt.Key_Tab)
        assert window.source_tabs.hasFocus()
        qtbot.keyClick(window.source_tabs, QtCore.Qt.Key_Tab)
        assert window.source_import_button.hasFocus()
        qtbot.keyClick(
            window.source_import_button,
            QtCore.Qt.Key_Tab,
            QtCore.Qt.ShiftModifier,
        )
        assert window.source_tabs.hasFocus()
    finally:
        clipboard.setText(previous)


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
    assert window.preview_label.text() == "书签"
    assert window.preview_count_label.text() == "0 条"

    window.dir_text_edit.setPlainText("Chapter 1 1\nChapter 2 5")
    qapp.processEvents()

    assert window.preview_count_label.text() == "2 条"

    window.to_english()
    assert window.preview_count_label.text() == "2 items"

    window.dir_text_edit.clear()
    qapp.processEvents()
    assert window.preview_label.text() == "Bookmarks"
    assert window.preview_count_label.text() == "0 items"


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
