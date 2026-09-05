"""Shared lifecycle helpers for tests that own a ``Main`` window."""

import time

from PySide6 import QtCore
from PySide6 import QtTest
from PySide6 import QtWidgets


def track_main_window(qtbot, qapp, window):
    """Let pytest-qt own one safe close without leaking native dialogs."""

    def prepare_for_close(widget):
        widget.pdf_path_edit.blockSignals(True)
        widget._allow_close_once = True
        widget.close()
        # Keep terminal worker signals silent even when a QThread stopped just
        # before pytest-qt entered teardown but its queued slots remain pending.
        widget._close_requested = True

        deadline = time.monotonic() + 12
        while (
            widget._has_active_task() or widget._has_active_update()
        ) and time.monotonic() < deadline:
            qapp.processEvents(QtCore.QEventLoop.AllEvents, 50)
            QtTest.QTest.qWait(10)

        if widget._has_active_task() or widget._has_active_update():
            raise AssertionError(
                "Main window still owns a running background thread at teardown"
            )

        for dialog in widget.findChildren(QtWidgets.QDialog):
            if dialog.isVisible():
                dialog.close()
        qapp.processEvents(QtCore.QEventLoop.AllEvents, 50)
        visible_dialogs = [
            dialog.windowTitle()
            for dialog in widget.findChildren(QtWidgets.QDialog)
            if dialog.isVisible()
        ]
        if visible_dialogs:
            raise AssertionError(
                "Main window still owns visible dialogs at teardown: {}".format(
                    visible_dialogs
                )
            )

        widget._allow_close_once = True

    qtbot.addWidget(window, before_close_func=prepare_for_close)
    return window
