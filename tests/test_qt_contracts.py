import ast
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtWidgets

from src.gui.main import Main

GUI_SOURCE_FILES = (
    Path(__file__).resolve().parents[1] / "src" / "gui" / "base.py",
    Path(__file__).resolve().parents[1] / "src" / "gui" / "main.py",
)


@pytest.fixture
def window(qtbot, qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    qtbot.addWidget(main_window)
    return main_window


def _dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def test_direct_qt_binding_calls_use_positional_arguments():
    """Avoid binding-specific keyword names such as directory/dir and msecs."""
    violations = []
    for source_path in GUI_SOURCE_FILES:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.keywords:
                continue
            call_name = _dotted_name(node.func)
            is_direct_qt_call = call_name.startswith(
                ("QtCore.", "QtGui.", "QtWidgets.", "QMessageBox.")
            )
            is_known_qt_instance_call = call_name.endswith(
                (".showMessage", ".exec", ".load")
            )
            if is_direct_qt_call or is_known_qt_instance_call:
                violations.append(
                    (
                        source_path.name,
                        node.lineno,
                        call_name,
                        [keyword.arg for keyword in node.keywords],
                    )
                )

    assert violations == []


@pytest.mark.parametrize(
    ("level", "title", "icon"),
    [
        ("info", "Information", QtWidgets.QMessageBox.Icon.Information),
        ("warn", "Warning", QtWidgets.QMessageBox.Icon.Warning),
    ],
)
def test_message_box_uses_real_pyside6_enums_and_exec(
    qapp, monkeypatch, level, title, icon
):
    shown_boxes = []
    window_titles = []
    original_set_window_title = QtWidgets.QMessageBox.setWindowTitle

    def capture_exec(box):
        shown_boxes.append(
            (box.icon(), box.text())
        )
        return 0

    def capture_window_title(box, value):
        window_titles.append(value)
        original_set_window_title(box, value)

    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", capture_exec)
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "setWindowTitle",
        capture_window_title,
    )

    Main.alert_msg("Message", level=level)

    assert window_titles == [title]
    assert shown_boxes == [(icon, "Message")]


def test_message_box_ok_action_receives_clicked_button(qapp, monkeypatch):
    shown_boxes = []
    clicked = []

    def capture_exec(box):
        shown_boxes.append(box)
        return 0

    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", capture_exec)

    Main.alert_msg("Confirm", ok_action=lambda button: clicked.append(button))
    box = shown_boxes[0]
    ok_button = box.button(QtWidgets.QMessageBox.StandardButton.Ok)
    ok_button.click()

    assert clicked == [ok_button]


def test_status_bar_uses_real_pyside6_signature(window):
    window.show_status("Ready", timeout=123)

    assert window.statusbar.currentMessage() == "Ready"
