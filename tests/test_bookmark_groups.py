"""No-target outline nodes must survive the full editable import path."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfReader, PdfWriter
from PySide6 import QtCore

from src.convert import convert_dir_text
from src.gui.main import Main
from src.pdf.bookmark import add_bookmark, check_bookmarks, get_bookmarks_strict
from src.pdf.pdf import Pdf
from tests.gui_test_utils import track_main_window


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "grouped.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    group = writer.add_outline_item("Book 2026", None)
    writer.add_outline_item("Introduction", 0, parent=group)
    nested = writer.add_outline_item("Part 2", None, parent=group)
    writer.add_outline_item("Chapter", 1, parent=nested)
    writer.add_outline_item("Appendix", 2)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_no_target_groups_round_trip_without_errors(source, caplog):
    original = source.read_bytes()
    lines = get_bookmarks_strict(str(source))
    assert not any("unsupported operand" in record.message for record in caplog.records)
    assert lines == [
        "Book 2026  —", " Introduction  1", " Part 2  —",
        "  Chapter  2", "Appendix  3",
    ]
    records = convert_dir_text(lines, level_by_space=True, fix_non_seq=False)
    assert records[0] == {"title": "Book 2026", "num": None, "real_num": None, "is_group": True}
    assert records[2]["parent"] == 0
    assert records[3]["parent"] == 2
    check_bookmarks(str(source), records)
    output = add_bookmark(str(source), records)
    assert Pdf._outline_specs(PdfReader(output)) == Pdf._outline_specs(PdfReader(source))
    assert source.read_bytes() == original


def test_group_does_not_inherit_or_advance_page_sequence():
    records = convert_dir_text("First 4\nGroup 2026  —\nUntitled page\nLast 6", offset=2)
    assert records[1]["title"] == "Group 2026"
    assert records[1]["real_num"] is None
    assert records[2]["real_num"] == 6
    assert records[3]["real_num"] == 8


def test_group_only_document_is_exportable(source):
    records = {0: {"title": "Group", "is_group": True, "real_num": None}}
    check_bookmarks(str(source), records)
    output = add_bookmark(str(source), records)
    assert Pdf._outline_specs(PdfReader(output)) == [("Group", None, None)]


@pytest.mark.parametrize("page", [1, "1", True])
def test_group_with_a_page_is_rejected(source, page):
    records = {0: {"title": "Group", "is_group": True, "real_num": page}}
    with pytest.raises(ValueError, match="must not have a page"):
        check_bookmarks(str(source), records)
    with pytest.raises(ValueError, match="must not have a page"):
        add_bookmark(str(source), records)


def test_gui_open_reads_pdf_once_and_preserves_groups(source, qtbot, qapp, monkeypatch):
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    monkeypatch.setattr(window, "_prompt_import_bookmarks", lambda _draft: True)
    window.read_exist_dir_box.setChecked(True)
    import src.pdf.pdf as pdf_module
    import src.gui.main as main_module
    reads = []

    def reader(*args, **kwargs):
        reads.append(args[0])
        return PdfReader(*args, **kwargs)

    monkeypatch.setattr(pdf_module, "PdfReader", reader)
    monkeypatch.setattr(main_module, "PdfReader", reader)
    assert window._activate_document(str(source))
    assert len(reads) == 1
    assert window._document_page_count == 3
    assert window._preview_item_count() == 5
    assert not window._validate_preview_tree()
    assert window.export_button.isEnabled()
    assert window._generation_signature() is not None
    tree = window.dir_tree_widget
    group = tree.topLevelItem(0)
    assert group.text(1) == group.text(2) == "—"
    assert "不跳转" in group.toolTip(2)
    window.to_english()
    assert "without a page" in group.toolTip(2)
    window.to_chinese()
    group.setText(0, "Renamed group")
    window.offset_edit.setText("1")
    assert window.tree_to_dict()[0]["real_num"] is None
    assert window.tree_to_dict()[1]["real_num"] == 2
    tree.undo()
    assert tree.topLevelItem(0).text(0) == "Book 2026"
    assert window.tree_to_dict()[0]["is_group"]
    tree.redo()
    assert tree.topLevelItem(0).text(0) == "Renamed group"
    tree.topLevelItem(0).setText(2, "invalid")
    assert window._validate_preview_tree()
    assert not window.export_button.isEnabled()


@pytest.mark.e2e
def test_group_import_edit_export_through_worker(source, qtbot, qapp, monkeypatch):
    original = source.read_bytes()
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.show()
    window.read_exist_dir_box.setChecked(True)
    monkeypatch.setattr(window, "_prompt_import_bookmarks", lambda _draft: True)
    assert window._activate_document(str(source))
    window.dir_tree_widget.topLevelItem(0).setText(0, "Renamed group")
    output = source.with_name("grouped_new.pdf")
    qtbot.mouseClick(window.export_button, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: output.exists() and window._worker_thread is None, timeout=15000)
    expected = Pdf._outline_specs(PdfReader(source))
    expected[0] = ("Renamed group", None, None)
    assert Pdf._outline_specs(PdfReader(output)) == expected
    assert window._generated_result_state() == "current"
    assert source.read_bytes() == original


def test_reopen_refreshes_page_count(source, qtbot, qapp, monkeypatch):
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.read_exist_dir_box.setChecked(False)
    assert window._activate_document(str(source))
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as stream:
        writer.write(stream)
    assert window._activate_document(str(source))
    assert window._document_page_count == 1
    assert "1 页" in window.document_name_label.accessibleDescription()
