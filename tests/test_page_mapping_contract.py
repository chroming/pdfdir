"""The displayed page formula must describe the actual exported destination."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore
from pypdf import PdfReader, PdfWriter

from src.gui.main import Main
from src.pdf.bookmark import add_bookmark
from tests.gui_test_utils import track_main_window


@pytest.fixture
def window(qtbot, qapp, tmp_path):
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    writer = PdfWriter()
    for _ in range(30):
        writer.add_blank_page(width=72, height=72)
    source = tmp_path / "source.pdf"
    writer.write(source)
    window.read_exist_dir_box.setChecked(False)
    window._activate_document(str(source))
    window.dir_text_edit.setPlainText("Chapter 1")
    window.offset_edit.setText("8")
    window.show()
    return window


def test_edit_either_page_column_maintains_formula_and_export(window):
    tree = window.dir_tree_widget
    item = tree.topLevelItem(0)
    item.setText(1, "3")
    assert item.text(2) == "11"
    item.setText(2, "15")
    assert item.text(1) == "7"
    tree.undo()
    assert tree.topLevelItem(0).text(2) == "11"
    tree.redo()
    window.offset_edit.setText("9")
    assert tree.topLevelItem(0).text(2) == "16"
    output = add_bookmark(window.pdf_path, window.tree_to_dict())
    reader = PdfReader(output)
    assert reader.get_destination_page_number(reader.outline[0]) == 15


def test_group_can_be_edited_to_a_destination_and_back(window):
    item = window.dir_tree_widget.topLevelItem(0)
    item.setText(1, "—")
    assert item.text(2) == "—"
    assert window.tree_to_dict()[0]["is_group"]
    item.setText(2, "12")
    assert item.text(1) == "4"
    assert not window.tree_to_dict()[0].get("is_group")


def test_validation_replaces_transient_feedback_immediately(window):
    window.show_status("Previous operation completed", 5000)
    window.dir_tree_widget.topLevelItem(0).setText(2, "999")
    assert "999" in window.action_status_label.toolTip()
    assert window.action_status_label.property("statusKind") == "error"


@pytest.mark.parametrize("language", ["zh", "en"])
def test_invalid_destination_is_inline_and_recovers_through_undo(window, language):
    if language == "en":
        window.to_english()
    tree = window.dir_tree_widget
    item = tree.topLevelItem(0)
    item.setText(2, "999")
    assert not window.export_button.isEnabled()
    assert "999" in window._validate_preview_tree()
    assert "30" in item.toolTip(2)
    assert item.foreground(2).style() != QtCore.Qt.NoBrush
    tree.undo()
    assert window.export_button.isEnabled()
    item = tree.topLevelItem(0)
    assert item.foreground(2).style() == QtCore.Qt.NoBrush
    window.offset_edit.setText("-8")
    assert not window.export_button.isEnabled()
    window.offset_edit.setText("0")
    assert window.export_button.isEnabled()


def test_import_is_atomic_and_preserves_original_targets(window, tmp_path, monkeypatch):
    writer = PdfWriter()
    for _ in range(30):
        writer.add_blank_page(width=72, height=72)
    group = writer.add_outline_item("Group", None)
    writer.add_outline_item("Later", 19, parent=group)
    writer.add_outline_item("Earlier", 1, parent=group)
    source = tmp_path / "bookmarks.pdf"
    writer.write(source)
    window.read_exist_dir_box.setChecked(True)
    window.fix_non_seq_box.setChecked(True)
    window.dir_tree_widget.topLevelItem(0).setText(0, "Manual edit")
    window.level_mode_box.setCurrentIndex(1)
    assert window._rule_guarded
    monkeypatch.setattr(window, "_prompt_document_switch", lambda: "keep")
    monkeypatch.setattr(window, "_prompt_import_bookmarks", lambda _draft: True)
    assert window._activate_document(str(source))
    records = window.tree_to_dict()
    assert [record["real_num"] for record in records.values()] == [None, 20, 2]
    assert window.offset_num == 0
    assert not window.fix_non_seq
    assert not window._is_dirty()
    assert not window._rules_pending
    output = add_bookmark(str(source), records)
    reader = PdfReader(output)
    assert [reader.get_destination_page_number(item) for item in reader.outline[1]] == [19, 1]
