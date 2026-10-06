"""Exercise terminal interrupts in a separate, real Qt event loop."""

import os
import subprocess
import sys

import pytest


SCRIPT = r'''
import os
import signal
import sys
import tempfile
import time
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from pypdf import PdfWriter
import src.gui.main as gui
from src.pdf.cancellation import OperationCancelled

mode = sys.argv[1]
original_signal = signal.getsignal(signal.SIGINT)
original_hook = sys.excepthook
temporary = tempfile.TemporaryDirectory()

def unexpected_error(*args, **kwargs):
    print('UNEXPECTED_ERROR_DIALOG', flush=True)
    QtWidgets.QApplication.instance().exit(91)

gui.QMessageBox.critical = unexpected_error

def interrupt():
    if mode == 'callback-interrupt':
        raise KeyboardInterrupt()
    os.kill(os.getpid(), signal.SIGINT)

def read_toc(_path, cancel_check, **kwargs):
    while not cancel_check():
        time.sleep(0.005)
    time.sleep(0.05)
    print('WORKER_CANCELLED', flush=True)
    raise OperationCancelled()

gui.extract_toc_text = read_toc

original_init = gui.Main.__init__
original_close = gui.Main.closeEvent

class Probe:
    def __init__(self, app, translator):
        original_init(self, app, translator)
        self.responses = 0
        QtCore.QTimer.singleShot(0, self.prepare)

    def prepare(self):
        if mode == 'dirty':
            self.dir_text_edit.setPlainText('Unsaved chapter 1')
            self.answer_timer = QtCore.QTimer(self)
            self.answer_timer.timeout.connect(self.answer_prompt)
            self.answer_timer.start(20)
        elif mode == 'busy':
            source = Path(temporary.name) / 'source.pdf'
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            writer.write(source)
            self.read_exist_dir_box.setChecked(False)
            assert self._activate_document(str(source))
            self.fill_toc_text()
            assert self._has_active_task()
        print('READY', flush=True)
        QtCore.QTimer.singleShot(150, interrupt)

    def answer_prompt(self):
        box = self._dirty_close_box
        if not box or not box.isVisible():
            return
        if self.responses == 0:
            next(b for b in box.buttons() if b is not self._dirty_discard_button).click()
            assert self.isVisible()
            assert self.dir_text == 'Unsaved chapter 1'
            print('DRAFT_PRESERVED', flush=True)
            self.responses += 1
            QtCore.QTimer.singleShot(150, interrupt)
        else:
            self._dirty_discard_button.click()
            print('DISCARD_CONFIRMED', flush=True)
            self.answer_timer.stop()

    def closeEvent(self, event):
        original_close(self, event)
        if event.isAccepted():
            assert not self._has_active_task()
            assert not self._has_active_update()
            print('CLOSED_SAFELY', flush=True)

for name in ('__init__', 'prepare', 'answer_prompt', 'closeEvent'):
    setattr(gui.Main, name, getattr(Probe, name))
try:
    gui.run()
except SystemExit as error:
    assert signal.getsignal(signal.SIGINT) is original_signal
    assert sys.excepthook is original_hook
    temporary.cleanup()
    raise
'''


@pytest.mark.skipif(os.name == "nt", reason="Uses POSIX terminal SIGINT delivery")
@pytest.mark.parametrize("mode", ["clean", "dirty", "busy", "callback-interrupt"])
def test_sigint_uses_close_flow_without_error_dialog(mode):
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, mode],
        env={**os.environ, "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CLOSED_SAFELY" in result.stdout
    assert "UNEXPECTED_ERROR_DIALOG" not in result.stdout
    assert "KeyboardInterrupt" not in result.stderr
    assert "QThread: Destroyed" not in result.stderr
    if mode == "dirty":
        assert "DRAFT_PRESERVED" in result.stdout
        assert "DISCARD_CONFIRMED" in result.stdout
    if mode == "busy":
        assert "WORKER_CANCELLED" in result.stdout


def test_regular_exceptions_still_reach_the_error_dialog(qapp, monkeypatch):
    import src.gui.main as gui

    logged = []
    dialogs = []
    monkeypatch.setattr(gui, "_original_excepthook", lambda *args: logged.append(args))
    monkeypatch.setattr(gui.QMessageBox, "critical", lambda *args: dialogs.append(args))
    error = RuntimeError("real application error")

    gui.exception_hook(type(error), error, None)

    assert logged == [(RuntimeError, error, None)]
    assert len(dialogs) == 1
    assert "real application error" in dialogs[0][2]
