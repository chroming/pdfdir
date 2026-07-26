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
from src.gui.main import BookmarkWorkerThread, Main


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    qtbot.addWidget(main_window)
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
    window.space_level_box.setChecked(True)

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


def test_translation_loader_finds_packaged_translation(window):
    loaded_paths = []

    class FakeTranslator:
        def load(self, path):
            loaded_paths.append(path)
            return path.endswith("src/language/en.qm")

    window.trans = FakeTranslator()

    assert window._load_translation("en") is True
    assert any(path.endswith("src/language/en.qm") for path in loaded_paths)


def test_translation_loader_warns_when_translation_is_missing(window):
    class MissingTranslator:
        @staticmethod
        def load(_path):
            return False

    window.trans = MissingTranslator()
    messages = _capture_alerts(window)

    window.to_english()

    assert messages == [("warn", "English translation file not found")]


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


def test_bookmark_worker_reports_success(monkeypatch, qapp):
    calls = []
    monkeypatch.setattr(
        main_module,
        "add_bookmark",
        lambda path, bookmarks, keep: (
            calls.append((path, bookmarks, keep)) or "/tmp/output.pdf"
        ),
    )
    results = []
    worker = BookmarkWorkerThread("input.pdf", {0: {"title": "A"}}, True)
    worker.result.connect(lambda *result: results.append(result))

    worker.run()

    assert calls == [("input.pdf", {0: {"title": "A"}}, True)]
    assert results == [(True, "/tmp/output.pdf Finished!")]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (PermissionError(), "Permission denied!"),
        (ValueError("Page number is out of range"), "Page number is out of range"),
        (RuntimeError(), "RuntimeError"),
    ],
)
def test_bookmark_worker_reports_errors(monkeypatch, qapp, error, expected):
    def fail_write(*_args):
        raise error

    monkeypatch.setattr(main_module, "add_bookmark", fail_write)
    results = []
    worker = BookmarkWorkerThread("input.pdf", {}, False)
    worker.result.connect(lambda *result: results.append(result))

    worker.run()

    assert results == [(False, expected)]


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
    assert messages[-1][0] == "info"
    assert window.export_button.isEnabled()
    assert window.statusbar.currentMessage() == "Done"


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


def test_background_failure_restores_controls(window, qtbot, monkeypatch):
    def fail_write(*_args):
        raise ValueError("invalid bookmark")

    monkeypatch.setattr(main_module, "add_bookmark", fail_write)
    messages = _capture_alerts(window)
    window.pdf_path_edit.setText("source.pdf")

    window.write_tree_to_pdf()
    qtbot.waitUntil(lambda: window._worker is None, timeout=5_000)

    assert messages == [("warn", "invalid bookmark")]
    assert window.export_button.isEnabled()


def test_second_export_is_ignored_while_worker_is_running(
    window, qtbot, monkeypatch
):
    release_worker = threading.Event()

    def blocked_write(*_args):
        release_worker.wait(timeout=5)
        return "/tmp/output.pdf"

    monkeypatch.setattr(main_module, "add_bookmark", blocked_write)
    _capture_alerts(window)
    window.pdf_path_edit.setText("source.pdf")

    try:
        window.write_tree_to_pdf()
        first_worker = window._worker
        assert first_worker is not None
        window.write_tree_to_pdf()
        assert window._worker is first_worker
    finally:
        release_worker.set()
        qtbot.waitUntil(lambda: window._worker is None, timeout=5_000)


def test_export_without_pdf_shows_warning(window):
    messages = _capture_alerts(window)

    window.write_tree_to_pdf()

    assert messages == [("warn", "Please select a PDF file first.")]
    assert window._worker is None


def test_invalid_tree_page_edit_preserves_export_controls(window):
    messages = _capture_alerts(window)
    window.pdf_path_edit.setText("source.pdf")
    window.dir_text_edit.setPlainText("Chapter 1")
    tree_item = window.dir_tree_widget.topLevelItem(0)
    tree_item.setText(2, "not-a-page")

    window.write_tree_to_pdf()

    assert messages == [("warn", "Page numbers must be integers.")]
    assert tree_item.text(2) == "not-a-page"
    assert window.export_button.isEnabled()
    assert window._worker is None


def test_close_is_ignored_while_worker_is_running(window):
    class RunningWorker:
        @staticmethod
        def isRunning():
            return True

    window._worker = RunningWorker()
    event = QtGui.QCloseEvent()

    window.closeEvent(event)

    assert not event.isAccepted()
    assert "Please wait" in window.statusbar.currentMessage()
    window._worker = None


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
        (window, "select PDF", "/tmp/default", "PDF (*.pdf)")
    ]


def test_file_dialog_loads_existing_bookmarks(window, tmp_path, monkeypatch):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.read_exist_dir_action.setChecked(True)

    def select_pdf(parent, caption, initial_dir, file_filter):
        assert parent is window
        assert caption == "select PDF"
        assert initial_dir == window.default_folder
        assert file_filter == "PDF (*.pdf)"
        return str(source_path), "PDF (*.pdf)"

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        select_pdf,
    )
    monkeypatch.setattr(
        window,
        "read_pdf_dir_text",
        lambda _path: "Chapter\x00 1",
    )

    window.open_button.click()

    assert window.pdf_path == str(source_path)
    assert window.default_folder == str(tmp_path)
    assert window.dir_text == "Chapter 1"
    assert window.space_level_box.isChecked()


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


def test_resource_path_prefers_frozen_bundle(tmp_path, monkeypatch):
    icon_path = tmp_path / "src" / "pdf.ico"
    icon_path.parent.mkdir()
    icon_path.write_bytes(b"icon")
    monkeypatch.setattr(main_module.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert Main._resource_path("pdf.ico") == icon_path


@pytest.mark.parametrize("value", ["", "not a number", "--1"])
def test_invalid_offset_defaults_to_zero(window, value):
    window.offset_edit.setText(value)
    assert window.offset_num == 0


@pytest.mark.parametrize("level", range(6))
def test_level_checkbox_click_toggles_matching_editor(window, level):
    checkbox = getattr(window, f"level{level}_box")
    editor = getattr(window, f"level{level}_edit")

    assert not editor.isEnabled()
    checkbox.click()
    assert editor.isEnabled()
    checkbox.click()
    assert not editor.isEnabled()


def test_keep_existing_option_reaches_pdf_writer(window, qtbot, monkeypatch):
    calls = []

    def write_pdf(path, bookmarks, keep_existing):
        calls.append((path, bookmarks, keep_existing))
        return "source_new.pdf"

    monkeypatch.setattr(main_module, "add_bookmark", write_pdf)
    _capture_alerts(window)
    window.pdf_path_edit.setText("source.pdf")
    window.dir_text_edit.setPlainText("Chapter 1")
    window.keep_exist_dir_action.setChecked(True)

    window.export_button.click()
    qtbot.waitUntil(lambda: window._worker is None, timeout=5_000)

    assert calls[0][0] == "source.pdf"
    assert calls[0][2] is True


def test_language_menu_actions_switch_translation(window):
    assert window.export_button.text() == "写入"

    window.english_action.trigger()
    assert window.export_button.text() == "Write"

    window.chinese_action.trigger()
    assert window.export_button.text() == "写入"


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


@pytest.mark.parametrize(
    ("result", "expected_status", "opened"),
    [
        (True, "Find new version", True),
        (False, "No update", False),
    ],
)
def test_update_check_results(window, monkeypatch, result, expected_status, opened):
    opened_urls = []
    messages = _capture_alerts(window)
    monkeypatch.setattr(main_module, "is_updated", lambda *_args: result)
    monkeypatch.setattr(
        main_module.webbrowser,
        "open",
        lambda url, **_kwargs: opened_urls.append(url),
    )

    window.update_action.trigger()

    assert window.statusbar.currentMessage() == expected_status
    assert bool(opened_urls) is opened
    if not result:
        assert messages == [("info", "No update")]


def test_update_check_failure_is_reported(window, monkeypatch):
    messages = _capture_alerts(window)

    def fail_check(*_args):
        raise RuntimeError("network failure")

    monkeypatch.setattr(main_module, "is_updated", fail_check)

    window._open_update_page()

    assert messages == [("warn", "Check update failed")]
