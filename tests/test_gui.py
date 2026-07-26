import os
import subprocess
import sys
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfWriter
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
    window.make_dir_tree()

    assert window.dir_tree_widget.topLevelItemCount() == 1
    assert window.tree_to_dict()[1]["parent"] == 0


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
    window.make_dir_tree()

    window.write_tree_to_pdf()
    assert window._worker is not None
    assert not window.export_button.isEnabled()
    qtbot.waitUntil(lambda: window._worker is None, timeout=15_000)

    assert (tmp_path / "source_new.pdf").exists()
    assert messages[-1][0] == "info"
    assert window.export_button.isEnabled()
    assert window.statusbar.currentMessage() == "Done"


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
    window.pdf_path_edit.setText("existing.pdf")
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: ("", ""),
    )

    window.open_file_dialog()

    assert window.pdf_path == "existing.pdf"


def test_file_dialog_loads_existing_bookmarks(window, tmp_path, monkeypatch):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.read_exist_dir_action.setChecked(True)
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(source_path), "PDF (*.pdf)"),
    )
    monkeypatch.setattr(
        window,
        "read_pdf_dir_text",
        lambda _path: "Chapter\x00 1",
    )

    window.open_file_dialog()

    assert window.pdf_path == str(source_path)
    assert window.default_folder == str(tmp_path)
    assert window.dir_text == "Chapter 1"
    assert window.space_level_box.isChecked()


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

    window._open_update_page()

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
