import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfReader, PdfWriter
from PySide6 import QtCore, QtWidgets

from src.gui.main import Main
from tests.gui_test_utils import track_main_window


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
    assert window.output_path_edit.text() == str(output_path)

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
    assert "已生成" in window.action_status_label.text()
    assert window.export_button.text() == "打开生成的 PDF"
