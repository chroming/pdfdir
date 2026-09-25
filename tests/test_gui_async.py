import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfWriter
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

import src.gui.main as main_module
from src.gui.main import Main
from src.gui.main import TocTextWorker
from src.pdf.cancellation import OperationCancelled
from tests.gui_test_utils import track_main_window


def _write_blank_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    return track_main_window(qtbot, qapp, main_window)


def test_toc_result_does_not_replace_a_newer_document(
    window, qtbot, tmp_path, monkeypatch
):
    source_a = tmp_path / "a.pdf"
    source_b = tmp_path / "b.pdf"
    _write_blank_pdf(source_a)
    _write_blank_pdf(source_b)

    def read_toc(_path, **_kwargs):
        time.sleep(0.05)
        return "TOC from A 1"

    monkeypatch.setattr(main_module, "extract_toc_text", read_toc)
    window.pdf_path_edit.setText(str(source_a))
    window.dir_text_edit.setPlainText("Draft A 1")
    window.fill_toc_text()

    window.pdf_path_edit.setText(str(source_b))
    window.dir_text_edit.setPlainText("Draft B 1")
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)

    assert window.pdf_path_edit.text() == str(source_b)
    assert window.dir_text_edit.toPlainText() == "Draft B 1"


def test_offset_result_does_not_replace_a_newer_draft(
    window, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    def infer_offset(_path, _text, **_kwargs):
        time.sleep(0.05)
        return 8

    monkeypatch.setattr(main_module, "infer_page_offset", infer_offset)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Draft A 1")
    window.fill_offset()

    window.dir_text_edit.setPlainText("Draft B 1")
    window.offset_edit.setText("99")
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)

    assert window.offset_edit.text() == "99"
    assert window.dir_text_edit.toPlainText() == "Draft B 1"


def test_toc_result_does_not_replace_newer_draft_for_same_document(
    window, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    def read_toc(_path, **_kwargs):
        time.sleep(0.05)
        return "Old asynchronous result 1"

    monkeypatch.setattr(main_module, "extract_toc_text", read_toc)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Starting draft 1")
    window.fill_toc_text()

    window.dir_text_edit.setPlainText("New manual draft 1")
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)

    assert window.dir_text_edit.toPlainText() == "New manual draft 1"
    assert "丢弃" in window.statusbar.currentMessage()


def test_inferred_offset_uses_domain_value_without_second_conversion(
    window, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(30):
        writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as handle:
        writer.write(handle)

    monkeypatch.setattr(
        main_module,
        "infer_page_offset",
        lambda *_args, **_kwargs: 9,
    )
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Chapter 1  1\nChapter 2  20")

    window.fill_offset()
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)

    assert window.offset_edit.text() == "9"
    assert window.dir_tree_widget.topLevelItem(0).text(2) == "10"
    assert window.dir_tree_widget.topLevelItem(1).text(2) == "29"


def test_toc_failure_clears_working_state(
    window, qapp, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    def fail_read(_path, **_kwargs):
        raise RuntimeError("OCR dependency missing")

    monkeypatch.setattr(main_module, "extract_toc_text", fail_read)
    window.pdf_path_edit.setText(str(source_path))
    messages = []

    def dismiss_warning():
        for widget in qapp.topLevelWidgets():
            if (
                isinstance(widget, QtWidgets.QMessageBox)
                and widget.isVisible()
                and widget.parent() is window
            ):
                messages.append(widget.text())
                widget.accept()

    timer = QtCore.QTimer(window)
    timer.setInterval(10)
    timer.timeout.connect(dismiss_warning)
    timer.start()
    window.fill_toc_text()
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)
    timer.stop()

    assert "失败" in window.statusbar.currentMessage()
    assert window.auto_toc_button.isEnabled()
    assert messages == ["目录识别失败：OCR dependency missing"]


def test_toc_worker_exposes_cooperative_cancellation():
    worker = TocTextWorker("source.pdf")

    worker.cancel()

    assert worker.is_cancelled()


def test_worker_busy_guard_covers_thread_cleanup_gap(
    window, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.pdf_path_edit.setText(str(source_path))

    class FinishedThread:
        @staticmethod
        def isRunning():
            return False

    prior_thread = FinishedThread()
    window._worker_thread = prior_thread
    window._worker_busy = True
    messages = []
    monkeypatch.setattr(
        window,
        "alert_msg",
        lambda message, **_kwargs: messages.append(message),
    )

    window.fill_toc_text()

    assert window._worker_thread is prior_thread
    assert messages == [window._t("task_running")]

    window._background_task_finished()
    assert not window._worker_busy


def test_close_requests_cancellation_instead_of_destroying_running_thread(
    window,
):
    class RunningThread:
        @staticmethod
        def isRunning():
            return True

    class Worker:
        cancelled = False

        def cancel(self):
            self.cancelled = True

    worker = Worker()
    window._worker_thread = RunningThread()
    window._worker = worker
    window._allow_close_once = True
    event = QtGui.QCloseEvent()

    window.closeEvent(event)

    assert not event.isAccepted()
    assert worker.cancelled
    assert window._allow_close_once
    window._worker = None
    window._worker_thread = None
    window._worker_busy = False


def test_close_suppresses_update_result_until_thread_cleanup(
    window, qtbot, monkeypatch
):
    started = threading.Event()
    release = threading.Event()
    opened = []
    messages = []

    def delayed_check(_url, _version):
        started.set()
        release.wait(timeout=5)
        return "update"

    monkeypatch.setattr(main_module, "check_for_update", delayed_check)
    monkeypatch.setattr(
        main_module.webbrowser,
        "open",
        lambda url, **_kwargs: opened.append(url),
    )
    monkeypatch.setattr(
        window,
        "alert_msg",
        lambda message, **_kwargs: messages.append(message),
    )

    window.show()
    window._open_update_page()
    qtbot.waitUntil(started.is_set, timeout=5_000)

    window.close()

    assert window.isVisible()
    assert window._close_requested
    release.set()
    qtbot.waitUntil(lambda: window._update_thread is None, timeout=5_000)
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5_000)
    assert not opened
    assert not messages


def test_close_waits_for_update_and_document_task(
    window, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.pdf_path_edit.setText(str(source_path))

    update_started = threading.Event()
    update_release = threading.Event()
    task_started = threading.Event()

    def delayed_check(_url, _version):
        update_started.set()
        update_release.wait(timeout=5)
        return "current"

    def cancellable_read(_path, cancel_check=None, **_kwargs):
        task_started.set()
        while not cancel_check():
            time.sleep(0.005)
        raise OperationCancelled()

    monkeypatch.setattr(main_module, "check_for_update", delayed_check)
    monkeypatch.setattr(main_module, "extract_toc_text", cancellable_read)
    monkeypatch.setattr(window, "alert_msg", lambda *_args, **_kwargs: None)

    window.show()
    window._open_update_page()
    window.fill_toc_text()
    qtbot.waitUntil(update_started.is_set, timeout=5_000)
    qtbot.waitUntil(task_started.is_set, timeout=5_000)

    window.close()

    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)
    assert window.isVisible()
    assert window._close_requested

    update_release.set()
    qtbot.waitUntil(lambda: window._update_thread is None, timeout=5_000)
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5_000)


def test_export_runs_in_background_and_keeps_event_loop_responsive(
    window, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)
    window.pdf_path_edit.setText(str(source_path))
    window.dir_text_edit.setPlainText("Chapter 1  1")
    messages = []
    monkeypatch.setattr(window, "alert_msg", messages.append)

    def slow_write(_path, _bookmarks, _keep_existing=False, **_kwargs):
        time.sleep(0.08)
        return str(tmp_path / "source_new.pdf")

    monkeypatch.setattr(main_module, "add_bookmark", slow_write)
    event_loop_ticks = []
    QtCore.QTimer.singleShot(10, lambda: event_loop_ticks.append(True))

    started_at = time.monotonic()
    window.write_tree_to_pdf()
    returned_after = time.monotonic() - started_at

    assert returned_after < 0.05
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)
    assert event_loop_ticks
    assert "source_new.pdf" in window.statusbar.currentMessage()


def test_running_toc_task_is_cancelled_before_window_closes(
    window, qtbot, tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    def cancellable_read(_path, cancel_check=None, **_kwargs):
        while not cancel_check():
            time.sleep(0.005)
        raise OperationCancelled()

    monkeypatch.setattr(main_module, "extract_toc_text", cancellable_read)
    window.pdf_path_edit.setText(str(source_path))
    window.show()
    window.fill_toc_text()
    qtbot.waitUntil(
        lambda: window._worker_thread is not None
        and window._worker_thread.isRunning(),
        timeout=5_000,
    )

    window.close()

    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=5_000)
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5_000)


def test_update_check_runs_without_blocking_the_qt_event_loop(
    window, qtbot, monkeypatch
):
    opened = []

    def slow_check(_url, _version):
        time.sleep(0.08)
        return "update"

    monkeypatch.setattr(main_module, "check_for_update", slow_check)
    monkeypatch.setattr(
        main_module.webbrowser,
        "open",
        lambda url, **_kwargs: opened.append(url),
    )
    event_loop_ticks = []
    QtCore.QTimer.singleShot(10, lambda: event_loop_ticks.append(True))

    started_at = time.monotonic()
    window._open_update_page()
    returned_after = time.monotonic() - started_at

    assert returned_after < 0.05
    qtbot.waitUntil(lambda: window._update_thread is None, timeout=5_000)
    assert event_loop_ticks
    assert opened
