import os
import re
import subprocess
import sys
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfReader, PdfWriter
from PySide6 import QtCore, QtGui, QtWidgets

import src.gui.main as main_module
from src.gui.main import Main
from tests.gui_test_utils import track_main_window


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, main_window)
    return main_window


def _capture_alerts(window):
    messages = []
    window.alert_msg = lambda message, level="info", **_kwargs: messages.append(
        (level, message)
    )
    return messages


def _write_blank_pdf(path, page_count=1):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def test_main_builds_nested_bookmark_tree(window):
    window.dir_text_edit.setPlainText("Chapter 1 1\n  Section 1 2")
    window.level_mode_box.setCurrentIndex(0)

    assert window.dir_tree_widget.topLevelItemCount() == 1
    assert window.tree_to_dict()[1]["parent"] == 0


@pytest.mark.parametrize(
    ("level", "title"),
    [
        (0, "1. Chapter"),
        (1, "1.1 Section"),
        (2, "1.1.1 Topic"),
    ],
)
def test_gui_default_level_patterns_match_numbered_titles(window, level, title):
    pattern = getattr(window, f"level{level}_edit").text()

    assert "\n" not in pattern
    assert re.match(pattern, title)


def test_importing_gui_module_does_not_replace_excepthook():
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "original = sys.excepthook; "
                "import src.gui.main; "
                "assert sys.excepthook is original"
            ),
        ],
        check=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )


def test_gui_window_starts_and_processes_event_loop():
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from PySide6 import QtCore, QtWidgets; "
                "from src.gui.main import Main; "
                "app = QtWidgets.QApplication([]); "
                "window = Main(app, QtCore.QTranslator()); "
                "window.show(); "
                "QtCore.QTimer.singleShot(50, app.quit); "
                "assert app.exec() == 0"
            ),
        ],
        check=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=10,
    )


def test_main_writes_pdf_in_background(window, qtbot, tmp_path):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source)
    messages = _capture_alerts(window)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Chapter One 1")
    window.export_button.click()
    assert window._worker is not None
    assert not window.export_button.isEnabled()
    qtbot.waitUntil(lambda: window._worker is None, timeout=15_000)

    assert (tmp_path / "source_new.pdf").exists()
    assert messages == []
    assert window.export_button.isEnabled()
    assert window.export_button.text() == "打开生成的 PDF"


def test_tree_edits_reach_generated_pdf(window, qtbot, tmp_path):
    source = tmp_path / "source.pdf"
    _write_blank_pdf(source, page_count=2)
    _capture_alerts(window)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Original 1")
    tree_item = window.dir_tree_widget.topLevelItem(0)
    tree_item.setText(0, "Edited title")
    tree_item.setText(1, "2")
    tree_item.setText(2, "2")

    window.export_button.click()
    qtbot.waitUntil(lambda: window._worker is None, timeout=15_000)

    reader = PdfReader(tmp_path / "source_new.pdf")
    assert reader.outline[0].title == "Edited title"
    assert reader.get_destination_page_number(reader.outline[0]) == 1


def test_offset_edit_rebuilds_preview_tree(window):
    window.dir_text_edit.setPlainText("Chapter 1")
    assert window.tree_to_dict()[0]["real_num"] == 1

    window.offset_edit.setText("3")

    assert window.tree_to_dict()[0]["real_num"] == 4


def test_export_without_pdf_shows_warning(window):
    messages = _capture_alerts(window)

    window.write_tree_to_pdf()

    assert messages and messages[0][0] == "warn"
    assert window._worker is None


def test_invalid_tree_page_edit_preserves_export_controls(window):
    messages = _capture_alerts(window)
    window.pdf_path_edit.setText("source.pdf")
    window.dir_text_edit.setPlainText("Chapter 1")
    tree_item = window.dir_tree_widget.topLevelItem(0)
    tree_item.setText(2, "not-a-page")

    window.write_tree_to_pdf()

    assert messages and "整数" in messages[0][1]
    assert tree_item.text(2) == "not-a-page"
    assert not window.export_button.isEnabled()
    assert window._worker is None


def test_cancelled_file_dialog_does_not_change_current_path(window, monkeypatch):
    calls = []
    window.pdf_path_edit.setText("existing.pdf")
    window.default_folder = "/tmp/default"

    def cancel_dialog(parent, caption, initial_dir, file_filter):
        calls.append((parent, caption, initial_dir, file_filter))
        return "", ""

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        cancel_dialog,
    )

    window.open_button.click()

    assert window.pdf_path == "existing.pdf"
    assert calls == [
        (window, window._t("select_pdf"), "/tmp/default", "PDF (*.pdf)")
    ]


def test_file_dialog_does_not_import_bookmarks_when_option_is_disabled(
    window, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.read_exist_dir_action.setChecked(False)

    def select_pdf(_parent, _caption, _initial_dir, _file_filter):
        return str(source_path), "PDF (*.pdf)"

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        select_pdf,
    )
    monkeypatch.setattr(
        window,
        "read_pdf_dir_text",
        lambda _path: "Existing bookmark 1",
    )

    window.open_button.click()

    assert window.pdf_path == str(source_path)
    assert window.dir_text.strip() == ""


@pytest.mark.parametrize("value", ["", "not a number", "--1"])
def test_invalid_offset_defaults_to_zero(window, value):
    window.offset_edit.setText(value)
    assert window.offset_num == 0


@pytest.mark.parametrize("level", range(6))
def test_level_checkbox_click_toggles_matching_editor(window, level):
    window.level_mode_box.setCurrentIndex(1)
    checkbox = getattr(window, f"level{level}_box")
    editor = getattr(window, f"level{level}_edit")

    assert not editor.isEnabled()
    checkbox.click()
    assert editor.isEnabled()
    checkbox.click()
    assert not editor.isEnabled()


def test_language_menu_actions_switch_translation(window):
    assert window.export_button.text() == "生成带书签的 PDF"

    window.english_action.trigger()
    assert window.export_button.text() == "Generate bookmarked PDF"

    window.chinese_action.trigger()
    assert window.export_button.text() == "生成带书签的 PDF"


def test_home_and_help_menu_actions_open_expected_urls(window, monkeypatch):
    opened = []

    def open_url(url, new):
        opened.append((url, new))
        return True

    monkeypatch.setattr(main_module.webbrowser, "open", open_url)

    window.home_page_action.trigger()
    window.help_action.trigger()

    assert opened == [
        (main_module.CONFIG.HOME_PAGE_URL, 1),
        (main_module.CONFIG.HELP_PAGE_URL, 1),
    ]
