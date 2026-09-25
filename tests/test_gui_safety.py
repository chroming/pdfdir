import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfWriter
from PySide6 import QtCore
from PySide6 import QtWidgets

from src.gui.main import Main
from tests.gui_test_utils import track_main_window


def _write_blank_pdf(path, page_count=1):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def _write_pdf_with_bookmark(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_outline_item("Existing bookmark", 0)
    with path.open("wb") as handle:
        writer.write(handle)


def _dismiss_message_boxes(qapp, parent):
    messages = []

    def dismiss():
        for widget in qapp.topLevelWidgets():
            if (
                isinstance(widget, QtWidgets.QMessageBox)
                and widget.isVisible()
                and widget.parent() is parent
            ):
                messages.append(widget.text())
                widget.accept()

    timer = QtCore.QTimer(parent)
    timer.setInterval(10)
    timer.timeout.connect(dismiss)
    timer.start()
    return timer, messages


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    return track_main_window(qtbot, qapp, main_window)


def test_generate_is_disabled_until_pdf_and_bookmarks_are_ready(window, tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    assert not window.export_button.isEnabled()

    window.pdf_path_edit.setText(str(source_path))
    assert not window.export_button.isEnabled()

    window.dir_text_edit.setPlainText("Chapter 1")
    assert window.export_button.isEnabled()


def test_generate_stays_disabled_for_missing_pdf(window, tmp_path):
    window.pdf_path_edit.setText(str(tmp_path / "missing.pdf"))
    window.dir_text_edit.setPlainText("Chapter 1")

    assert not window.export_button.isEnabled()


def test_out_of_range_preview_does_not_write_pdf(window, qapp, tmp_path):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path, page_count=2)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Chapter 999")
    timer, messages = _dismiss_message_boxes(qapp, window)

    window.export_button.click()
    qapp.processEvents()
    timer.stop()

    assert not output_path.exists()
    assert messages == [
        "书签页码 999 超出 PDF 总页数 2，请在预览中修正"
    ]


def test_cancelled_file_picker_preserves_current_work(window, tmp_path, monkeypatch):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Unsaved draft 1")
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: ("", ""),
    )

    window.open_button.click()

    assert window.pdf_path_edit.text() == str(source_path)
    assert window.dir_text_edit.toPlainText() == "Unsaved draft 1"


def test_opening_bookmarked_pdf_does_not_replace_draft_without_confirmation(
    window, qapp, tmp_path, monkeypatch
):
    source_path = tmp_path / "bookmarked.pdf"
    _write_pdf_with_bookmark(source_path)
    window.dir_text_edit.setPlainText("Unsaved draft 1")
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(source_path), "PDF (*.pdf)"),
    )

    def reject_import():
        for widget in qapp.topLevelWidgets():
            if (
                isinstance(widget, QtWidgets.QMessageBox)
                and widget.isVisible()
                and widget.parent() is window
            ):
                widget.done(QtWidgets.QMessageBox.No)

    timer = QtCore.QTimer(window)
    timer.setInterval(10)
    timer.timeout.connect(reject_import)
    timer.start()
    window.open_button.click()
    timer.stop()

    assert window.pdf_path_edit.text() == str(source_path)
    assert window.dir_text_edit.toPlainText() == "Unsaved draft 1"


def test_existing_output_selects_a_new_numbered_target(window, tmp_path):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    output_path.write_bytes(b"existing output")
    window.pdf_path_edit.setText(str(source_path))

    assert output_path.read_bytes() == b"existing output"
    assert window.output_path_edit.text() == str(
        tmp_path / "source_new_2.pdf"
    )
