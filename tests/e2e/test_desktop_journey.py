import pytest
from pypdf import PdfReader, PdfWriter
from PySide6 import QtCore, QtWidgets

from src.gui.main import Main


def _write_blank_pdf(path, page_count):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.mark.e2e
def test_user_opens_pdf_and_writes_nested_bookmarks(
    qtbot, qapp, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path, page_count=2)

    window = Main(qapp, QtCore.QTranslator())
    qtbot.addWidget(window)
    window.show()
    window.read_exist_dir_action.setChecked(False)

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args: (str(source_path), "PDF (*.pdf)"),
    )

    qtbot.mouseClick(
        window.open_button,
        QtCore.Qt.MouseButton.LeftButton,
    )
    assert window.pdf_path_edit.text() == str(source_path)

    if not window.space_level_box.isChecked():
        window.space_level_box.click()
    assert window.space_level_box.isChecked()
    qtbot.keyClicks(window.dir_text_edit, "Chapter One 1")
    qtbot.keyPress(
        window.dir_text_edit,
        QtCore.Qt.Key.Key_Return,
    )
    qtbot.keyClicks(window.dir_text_edit, "  Section One 2")

    assert window.dir_text_edit.toPlainText() == (
        "Chapter One 1\n  Section One 2"
    )
    qtbot.waitUntil(
        lambda: (
            window.dir_tree_widget.topLevelItemCount() == 1
            and window.dir_tree_widget.topLevelItem(0).childCount() == 1
        ),
        timeout=5_000,
    )

    messages = []

    def accept_visible_message_box():
        for widget in qapp.topLevelWidgets():
            if isinstance(widget, QtWidgets.QMessageBox) and widget.isVisible():
                messages.append(widget.text())
                widget.accept()

    message_box_timer = QtCore.QTimer(window)
    message_box_timer.setInterval(10)
    message_box_timer.timeout.connect(accept_visible_message_box)
    message_box_timer.start()

    qtbot.mouseClick(
        window.export_button,
        QtCore.Qt.MouseButton.LeftButton,
    )
    qtbot.waitUntil(
        lambda: output_path.exists() and window.export_button.isEnabled(),
        timeout=15_000,
    )
    message_box_timer.stop()

    reader = PdfReader(output_path)
    chapter = reader.outline[0]
    section = reader.outline[1][0]

    assert chapter.title == "Chapter One"
    assert reader.get_destination_page_number(chapter) == 0
    assert section.title == "Section One"
    assert reader.get_destination_page_number(section) == 1
    assert messages == [f"{output_path} Finished!"]
