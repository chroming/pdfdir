import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfReader, PdfWriter
from PySide6 import QtCore, QtWidgets

from src.gui.main import Main
from tests.gui_test_utils import track_main_window, edit_output_settings


def _write_blank_pdf(path, page_count):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.mark.e2e
def test_user_opens_pdf_previews_hierarchy_and_generates_bookmarks(
    qtbot, qapp, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path, page_count=2)

    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.show()
    window.read_exist_dir_box.setChecked(False)
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(source_path), "PDF (*.pdf)"),
    )

    window.open_button.click()
    assert window.pdf_path_edit.text() == str(source_path)
    assert os.path.normcase(os.path.normpath(window.output_path_edit.text())) == os.path.normcase(str(output_path))

    window.dir_text_edit.setFocus()
    qtbot.keyClicks(window.dir_text_edit, "Chapter One 1")
    qtbot.keyPress(window.dir_text_edit, QtCore.Qt.Key_Return)
    qtbot.keyClicks(window.dir_text_edit, "  Section One 2")

    qtbot.waitUntil(
        lambda: (
            window.dir_tree_widget.topLevelItemCount() == 1
            and window.dir_tree_widget.topLevelItem(0).childCount() == 1
        ),
        timeout=5_000,
    )
    assert window.export_button.isEnabled()
    window.dir_tree_widget.topLevelItem(0).setText(
        0,
        "Chapter One corrected",
    )

    window.export_button.click()
    qtbot.waitUntil(
        lambda: output_path.exists() and window._worker_thread is None,
        timeout=15_000,
    )

    reader = PdfReader(output_path)
    chapter = reader.outline[0]
    section = reader.outline[1][0]
    assert chapter.title == "Chapter One corrected"
    assert reader.get_destination_page_number(chapter) == 0
    assert section.title == "Section One"
    assert reader.get_destination_page_number(section) == 1
    assert window.output_path_edit.text() == str(output_path)
    assert "已生成" in window.action_status_label.accessibleDescription()
    assert window.export_button.text() == "打开生成的 PDF"


@pytest.mark.e2e
def test_user_can_choose_output_folder_and_filename(qtbot, qapp, tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "results"
    destination.mkdir()
    output = destination / "reviewed.pdf"
    _write_blank_pdf(source, page_count=2)

    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.show()
    assert window._activate_document(str(source))
    window.dir_text_edit.setPlainText("Chapter 1")
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getExistingDirectory",
        lambda *_args, **_kwargs: str(destination),
    )
    edit_output_settings(window, qtbot, name="reviewed.pdf", folder=str(destination))

    assert os.path.normcase(os.path.normpath(window.output_path_edit.text())) == os.path.normcase(str(output))
    window.export_button.click()
    qtbot.waitUntil(
        lambda: output.exists() and window._worker_thread is None,
        timeout=15_000,
    )
    assert PdfReader(output).outline[0].title == "Chapter"
    assert not (tmp_path / "source_new.pdf").exists()
    assert window.export_button.text() == "打开生成的 PDF"


@pytest.mark.e2e
def test_external_result_replacement_never_opens_or_overwrites_it(
    qtbot, qapp, tmp_path
):
    source = tmp_path / "source.pdf"
    output = tmp_path / "source_new.pdf"
    next_output = tmp_path / "source_new_2.pdf"
    _write_blank_pdf(source, page_count=2)
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.show()
    assert window._activate_document(str(source))
    window.dir_text_edit.setPlainText("Chapter 1")
    window.export_button.click()
    qtbot.waitUntil(
        lambda: output.exists() and window._worker_thread is None,
        timeout=15_000,
    )

    _write_blank_pdf(output, page_count=3)
    qtbot.waitUntil(lambda: not window._last_generated_path, timeout=3_000)

    assert not window.open_result_action.isEnabled()
    assert window.export_button.text() == "生成 PDF"
    assert window.output_path_edit.text() == str(next_output)
    assert "外部修改" in window.action_status_label.accessibleDescription()
    window.export_button.click()
    qtbot.waitUntil(
        lambda: next_output.exists() and window._worker_thread is None,
        timeout=15_000,
    )
    assert len(PdfReader(output).pages) == 3
    assert PdfReader(next_output).outline[0].title == "Chapter"


@pytest.mark.e2e
def test_user_multiselects_deletes_undoes_and_exports_remaining_bookmarks(qtbot, qapp, tmp_path):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source, page_count=3)
    original = source.read_bytes()
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.show()
    window.read_exist_dir_box.setChecked(False)
    assert window._activate_document(str(source))
    window.dir_text_edit.setPlainText("Chapter 1\n  Section 1\nKeep 2\nRemove 3")
    tree = window.dir_tree_widget
    parent, removed = tree.topLevelItem(0), tree.topLevelItem(2)
    child = parent.child(0)
    parent.setExpanded(True)
    qtbot.wait(40)
    before = window._tree_snapshot()
    qtbot.mouseClick(tree.viewport(), QtCore.Qt.LeftButton, pos=tree.visualItemRect(parent).center())
    for item in (child, removed):
        qtbot.mouseClick(tree.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.ControlModifier,
                         tree.visualItemRect(item).center())
    assert len(tree.selectedItems()) == 3
    assert not tree.can_move_current_level(1)
    capture_dir = os.environ.get("PDFDIR_UI_CAPTURE_DIR")
    if capture_dir:
        Path(capture_dir).mkdir(parents=True, exist_ok=True)
        window.grab().save(str(Path(capture_dir) / "multi-selection.png"))
    qtbot.keyClick(tree, QtCore.Qt.Key_Delete)
    assert tree.topLevelItemCount() == 1
    assert tree.topLevelItem(0).text(0) == "Keep"
    assert window._preview_manually_adjusted
    window.undo_button.click()
    assert window._tree_snapshot() == before
    window.redo_button.click()
    assert tree.topLevelItemCount() == 1
    window.export_button.click()
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=15000)
    outline = PdfReader(window.output_path_edit.text()).outline
    assert len(outline) == 1
    assert outline[0].title == "Keep"
    assert source.read_bytes() == original
