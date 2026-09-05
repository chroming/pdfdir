import os
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfWriter
from PySide6 import QtCore, QtGui, QtWidgets

from src.gui.main import Main
from src.gui import main as main_module
from tests.gui_test_utils import track_main_window


def _write_pdf(path, *, bookmarks=()):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    for title in bookmarks:
        writer.add_outline_item(title, 0)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, main_window)
    main_window.show()
    return main_window


def test_empty_preview_explains_how_to_start(window, qtbot):
    qtbot.waitUntil(window.preview_empty_label.isVisible)
    assert window.preview_empty_label.isVisible()
    assert "目录" in window.preview_empty_label.text()

    window.dir_text_edit.setPlainText("Chapter 1  1")

    assert not window.preview_empty_label.isVisible()


def test_invalid_numbering_regex_is_inline_and_blocks_generation(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    _write_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("1. Chapter 1  1")
    window.level_mode_box.setCurrentIndex(1)
    window.level0_box.setChecked(True)
    window.level0_edit.setText("[")
    window.advanced_button.click()

    assert window.regex_error_label.isVisible()
    assert "正则" in window.regex_error_label.text()
    assert not window.export_button.isEnabled()

    window.level0_edit.setText(r"\d+\.")

    assert not window.regex_error_label.isVisible()
    assert window.export_button.isEnabled()


def test_pure_page_number_is_not_exportable_bookmark(window, tmp_path):
    source = tmp_path / "source.pdf"
    _write_pdf(source)
    window.pdf_path_edit.setText(str(source))

    window.dir_text_edit.setPlainText("12")

    assert not window.export_button.isEnabled()
    assert "标题" in window.export_button.toolTip()


def test_rebuilding_after_manual_preview_edit_is_explicit(window):
    window.dir_text_edit.setPlainText("Original title 1")
    item = window.dir_tree_widget.topLevelItem(0)
    item.setText(0, "Corrected title")

    assert window._preview_manually_adjusted
    assert "手工调整" in window.preview_hint_label.text()

    window.offset_edit.setText("1")

    assert window.dir_tree_widget.topLevelItem(0).text(0) == "Original title"
    assert "重新生成" in window.statusbar.currentMessage()


def test_advanced_dialog_has_local_mode_switch_and_initial_focus(
    window, qtbot
):
    window.advanced_button.click()
    qtbot.waitUntil(window.advanced_dialog.isVisible)
    qtbot.waitUntil(lambda: window.advanced_dialog.focusWidget() is not None)

    assert window.advanced_dialog.focusWidget() is window.advanced_mode_box
    assert window.advanced_mode_box.currentIndex() == 0
    assert window.sub_dir_group.isHidden()

    window.advanced_mode_box.setCurrentIndex(1)

    assert window.level_mode_box.currentIndex() == 1
    assert not window.sub_dir_group.isHidden()
    assert window.sub_dir_group.isEnabled()

    window.advanced_mode_box.setCurrentIndex(0)

    assert window.sub_dir_group.isHidden()


def _complete_generation(window, source, output):
    _write_pdf(source)
    window._activate_document(str(source))
    window.dir_text_edit.setPlainText("Chapter 1")
    output.write_bytes(source.read_bytes())
    window._task_context = {
        "kind": "write",
        "pdf_path": str(source),
        "index_dict": window.tree_to_dict(),
        "keep_exist_dir": window.keep_exist_dir,
        "draft_signature": window._current_draft_signature(),
    }
    window._pdf_write_finished(str(output))


def test_success_keeps_actual_result_and_persistent_open_action(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"

    _complete_generation(window, source, output)

    assert window.output_path_edit.text() == str(output)
    assert window.export_button.text() == "打开生成的 PDF"
    assert "已生成" in window.action_status_label.text()
    assert str(output) not in window.action_status_label.text()
    assert str(output) not in window.action_status_label.toolTip()

    window._status_timeout()

    assert window.output_path_edit.text() == str(output)
    assert window.export_button.text() == "打开生成的 PDF"
    assert "已生成" in window.action_status_label.text()


def test_success_primary_action_opens_result_without_writing_duplicate(
    window, tmp_path, monkeypatch
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    duplicate = tmp_path / "source_new_2.pdf"
    opened = []
    _complete_generation(window, source, output)
    monkeypatch.setattr(
        QtGui.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toLocalFile()) or True,
    )

    window.export_button.click()

    assert opened == [str(output)]
    assert not duplicate.exists()
    assert window.export_button.text() == "打开生成的 PDF"

    assert window._open_generated_pdf()
    assert opened == [str(output), str(output)]


def test_effective_output_changes_leave_and_restore_result_state(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    _complete_generation(window, source, output)
    item = window.dir_tree_widget.topLevelItem(0)

    item.setText(0, "Changed chapter")

    assert window.export_button.text() == "生成带书签的 PDF"
    assert window.output_path_edit.text() == str(tmp_path / "source_new_2.pdf")
    assert "未生成" in window.action_status_label.text()

    item.setText(0, "Chapter")

    assert window.export_button.text() == "打开生成的 PDF"
    assert window.output_path_edit.text() == str(output)
    assert "已生成" in window.action_status_label.text()


def test_hidden_numbering_rules_do_not_make_indent_result_stale(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    _complete_generation(window, source, output)

    window.level0_edit.setText(r"^Chapter")

    assert window.level_mode_box.currentIndex() == 0
    assert window.sub_dir_group.isHidden()
    assert window.export_button.text() == "打开生成的 PDF"
    assert window.output_path_edit.text() == str(output)


def test_missing_result_recovers_to_generation_without_duplicate(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    _complete_generation(window, source, output)
    output.unlink()

    window.export_button.click()

    assert window.export_button.text() == "生成带书签的 PDF"
    assert window.output_path_edit.text() == str(output)
    assert "移动或删除" in window.action_status_label.text()


def test_open_failure_keeps_result_available_for_retry(
    window, tmp_path, monkeypatch
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    _complete_generation(window, source, output)
    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", lambda _url: False)

    window.export_button.click()

    assert window.output_path_edit.text() == str(output)
    assert window.export_button.text() == "打开生成的 PDF"
    assert "无法打开" in window.action_status_label.text()


def test_result_removed_while_idle_explains_recovery(window, tmp_path, qtbot):
    output = tmp_path / "source_new.pdf"
    _complete_generation(window, tmp_path / "source.pdf", output)
    output.unlink()
    qtbot.waitUntil(lambda: window._primary_action_mode == "generate", timeout=3000)
    assert "移动或删除" in window.action_status_label.toolTip()
    assert not window.open_result_action.isEnabled()
    assert not output.exists()


def test_result_action_translates_without_losing_ownership(window, tmp_path):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    _complete_generation(window, source, output)

    window.to_english()

    assert window.output_path_edit.text() == str(output)
    assert window.export_button.text() == "Open generated PDF"
    assert "Generated" in window.action_status_label.text()


@pytest.mark.parametrize("column", [1, 2])
@pytest.mark.parametrize("value", ["", "not a page"])
def test_invalid_page_after_result_is_recoverable(window, tmp_path, column, value):
    _complete_generation(window, tmp_path / "source.pdf", tmp_path / "source_new.pdf")
    item = window.dir_tree_widget.topLevelItem(0)
    item.setText(column, value)
    assert not window.export_button.isEnabled()
    assert window.action_status_label.property("statusKind") == "error"
    item.setText(column, "1")
    assert window.export_button.isEnabled()
    assert window.export_button.text() == "打开生成的 PDF"


@pytest.mark.parametrize("kind", ["toc", "offset"])
@pytest.mark.parametrize("edit", ["title", "delete", "offset", "rules"])
def test_recognition_preserves_newer_complete_draft(
    window, tmp_path, qtbot, monkeypatch, kind, edit
):
    source = tmp_path / "source.pdf"
    _write_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Original 1\n  Child 1")
    release = threading.Event()

    def recognize(*_args, **_kwargs):
        assert release.wait(5)
        return "Replacement 1" if kind == "toc" else 2

    monkeypatch.setattr(
        main_module, "extract_toc_text" if kind == "toc" else "infer_page_offset", recognize
    )
    try:
        (window.fill_toc_text if kind == "toc" else window.fill_offset)()
        item = window.dir_tree_widget.topLevelItem(0)
        if edit == "title":
            item.setText(0, "Manual correction")
        elif edit == "delete":
            window.dir_tree_widget.remove_item(item.child(0))
        elif edit == "offset":
            window.offset_edit.setText("3")
        else:
            window.level_mode_box.setCurrentIndex(1)
        draft = window._current_draft_signature()
    finally:
        release.set()
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5000)
    assert window._current_draft_signature() == draft
    assert "丢弃" in window.action_status_label.toolTip()


def test_busy_document_guard_covers_drop_and_activation(window, tmp_path, monkeypatch):
    source, other = tmp_path / "source.pdf", tmp_path / "other.pdf"
    _write_pdf(source)
    _write_pdf(other)
    window._activate_document(str(source))
    window._worker_busy = True
    window._task_context = {"kind": "toc"}
    window._update_action_availability()
    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl.fromLocalFile(str(other))])
    event = QtGui.QDropEvent(
        QtCore.QPointF(10, 10), QtCore.Qt.CopyAction, mime,
        QtCore.Qt.LeftButton, QtCore.Qt.NoModifier,
    )
    try:
        assert not window._activate_document(str(other))
        window.dropEvent(event)
        assert not event.isAccepted()
        assert window.pdf_path == str(source)
    finally:
        window._worker_busy = False
        window._task_context = None
        window._update_action_availability()


def test_changed_source_reenables_generation_and_keeps_old_result(
    window, tmp_path, qtbot, monkeypatch
):
    from pypdf import PdfReader

    source, output = tmp_path / "source.pdf", tmp_path / "source_new.pdf"
    _complete_generation(window, source, output)
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=72, height=72)
    writer.write(str(source))
    qtbot.waitUntil(lambda: window._primary_action_mode == "generate", timeout=3000)
    assert "源 PDF 已更改" in window.action_status_label.toolTip()
    opened = []
    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    window.open_result_action.trigger()
    assert opened == [str(output)]
    window.export_button.click()
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5000)
    assert len(PdfReader(tmp_path / "source_new_2.pdf").pages) == 2
    assert len(PdfReader(output).pages) == 1
    assert window._primary_action_mode == "open"


def test_existing_bookmark_option_only_appears_when_relevant(
    window, tmp_path, monkeypatch
):
    plain = tmp_path / "plain.pdf"
    bookmarked = tmp_path / "bookmarked.pdf"
    _write_pdf(plain)
    _write_pdf(bookmarked, bookmarks=("Existing",))
    monkeypatch.setattr(window, "_prompt_import_bookmarks", lambda *_args: False)

    assert window._activate_document(str(plain))
    assert not window.keep_exist_dir_box.isVisible()

    assert window._activate_document(str(bookmarked))
    assert window.keep_exist_dir_box.isVisible()
    assert "源 PDF" in window.keep_exist_dir_box.text()


def test_imported_bookmark_titles_are_not_interpreted_as_rich_text(
    window, tmp_path, monkeypatch
):
    source = tmp_path / "bookmarked.pdf"
    _write_pdf(source, bookmarks=("<b>Chapter</b>",))
    monkeypatch.setattr(window, "_prompt_import_bookmarks", lambda *_args: True)

    assert window._activate_document(str(source))

    assert "<b>Chapter</b>" in window.dir_text_edit.toPlainText()
    assert not window.keep_exist_dir_box.isVisible()


def test_document_switch_can_cancel_or_clear_a_bound_draft(
    window, tmp_path, monkeypatch
):
    source_a = tmp_path / "a.pdf"
    source_b = tmp_path / "b.pdf"
    _write_pdf(source_a)
    _write_pdf(source_b)
    assert window._activate_document(str(source_a))
    window.dir_text_edit.setPlainText("Draft A 1")

    monkeypatch.setattr(window, "_prompt_document_switch", lambda: "cancel")
    assert not window._activate_document(str(source_b))
    assert window.pdf_path_edit.text() == str(source_a)
    assert window.dir_text_edit.toPlainText() == "Draft A 1"

    monkeypatch.setattr(window, "_prompt_document_switch", lambda: "clear")
    assert window._activate_document(str(source_b))
    assert window.pdf_path_edit.text() == str(source_b)
    assert not window.dir_text_edit.toPlainText()


def test_invalid_pdf_keeps_current_document_and_draft(
    window, tmp_path, monkeypatch
):
    source = tmp_path / "source.pdf"
    broken = tmp_path / "broken.pdf"
    _write_pdf(source)
    broken.write_bytes(b"not a pdf")
    assert window._activate_document(str(source))
    window.dir_text_edit.setPlainText("Draft 1")
    warnings = []
    monkeypatch.setattr(
        window,
        "alert_msg",
        lambda message, **_kwargs: warnings.append(message),
    )

    assert not window._activate_document(str(broken))

    assert window.pdf_path_edit.text() == str(source)
    assert window.dir_text_edit.toPlainText() == "Draft 1"
    assert warnings and "无法打开" in warnings[0]


def test_window_owns_alerts_and_skips_path_commit_while_closing(
    window, tmp_path, monkeypatch
):
    parents = []
    activated = []
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "exec",
        lambda box: parents.append(box.parent()),
    )
    monkeypatch.setattr(
        window,
        "_activate_document",
        lambda path: activated.append(path),
    )

    window.alert_msg("Owned message")
    window.pdf_path_edit.setText(str(tmp_path / "missing.pdf"))
    window._close_requested = True
    window._commit_typed_pdf_path()
    window._close_requested = False

    assert parents == [window]
    assert not activated


def test_close_with_ungenerated_draft_requires_confirmation(window, qapp):
    window.dir_text_edit.setPlainText("Unsaved chapter 1")
    event = QtGui.QCloseEvent()

    window.closeEvent(event)
    qapp.processEvents()

    assert not event.isAccepted()
    assert window._dirty_close_box.isVisible()
    assert window.isWindowModified()
    assert window._dirty_close_box.defaultButton().text() == "继续编辑"
    window._dirty_close_box.defaultButton().click()


def test_draft_choice_dialogs_name_effects_and_keep_safe_defaults(window):
    switch_box, switch_buttons = window._build_choice_box(
        "switch_draft_title",
        "switch_draft",
        (
            ("keep", "carry_draft_action", QtWidgets.QMessageBox.AcceptRole),
            (
                "clear",
                "clear_draft_action",
                QtWidgets.QMessageBox.DestructiveRole,
            ),
            ("cancel", "cancel_action", QtWidgets.QMessageBox.RejectRole),
        ),
        default_choice="cancel",
        escape_choice="cancel",
    )

    assert {button.text() for button in switch_box.buttons()} == {
        "沿用草稿",
        "清空草稿",
        "取消",
    }
    assert switch_box.defaultButton() is switch_buttons["cancel"]
    assert switch_box.escapeButton() is switch_buttons["cancel"]

    import_box, import_buttons = window._build_choice_box(
        "import_title",
        "replace_draft",
        (
            (
                "import",
                "import_replace_action",
                QtWidgets.QMessageBox.AcceptRole,
            ),
            (
                "keep",
                "keep_draft_action",
                QtWidgets.QMessageBox.RejectRole,
            ),
        ),
        default_choice="keep",
        escape_choice="keep",
    )

    assert {button.text() for button in import_box.buttons()} == {
        "导入并替换",
        "保留当前草稿",
    }
    assert import_box.defaultButton() is import_buttons["keep"]
    assert import_box.escapeButton() is import_buttons["keep"]

    window.to_english()
    close_box, close_buttons = window._build_choice_box(
        "discard_draft_title",
        "discard_draft",
        (
            (
                "discard",
                "discard_close_action",
                QtWidgets.QMessageBox.DestructiveRole,
            ),
            (
                "keep",
                "keep_editing_action",
                QtWidgets.QMessageBox.RejectRole,
            ),
        ),
        default_choice="keep",
        escape_choice="keep",
        icon=QtWidgets.QMessageBox.Warning,
    )

    assert {button.text() for button in close_box.buttons()} == {
        "Discard and Close",
        "Keep Editing",
    }
    assert close_box.defaultButton() is close_buttons["keep"]
    assert close_box.escapeButton() is close_buttons["keep"]


def test_prompt_results_follow_the_clicked_semantic_action(
    window, qapp
):
    def choose(invoke, label):
        observed = {}

        def click_button():
            boxes = [
                widget
                for widget in qapp.topLevelWidgets()
                if isinstance(widget, QtWidgets.QMessageBox)
                and widget.isVisible()
                and widget.parent() is window
            ]
            assert len(boxes) == 1
            box = boxes[0]
            observed["default"] = box.defaultButton().text()
            button = next(
                button for button in box.buttons() if button.text() == label
            )
            button.click()

        QtCore.QTimer.singleShot(0, click_button)
        return invoke(), observed

    result, observed = choose(window._prompt_document_switch, "沿用草稿")
    assert result == "keep"
    assert observed["default"] == "取消"

    result, _observed = choose(window._prompt_document_switch, "清空草稿")
    assert result == "clear"

    result, _observed = choose(
        lambda: window._prompt_import_bookmarks(True),
        "保留当前草稿",
    )
    assert result is False

    result, _observed = choose(
        lambda: window._prompt_import_bookmarks(False),
        "导入为草稿",
    )
    assert result is True


def test_dirty_close_only_closes_for_explicit_discard(
    window, qapp, monkeypatch
):
    closed = []
    monkeypatch.setattr(window, "close", lambda: closed.append(True))

    window._show_dirty_close_prompt()
    qapp.processEvents()
    box = window._dirty_close_box
    assert {button.text() for button in box.buttons()} == {
        "放弃并关闭",
        "继续编辑",
    }
    box.defaultButton().click()
    qapp.processEvents()
    assert not closed

    window._show_dirty_close_prompt()
    qapp.processEvents()
    box = window._dirty_close_box
    discard = next(
        button for button in box.buttons() if button.text() == "放弃并关闭"
    )
    discard.click()
    qapp.processEvents()
    assert closed == [True]


def test_successful_generation_baseline_then_new_edit_is_dirty(
    window, tmp_path
):
    source = tmp_path / "source.pdf"
    _write_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Chapter 1  1")

    assert window.isWindowModified()

    window._pdf_write_finished(str(tmp_path / "source_new.pdf"))
    assert not window.isWindowModified()

    window.dir_text_edit.append("Chapter 2  1")
    assert window.isWindowModified()


def test_write_task_freezes_the_snapshot_controls_and_prioritizes_cancel(
    window, tmp_path
):
    class RunningThread:
        @staticmethod
        def isRunning():
            return True

    source = tmp_path / "source.pdf"
    _write_pdf(source)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Chapter 1  1")
    window._worker_thread = RunningThread()
    window._task_context = {"kind": "write"}

    window._update_action_availability()

    for control in (
        window.pdf_path_edit,
        window.open_button,
        window.dir_text_edit,
        window.dir_tree_widget,
        window.level_mode_box,
        window.offset_edit,
        window.advanced_button,
        window.keep_exist_dir_box,
    ):
        assert not control.isEnabled()
    assert window.cancel_button.isVisible()
    assert not window.export_button.isVisible()

    window._worker_thread = None
    window._task_context = None
    window._update_action_availability()


def test_english_accessibility_text_and_context_action_are_translated(window):
    window.to_english()

    assert window.page_title_label.accessibleName() == "PDF Bookmark Editor"
    assert "preview" in window.export_button.accessibleDescription().lower()
    assert window.dir_tree_widget.remove_action.text() == "Delete"
    for editor in window._regex_editors:
        assert editor.accessibleName()


def test_ctrl_tab_leaves_toc_editor_without_removing_tab_indentation(
    window, qtbot
):
    window.dir_text_edit.setFocus()

    qtbot.keyClick(
        window.dir_text_edit,
        QtCore.Qt.Key_Tab,
        modifier=QtCore.Qt.ControlModifier,
    )

    assert not window.dir_text_edit.hasFocus()

    window.dir_text_edit.setFocus()
    qtbot.keyClick(window.dir_text_edit, QtCore.Qt.Key_Tab)
    assert "\t" in window.dir_text_edit.toPlainText()


def test_escape_cancels_once_from_editor_and_cancel_button(window, qtbot):
    class RunningThread:
        @staticmethod
        def isRunning():
            return True

    class Worker:
        def __init__(self):
            self.cancel_count = 0

        def cancel(self):
            self.cancel_count += 1

    worker = Worker()
    window._worker = worker
    window._worker_thread = RunningThread()
    window._task_context = {"kind": "toc"}
    window._update_action_availability()
    window.activateWindow()
    window.raise_()

    window.dir_text_edit.setFocus()
    qtbot.waitUntil(window.dir_text_edit.hasFocus)
    qtbot.keyClick(window.dir_text_edit, QtCore.Qt.Key_Escape)
    assert worker.cancel_count == 1

    window.cancel_button.setFocus()
    qtbot.waitUntil(window.cancel_button.hasFocus)
    qtbot.keyClick(window.cancel_button, QtCore.Qt.Key_Escape)
    assert worker.cancel_count == 2

    window._worker = None
    window._worker_thread = None
    window._task_context = None


def test_large_font_preserves_core_workspaces_and_reflows_controls(
    window, qapp, qtbot, tmp_path
):
    original_font = qapp.font()
    large_font = QtGui.QFont(original_font)
    large_font.setPointSize(24)
    try:
        qapp.setFont(large_font)
        window.to_english()
        window.resize(window.minimumSize())
        qtbot.wait(10)
        window._reflow_controls()
        window.layout().activate()

        assert window.minimumSize() == QtCore.QSize(900, 700)
        assert window._tools_compact
        assert window._actions_compact
        line_height = QtGui.QFontMetrics(qapp.font()).lineSpacing()
        assert window.dir_text_edit.viewport().height() >= line_height * 2
        assert window.dir_tree_widget.viewport().height() >= line_height * 2
        assert window.preview_hint_label.isVisible()
        assert "F2" in window.preview_hint_label.text()
        for control in (
            window.advanced_button,
            window.auto_offset_button,
            window.export_button,
        ):
            assert control.width() >= control.sizeHint().width()
            control_rect = QtCore.QRect(
                control.mapTo(window.centralWidget(), QtCore.QPoint()),
                control.size(),
            )
            assert window.centralWidget().rect().contains(control_rect)

        class RunningThread:
            @staticmethod
            def isRunning():
                return True

        long_name = (
            "source-document-with-a-deliberately-long-visible-name.pdf"
        )
        source = tmp_path / long_name
        _write_pdf(source)
        window.pdf_path_edit.setText(str(source))
        window._worker_thread = RunningThread()
        window._task_context = {"kind": "write"}
        window._update_action_availability()
        window.layout().activate()
        assert (
            window.cancel_button.width()
            >= window.cancel_button.sizeHint().width()
        )
        window._render_action_status()
        status_lines = window.action_status_label.text().splitlines()
        assert len(status_lines) == 2
        assert window.action_status_label.minimumHeight() >= (
            line_height * 2 + 8
        )
        assert long_name in window.action_status_label.toolTip()
        for line in status_lines:
            assert (
                window.action_status_label.fontMetrics().horizontalAdvance(
                    line
                )
                <= window.action_status_label.contentsRect().width()
            )

        window._worker_thread = None
        window._task_context = None
        window._update_action_availability()
        window.advanced_button.click()
        qtbot.waitUntil(window.advanced_dialog.isVisible)
        assert window._regex_single_column
        assert window.advanced_dialog.minimumWidth() >= 720
        assert window.advanced_dialog.minimumHeight() >= 360
        window.advanced_mode_box.setCurrentIndex(1)
        qtbot.waitUntil(lambda: window.advanced_dialog.minimumHeight() >= 600)
        window.advanced_mode_box.setFocus()
        qtbot.waitUntil(window.advanced_mode_box.hasFocus)
        qtbot.keyClick(
            window.advanced_mode_box,
            QtCore.Qt.Key_Tab,
        )
        assert window.level0_box.hasFocus()
        for _ in range(16):
            if window.read_exist_dir_box.hasFocus():
                break
            qtbot.keyClick(
                window.advanced_dialog.focusWidget(),
                QtCore.Qt.Key_Tab,
            )
        assert window.read_exist_dir_box.hasFocus()
        qtbot.wait(10)
        option_rect = QtCore.QRect(
            window.read_exist_dir_box.mapTo(
                window.advanced_dialog,
                QtCore.QPoint(),
            ),
            window.read_exist_dir_box.size(),
        )
        assert window.advanced_dialog.rect().contains(option_rect)
    finally:
        window.advanced_dialog.close()
        window._worker_thread = None
        window._task_context = None
        window.pdf_path_edit.clear()
        window._mark_clean()
        qapp.setFont(original_font)
