"""The bookmark draft owns output; source and PDF are its reference views."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfReader, PdfWriter
from PySide6 import QtCore, QtGui, QtWidgets

from src.gui.main import Main
from src.gui.controls import MenuButton, ViewTabs
from src.gui.base import SOURCE_ROLE
from tests.gui_test_utils import track_main_window


@pytest.fixture
def window(qtbot, qapp, tmp_path):
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    path = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(12):
        writer.add_blank_page(width=300, height=400)
    writer.write(path)
    window.pdf_path_edit.setText(str(path))
    window.dir_text_edit.setPlainText("Chapter 1\n  Section 2\nNext 3")
    window.show()
    return window


def test_source_edits_preserve_manual_bookmarks_until_explicit_rebuild(window):
    tree = window.dir_tree_widget
    original = window.dir_text
    tree.topLevelItem(0).setText(0, "Corrected")
    snapshot = tree._snapshot()
    history = list(tree._history)
    window.dir_text_edit.appendPlainText("Appendix 4")
    assert tree._snapshot() == snapshot
    assert window._rule_guarded
    assert window.guard_panel.isVisible()
    assert not window.export_button.isEnabled()
    assert not window.advanced_button.isChecked()
    window.rules_accept_button.click()
    assert not window._rule_guarded
    assert tree.topLevelItemCount() == 3
    assert window.export_button.isEnabled()
    assert window.source_restore_button.isVisible()
    window.source_restore_button.click()
    assert window.dir_text == original
    assert tree._snapshot() == snapshot
    assert tree._history == history
    assert window._preview_manually_adjusted
    assert not window.guard_panel.isVisible()


def test_discard_pending_source_edit_restores_exact_previous_text(window):
    window.dir_tree_widget.topLevelItem(0).setText(0, "Corrected")
    original = window.dir_text
    window.dir_text_edit.setPlainText("Replacement 5")
    window.dir_text_edit.appendPlainText("More 6")
    window.source_restore_button.click()
    assert window.dir_text == original
    assert window.dir_tree_widget.topLevelItem(0).text(0) == "Corrected"


def test_manual_edits_during_pending_rebuild_remain_recoverable(window):
    item = window.dir_tree_widget.topLevelItem(0)
    item.setText(0, "Corrected")
    window.dir_text_edit.appendPlainText("Appendix 4")
    item.setText(0, "Second correction")
    window.rules_accept_button.click()
    window.source_restore_button.click()
    assert window.dir_tree_widget.topLevelItem(0).text(0) == "Second correction"


def test_unmodified_source_still_updates_live(window):
    window.dir_text_edit.appendPlainText("Appendix 4")
    assert window.dir_tree_widget.topLevelItemCount() == 3
    assert not window._rules_pending


def test_reference_switch_preserves_draft_and_follows_physical_page(window):
    before = window._current_draft_signature()
    source = Path(window.pdf_path).read_bytes()
    window.offset_edit.setText("2")
    before = window._current_draft_signature()
    item = window.dir_tree_widget.topLevelItem(0).child(0)
    window.dir_tree_widget.setCurrentItem(item)
    window.source_tabs.setCurrentIndex(1)
    assert window.pdf_reference.page_count == 12
    assert window.pdf_reference.current_page == 4
    window.source_tabs.setCurrentIndex(0)
    assert window._current_draft_signature() == before
    assert Path(window.pdf_path).read_bytes() == source


def test_preview_groups_and_out_of_range_do_not_show_unrelated_page(window):
    window.source_tabs.setCurrentIndex(1)
    window.dir_text_edit.setPlainText("Group  —\n  Section 2\nOutside 20")
    tree = window.dir_tree_widget
    tree.setCurrentItem(tree.topLevelItem(0))
    assert window.pdf_reference._message == "group"
    tree.setCurrentItem(tree.topLevelItem(1))
    assert window.pdf_reference._message == "range"
    tree.setCurrentItem(tree.topLevelItem(0).child(0))
    assert window.pdf_reference.current_page == 2
    assert window.pdf_reference.stack.currentWidget() is window.pdf_reference.view


def test_switch_pdf_and_failed_load_clear_old_reference(window, tmp_path):
    window.source_tabs.setCurrentIndex(1)
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"invalid PDF")
    window.pdf_reference.set_source(str(broken))
    assert not window.pdf_reference._ready
    assert window.pdf_reference._message == "error"
    assert window.pdf_reference.stack.currentWidget() is window.pdf_reference.message_label
    window.pdf_reference.set_source("")
    assert window.pdf_reference._message == "empty"
    window.pdf_reference.set_source(window.pdf_path)
    assert window.pdf_reference.page_count == 12


def test_pdf_module_unavailable_does_not_disable_bookmark_editor(window, monkeypatch):
    from src.gui import pdf_reference
    monkeypatch.setattr(pdf_reference, "QPdfDocument", None)
    monkeypatch.setattr(pdf_reference, "QPdfView", None)
    pane = pdf_reference.PdfReferencePane(window)
    pane.set_source(window.pdf_path)
    assert pane._message == "unavailable"
    assert window.export_button.isEnabled()


def test_calibration_preserves_manual_titles_and_rejects_invalid_pages(window):
    tree = window.dir_tree_widget
    tree.topLevelItem(0).setText(0, "Corrected")
    window.calibrate_button.click()
    assert window.source_tabs.currentIndex() == 1
    window.printed_anchor.setText("1")
    window.pdf_anchor.setText("9")
    window.calibration_apply_button.click()
    assert window.offset_num == 8
    assert tree.topLevelItem(0).text(0) == "Corrected"
    assert tree.topLevelItem(0).text(2) == "9"
    assert window.pdf_reference.current_page == 9
    window.pdf_anchor.setText("13")
    assert not window.calibration_apply_button.isEnabled()
    assert window.calibration_error.isVisible()
    assert window.offset_num == 8
    window.pdf_anchor.setText("")
    assert not window.calibration_apply_button.isEnabled()
    window.printed_anchor.setText("3")
    window.pdf_anchor.setText("1")
    window.calibration_apply_button.click()
    assert window.offset_num == -2


def test_pdf_navigation_fills_calibration_target(window):
    window.calibrate_button.click()
    window.pdf_reference.go_to_page(8)
    assert window.pdf_anchor.text() == "8"


def test_editing_selected_destination_refreshes_pdf_reference(window):
    tree = window.dir_tree_widget
    tree.setCurrentItem(tree.topLevelItem(0))
    window.source_tabs.setCurrentIndex(1)
    tree.currentItem().setText(2, "4")
    assert window.pdf_reference.current_page == 4


def test_calibration_escape_returns_focus_without_changing_offset(window, qtbot):
    window.calibrate_button.click()
    window.pdf_anchor.setText("9")
    window.pdf_anchor.setFocus()
    qtbot.keyClick(window.pdf_anchor, QtCore.Qt.Key_Escape)
    assert not window.calibration_panel.isVisible()
    assert window.calibrate_button.hasFocus()
    assert window.offset_num == 0


def test_large_text_calibration_never_clips_its_fields(window, qapp, qtbot):
    original = qapp.font()
    font = QtGui.QFont(original)
    font.setPointSize(24)
    try:
        qapp.setFont(font)
        window.to_english()
        window.resize(window.minimumSize())
        window.dir_tree_widget.topLevelItem(0).setText(0, "Corrected")
        window.dir_text_edit.appendPlainText("Appendix 4")
        window.rules_accept_button.click()
        window.calibrate_button.click()
        qtbot.wait(30)
        for control in (window.printed_anchor, window.pdf_anchor, window.calibration_apply_button,
                        window.offset_edit, window.auto_offset_button):
            rect = QtCore.QRect(control.mapTo(window.calibration_panel, QtCore.QPoint()), control.size())
            assert window.calibration_panel.rect().contains(rect), (control, rect)
            assert control.height() >= control.sizeHint().height()
        assert window.dir_tree_widget.viewport().height() >= window.fontMetrics().height() * 2
    finally:
        qapp.setFont(original)


def test_hierarchy_move_preserves_subtree_source_and_undo(window):
    tree = window.dir_tree_widget
    item = tree.topLevelItem(1)
    source = item.data(0, SOURCE_ROLE)
    tree.setCurrentItem(item)
    initial = tree._snapshot()
    tree.move_current_level(1)
    assert item.parent() is tree.topLevelItem(0)
    assert item.data(0, SOURCE_ROLE) == source
    tree.move_current_level(-1)
    assert tree._snapshot() == initial
    tree.undo()
    assert tree.topLevelItemCount() == 1
    tree.undo()
    assert tree._snapshot() == initial


def test_final_bookmark_hierarchy_and_calibration_reach_export(window, qtbot):
    tree = window.dir_tree_widget
    tree.setCurrentItem(tree.topLevelItem(1))
    tree.move_current_level(1)
    window.offset_edit.setText("2")
    source = Path(window.pdf_path).read_bytes()
    window.export_button.click()
    qtbot.waitUntil(lambda: window._worker is None, timeout=15000)
    result = PdfReader(window.output_path_edit.text())
    assert result.get_destination_page_number(result.outline[0]) == 2
    assert len(result.outline[1]) == 2
    assert Path(window.pdf_path).read_bytes() == source


def test_explicit_rule_add_and_preferences_are_separate(window):
    window.level_mode_box.setCurrentIndex(1)
    window.advanced_button.click()
    assert not window.level0_edit.isVisible()
    window._add_rule_level(0)
    assert window.level0_edit.isVisible()
    assert window.level0_edit.isEnabled()
    window.rules_options_button.click()
    assert not window.level5_edit.isVisible()
    assert not window.read_exist_dir_box.isVisible()
    assert window.read_exist_dir_action in window.file_menu.actions()


def test_ambiguous_source_preserves_tree_and_blocks_even_after_manual_edit(window):
    tree = window.dir_tree_widget
    before = tree._snapshot()
    window.dir_text_edit.setPlainText("\nPreface iii\nChapter 1")
    assert tree._snapshot() == before
    assert not window.export_button.isEnabled()
    assert "第 2 行" in window._validate_preview_tree()
    tree.topLevelItem(0).setText(0, "Manual correction")
    assert not window.export_button.isEnabled()
    window.to_english()
    assert "Roman" in window._validate_preview_tree()


def test_source_error_recovers_when_corrected(window):
    window.dir_text_edit.setPlainText("Preface iii")
    assert not window.export_button.isEnabled()
    window.dir_text_edit.setPlainText("Preface 3")
    assert window.export_button.isEnabled()
    assert window.dir_tree_widget.topLevelItem(0).text(2) == "3"


def test_stale_tree_does_not_jump_to_an_unrelated_source_line(window):
    window.dir_text_edit.setPlainText("Preface iii\n\nCompletely different source")
    cursor = window.dir_text_edit.textCursor()
    cursor.movePosition(QtGui.QTextCursor.End)
    window.dir_text_edit.setTextCursor(cursor)
    position = cursor.position()
    window.dir_tree_widget.setCurrentItem(window.dir_tree_widget.topLevelItem(1))
    assert window.dir_text_edit.textCursor().position() == position
    assert not window.dir_text_edit.extraSelections()


def test_invalid_parent_is_rejected_before_clearing_preview(window, monkeypatch):
    from src.gui import main
    before = window.dir_tree_widget._snapshot()
    monkeypatch.setattr(main, "convert_dir_text", lambda *a, **kw: {
        0: {"title": "Orphan", "real_num": 1, "parent": 99},
    })
    window.make_dir_tree()
    assert window.dir_tree_widget._snapshot() == before
    assert not window.export_button.isEnabled()


def test_explicit_null_parent_is_a_root_not_a_dropped_child(window, monkeypatch):
    from src.gui import main
    monkeypatch.setattr(main, "convert_dir_text", lambda *a, **kw: {
        0: {"title": "Root", "num": 1, "real_num": 1, "parent": None},
    })
    window.make_dir_tree()
    assert window.dir_tree_widget.topLevelItem(0).text(0) == "Root"
    assert window.export_button.isEnabled()


def test_hierarchy_shortcuts_preserve_tab_and_undo(window, qtbot):
    tree = window.dir_tree_widget
    tree.setCurrentItem(tree.topLevelItem(1))
    tree.setFocus()
    before = tree._snapshot()
    qtbot.keyClick(tree, QtCore.Qt.Key_Right, QtCore.Qt.AltModifier)
    assert tree.currentItem().parent() is tree.topLevelItem(0)
    qtbot.keyClick(tree, QtCore.Qt.Key_Left, QtCore.Qt.AltModifier)
    assert tree._snapshot() == before
    tree.undo()
    assert tree.topLevelItemCount() == 1
    qtbot.keyClick(tree, QtCore.Qt.Key_Tab)
    assert not tree.hasFocus()
    assert tree.topLevelItemCount() == 1


def test_hierarchy_shortcut_does_not_move_row_while_editing(window, qtbot):
    tree = window.dir_tree_widget
    tree.setCurrentItem(tree.topLevelItem(1))
    tree.editItem(tree.currentItem(), 0)
    editor = tree.findChild(QtWidgets.QLineEdit)
    assert editor is not None
    qtbot.keyClick(editor, QtCore.Qt.Key_Right, QtCore.Qt.AltModifier)
    assert tree.topLevelItemCount() == 2


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_text_import_is_one_undoable_edit_and_preserves_manual_tree(window, tmp_path, monkeypatch, encoding):
    path = tmp_path / "目录.txt"
    path.write_text("新目录 3\n  子章节 4", encoding=encoding)
    before = window.dir_text
    tree = window.dir_tree_widget
    tree.topLevelItem(0).setText(0, "Corrected")
    snapshot = tree._snapshot()
    monkeypatch.setattr(window, "_confirm_text_import", lambda: True)
    assert window._import_toc_file(str(path))
    assert window.dir_text == "新目录 3\n  子章节 4"
    assert tree._snapshot() == snapshot
    assert window._rule_guarded
    window.dir_text_edit.undo()
    assert window.dir_text == before
    window.source_restore_button.click()
    assert tree._snapshot() == snapshot


def test_cancelled_and_invalid_text_import_leave_draft_unchanged(window, tmp_path, monkeypatch):
    path = tmp_path / "toc.txt"
    before = window._current_draft_signature()
    path.write_text("Replacement 1", encoding="utf-8")
    monkeypatch.setattr(window, "_confirm_text_import", lambda: False)
    assert not window._import_toc_file(str(path))
    errors = []
    monkeypatch.setattr(window, "alert_msg", lambda message, **kw: errors.append(message))
    path.write_bytes(b"\xffinvalid")
    assert not window._import_toc_file(str(path))
    assert errors
    assert window._current_draft_signature() == before


def test_accepted_close_releases_pdf_and_allows_reload(window):
    window.source_tabs.setCurrentIndex(1)
    pane = window.pdf_reference
    assert pane.page_count == 12
    window._allow_close_once = True
    window.close()
    assert pane.document.pageCount() == 0
    assert pane._source_key is None
    assert not pane._ready
    window.show()
    assert pane.page_count == 12


def test_dirty_close_keeps_reference_loaded_until_confirmed(window, monkeypatch):
    window.source_tabs.setCurrentIndex(1)
    monkeypatch.setattr(window, "_show_dirty_close_prompt", lambda: None)
    window.close()
    assert window.isVisible()
    assert window.pdf_reference.page_count == 12


def test_text_file_drop_on_editor_loads_content_not_url(window, tmp_path, monkeypatch, qapp):
    path = tmp_path / "toc.txt"
    path.write_text("Dropped chapter 4", encoding="utf-8")
    monkeypatch.setattr(window, "_confirm_text_import", lambda: True)
    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl.fromLocalFile(str(path))])
    viewport = window.dir_text_edit.viewport()
    enter = QtGui.QDragEnterEvent(QtCore.QPoint(10, 10), QtCore.Qt.CopyAction,
                                 mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    qapp.sendEvent(viewport, enter)
    assert enter.isAccepted()
    drop = QtGui.QDropEvent(QtCore.QPointF(10, 10), QtCore.Qt.CopyAction,
                           mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    qapp.sendEvent(viewport, drop)
    assert drop.isAccepted()
    assert window.dir_text == "Dropped chapter 4"
    assert window.dir_tree_widget.topLevelItem(0).text(2) == "4"


def test_text_import_menu_and_busy_guard(window, tmp_path, monkeypatch):
    path = tmp_path / "toc.txt"
    path.write_text("Imported chapter 4", encoding="utf-8")
    monkeypatch.setattr(window, "_confirm_text_import", lambda: True)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        lambda *a, **kw: (str(path), "Text (*.txt)"))
    window.import_text_action.trigger()
    assert window.dir_text == "Imported chapter 4"
    monkeypatch.setattr(window, "_has_active_task", lambda: True)
    path.write_text("Busy replacement 5", encoding="utf-8")
    assert not window._import_toc_file(str(path))
    assert window.dir_text == "Imported chapter 4"
    monkeypatch.undo()


def test_failed_rebuild_keeps_manual_restore_point(window):
    tree = window.dir_tree_widget
    original = window.dir_text
    tree.topLevelItem(0).setText(0, "Manual correction")
    before = tree._snapshot()
    window.dir_text_edit.setPlainText("Preface iii")
    window.rules_accept_button.click()
    assert tree._snapshot() == before
    assert window._preview_manually_adjusted
    assert window._rule_guarded
    assert not window.export_button.isEnabled()
    window.source_restore_button.click()
    assert tree._snapshot() == before
    assert window.dir_text == original
    assert window.export_button.isEnabled()


def test_text_replacement_dialog_cancel_is_safe_default(window, qtbot):
    def reject_dialog():
        box = window.findChild(QtWidgets.QMessageBox)
        assert box.defaultButton() is box.escapeButton()
        qtbot.keyClick(box, QtCore.Qt.Key_Escape)
    QtCore.QTimer.singleShot(0, reject_dialog)
    assert not window._confirm_text_import()


def test_source_error_remains_readable_with_large_text(window, qapp, qtbot):
    original = qapp.font()
    font = QtGui.QFont(original)
    font.setPointSize(24)
    try:
        qapp.setFont(font)
        window.to_english()
        window.resize(window.minimumSize())
        window.dir_text_edit.setPlainText("Preface iii")
        qtbot.wait(50)
        label = window.source_error_label
        assert label.height() >= label.heightForWidth(label.width())
        assert window.dir_text_edit.viewport().height() >= 72
    finally:
        qapp.setFont(original)


def test_source_error_height_shrinks_again_after_widening(window, qtbot):
    window.to_english()
    window.resize(780, 560)
    window.dir_text_edit.setPlainText("Preface iii")
    qtbot.wait(30)
    initial = window.source_error_label.height()
    window.resize(1440, 900)
    qtbot.wait(30)
    label = window.source_error_label
    probe = QtWidgets.QLabel(window)
    probe.setFont(label.font())
    probe.setWordWrap(True)
    probe.setText(label.text())
    assert label.height() <= probe.heightForWidth(label.width()) + 2
    assert label.height() < initial


@pytest.mark.parametrize("english", [False, True])
@pytest.mark.parametrize("state", ["text", "pdf", "rules", "calibration", "guard"])
def test_reference_surfaces_fit_minimum_window(window, qtbot, english, state):
    if english:
        window.to_english()
    window.resize(780, 560)
    if state in ("pdf", "calibration"):
        window.source_tabs.setCurrentIndex(1)
    if state == "calibration":
        window.calibrate_button.click()
    if state == "rules":
        window.level_mode_box.setCurrentIndex(1)
        window._add_rule_level(0)
        window.advanced_button.click()
    if state == "guard":
        window.dir_tree_widget.topLevelItem(0).setText(0, "Corrected")
        window.dir_text_edit.appendPlainText("Appendix 4")
    qtbot.wait(20)
    assert isinstance(window.source_tabs, ViewTabs)
    assert isinstance(window.source_import_button, MenuButton)
    assert type(window.source_import_button) is type(window.hierarchy_button)
    controls = [window.dir_tree_widget, window.export_button, window.source_tabs,
                window.calibrate_button, window.hierarchy_button]
    if state == "calibration":
        controls += [window.calibration_apply_button, window.printed_anchor, window.pdf_anchor]
    if state == "guard":
        controls += [window.rules_accept_button, window.source_restore_button]
    for control in controls:
        rect = QtCore.QRect(control.mapTo(window, QtCore.QPoint()), control.size())
        assert window.rect().contains(rect), (state, control.objectName(), rect)
        assert control.isVisible()
    assert window.dir_tree_widget.viewport().height() >= 72
