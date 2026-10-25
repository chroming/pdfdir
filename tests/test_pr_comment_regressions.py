"""Exercise review findings at their actual GUI and PDF call sites."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtGui
from pypdf import PdfReader, PdfWriter

from src.convert import convert_dir_text
from src.gui.main import Main
from src.pdf.bookmark import add_bookmark
from src.pdf.pdf import Pdf
from tests.gui_test_utils import track_main_window


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(5):
        writer.add_blank_page(width=72, height=72)
    writer.add_outline_item("Existing", 0)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


@pytest.fixture
def window(qtbot, qapp, source):
    widget = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, widget)
    widget.read_exist_dir_box.setChecked(False)
    assert widget._activate_document(str(source))
    widget.dir_text_edit.setPlainText("First 1\nSecond 3")
    widget.show()
    return widget


def test_converter_default_does_not_clamp_reset_page_numbers():
    assert [v["real_num"] for v in convert_dir_text("Preface 4\nChapter 1").values()] == [4, 1]


def test_group_record_may_omit_page(source):
    output = add_bookmark(str(source), {0: {"title": "Group", "is_group": True}})
    assert Pdf._outline_specs(PdfReader(output)) == [("Group", None, None)]


def test_copy_reader_keep_outline_contract(source):
    for keep in (False, True):
        writer = Pdf.copy_reader_to_writer(PdfReader(source), PdfWriter(), keep_outline=keep)
        assert ("/Outlines" in writer._root_object) is keep


def test_invalid_offset_disables_export_without_losing_tree(window):
    before = window.tree_to_dict()
    assert window.export_button.isEnabled()
    window.offset_edit.setText("-")
    assert not window.export_button.isEnabled()
    assert window.tree_to_dict() == before
    window.offset_edit.setText("0")
    assert window.export_button.isEnabled()


def test_shortcuts_do_not_remove_bookmarks_from_source_editor(window, qtbot):
    tree = window.dir_tree_widget
    tree.setCurrentItem(tree.topLevelItem(0))
    window.dir_text_edit.setFocus()
    cursor = window.dir_text_edit.textCursor()
    cursor.movePosition(QtGui.QTextCursor.End)
    window.dir_text_edit.setTextCursor(cursor)
    qtbot.keyClick(window.dir_text_edit, QtCore.Qt.Key_Backspace)
    assert window.dir_text_edit.toPlainText().endswith("Second ")
    assert window._preview_item_count() == 2
    assert window.open_button.shortcut() == QtGui.QKeySequence(QtGui.QKeySequence.Open)


def test_preserve_source_bookmarks_has_reachable_menu_action(window):
    assert window.keep_exist_dir_action in window.file_menu.actions()
    assert window.keep_exist_dir_action.isVisible()
    window.keep_exist_dir_action.trigger()
    assert window.keep_exist_dir_box.isChecked() == window.keep_exist_dir_action.isChecked()


def test_unchanged_validation_does_not_rewrite_model(window):
    window._validate_preview_tree()
    changes = []
    window.dir_tree_widget.model().dataChanged.connect(lambda *args: changes.append(args))
    window._validate_preview_tree()
    assert not changes


def test_cleanup_failure_cannot_mask_export_error(source, monkeypatch):
    import src.pdf.pdf as pdf_module

    def broken_cleanup(_path):
        raise PermissionError("cleanup denied")

    with Pdf(str(source)) as pdf:
        monkeypatch.setattr(pdf, "_validate_candidate", lambda _reader: (_ for _ in ()).throw(ValueError("original failure")))
        monkeypatch.setattr(pdf_module.os, "remove", broken_cleanup)
        with pytest.raises(ValueError, match="original failure"):
            pdf.save_pdf()


def test_existing_output_is_rejected_without_hashing(source, monkeypatch):
    from src.pdf.pdf import OutputTargetChangedError
    source.with_name("source_new.pdf").write_bytes(b"do not read or replace")
    with Pdf(str(source)) as pdf:
        monkeypatch.setattr(pdf, "output_fingerprint", lambda _path: pytest.fail("unnecessary whole-file hash"))
        with pytest.raises(OutputTargetChangedError):
            pdf.save_pdf()


def test_output_helper_propagates_slot_assertions(window, qtbot):
    from tests.gui_test_utils import edit_output_settings

    def fail(_dialog):
        raise AssertionError("inspection failed")

    with pytest.raises(AssertionError, match="inspection failed"):
        edit_output_settings(window, qtbot, inspect=fail)


def test_output_helper_owns_folder_dialog(window, qtbot, tmp_path):
    from tests.gui_test_utils import edit_output_settings
    edit_output_settings(window, qtbot, folder=tmp_path, accept=False)


def test_missing_ocr_uses_exception_type_not_backend_words(window):
    from src.pdf.page_offset import OcrUnavailableError
    assert window._friendly_recognition_error(OcrUnavailableError("arbitrary localized details")) == window._t("ocr_unavailable")
    assert window._friendly_recognition_error(ValueError("tesseract is in this title")) == "tesseract is in this title"


def test_unreadable_programmatic_pdf_path_blocks_export(window, tmp_path, caplog):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    window.pdf_path_edit.setText(str(broken))
    window.dir_text_edit.setPlainText("Chapter 1")
    assert window._document_info_error
    assert not window.export_button.isEnabled()
    assert "Could not read PDF page count" in caplog.text


def test_comparison_rows_follow_each_source_lines_actual_font(window, qtbot):
    import math
    editor = window.dir_text_edit
    editor.setPlainText("First 1\nSecond 2\nThird 3")
    cursor = editor.textCursor()
    cursor.movePosition(QtGui.QTextCursor.Start)
    cursor.select(QtGui.QTextCursor.BlockUnderCursor)
    text_format = QtGui.QTextCharFormat()
    text_format.setFontPointSize(24)
    cursor.mergeCharFormat(text_format)
    heights = [math.ceil(editor.blockBoundingRect(editor.document().findBlockByNumber(i)).height())
               for i in range(3)]
    assert len(set(heights)) > 1  # Exercise the same mixed-metric shape as CJK fallback.
    qtbot.waitUntil(lambda: [window.dir_tree_widget.visualItemRect(item).height()
                            for item in window.dir_tree_widget.all_items] == heights)

