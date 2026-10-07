"""Shared control roles, including their editing and disclosure states."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from src.gui.main import Main
from tests.gui_test_utils import track_main_window


@pytest.fixture
def window(qtbot, qapp):
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    window.dir_text_edit.setPlainText("1. Chapter 1\n1.1 Section 2\nAppendix 3")
    window.show()
    return window


@pytest.mark.parametrize("column", [0, 1, 2])
@pytest.mark.parametrize("large", [False, True])
def test_cell_editor_fits_row_and_preserves_content_type(window, qapp, qtbot, column, large):
    original = qapp.font()
    try:
        if large:
            font = QtGui.QFont(original)
            font.setPointSize(18)
            qapp.setFont(font)
        tree = window.dir_tree_widget
        item = tree.topLevelItem(0)
        qtbot.wait(20)
        before = tree.visualItemRect(item)
        tree.item_double_clicked(item, column)
        qtbot.wait(20)
        editor = next(c for c in tree.findChildren(QtWidgets.QLineEdit) if c.isVisible())
        assert editor.height() <= before.height()
        assert editor.y() >= before.top()
        assert editor.geometry().bottom() <= before.bottom()
        assert editor.font().pixelSize() == tree.font().pixelSize()
        assert editor.font().pointSizeF() == tree.font().pointSizeF()
        assert tree.visualItemRect(item) == before
        tree.closePersistentEditor(item, column)
    finally:
        qapp.setFont(original)


def test_peer_secondary_commands_share_presentation(window):
    commands = (window.auto_toc_button, window.paste_button, window.auto_offset_button)
    assert len({button.property("variant") for button in commands}) == 1
    assert len({button.height() for button in commands}) == 1
    assert all(button.property("variant") != "primary" for button in commands)


@pytest.mark.parametrize("english", [False, True])
def test_disclosures_share_component_and_keep_label_and_size(window, qtbot, english):
    if english:
        window.to_english()
    assert type(window.advanced_button) is type(window.rules_options_button)
    for button in (window.advanced_button, window.rules_options_button):
        if not button.isVisible():
            window.advanced_button.click()
        before = button.text(), button.sizeHint()
        icon = button.icon().cacheKey()
        button.click()
        qtbot.wait(20)
        assert not button.icon().isNull()
        assert button.icon().cacheKey() != icon
        assert (button.text(), button.sizeHint()) == before
        assert button.isCheckable()


@pytest.mark.parametrize("english", [False, True])
def test_inspection_links_are_explicit_and_do_not_change_draft(window, qtbot, english):
    if english:
        window.to_english()
    window.level_mode_box.setCurrentIndex(1)
    window.level0_box.setChecked(True)
    window.level1_box.setChecked(True)
    window.level0_edit.setText(r"^\d+\.")
    window.level1_edit.setText(r"^\d+\.\d+")
    window._clear_rule_trial()
    button = window.rule_counts[0]
    assert "match" in button.text().lower() if english else "匹配" in button.text()
    assert type(button) is type(window.output_location_button)
    assert type(button) is type(window.rules_unmatched_button)
    before = window._current_draft_signature()
    button.click()
    assert window._current_draft_signature() == before
    assert window.dir_tree_widget.currentItem() is not None
    window.level0_edit.setText("[")
    assert not button.isEnabled()
    assert "updated" in button.text() if english else "更新" in button.text()


@pytest.mark.parametrize("key", [QtCore.Qt.Key_Return, QtCore.Qt.Key_Tab, QtCore.Qt.Key_Escape])
def test_cell_editor_keyboard_commit_cancel_and_history(window, qtbot, key):
    tree = window.dir_tree_widget
    window.offset_edit.setText("8")
    item = tree.topLevelItem(0)
    original = item.text(1)
    tree.setCurrentItem(item, 1)
    tree.setFocus()
    qtbot.keyClick(tree, QtCore.Qt.Key_F2)
    editor = next(e for e in tree.findChildren(QtWidgets.QLineEdit) if e.isVisible())
    editor.selectAll()
    qtbot.keyClicks(editor, "3")
    qtbot.keyClick(editor, key)
    qtbot.wait(20)
    if key == QtCore.Qt.Key_Escape:
        assert item.text(1) == original
    else:
        assert item.text(1) == "3"
        assert item.text(2) == "11"
        # Tab may open the next editor. Finish it before traversing history.
        for editor in tree.findChildren(QtWidgets.QLineEdit):
            if editor.isVisible():
                qtbot.keyClick(editor, QtCore.Qt.Key_Escape)
        tree.undo()
        assert tree.topLevelItem(0).text(1) == original
        tree.redo()
        assert tree.topLevelItem(0).text(1) == "3"


def test_shared_control_roles_have_keyboard_and_disabled_states(window):
    controls = (window.advanced_button, window.rules_options_button,
                window.output_location_button, window.rules_unmatched_button,
                *window.rule_counts)
    for button in controls:
        assert button.focusPolicy() == QtCore.Qt.StrongFocus
        button.setEnabled(False)
        assert not button.isEnabled()
    assert window.rule_counts[0].property("variant") == "detail"
    assert window.output_location_button.property("density") == "compact"
    assert window.rule_counts[0].property("density") == "regular"
