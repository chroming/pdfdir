import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from src.gui.base import BookmarkTreeWidget, TreeWidget


def _make_tree(qtbot, preview_changed=None):
    tree = BookmarkTreeWidget()
    tree.setColumnCount(3)
    tree.init_connect(preview_changed=preview_changed)
    qtbot.addWidget(tree)
    tree.resize(640, 320)
    tree.show()
    return tree


def test_tree_items_are_editable_draggable_and_expose_complete_tooltips(qtbot):
    tree = _make_tree(qtbot)
    parent = QtWidgets.QTreeWidgetItem(
        ["A very long bookmark title", "123", "456"]
    )
    child = QtWidgets.QTreeWidgetItem(
        ["A nested bookmark title", "789", "999"]
    )

    tree.addTopLevelItem(parent)
    parent.addChild(child)

    assert tree.dragDropMode() == QtWidgets.QAbstractItemView.InternalMove
    assert tree.dragEnabled()
    assert tree.acceptDrops()
    assert tree.defaultDropAction() == QtCore.Qt.MoveAction
    for item in (parent, child):
        assert item.flags() & QtCore.Qt.ItemIsEditable
        for column in range(3):
            assert item.toolTip(column) == item.text(column)


def test_f2_edits_current_cell_and_notifies_preview_change(qtbot):
    changes = []
    tree = _make_tree(qtbot, preview_changed=lambda: changes.append("changed"))
    item = QtWidgets.QTreeWidgetItem(["Chapter", "1", "2"])
    tree.addTopLevelItem(item)
    changes.clear()
    tree.setCurrentItem(item, 0)
    tree.setFocus()

    qtbot.keyClick(tree, QtCore.Qt.Key_F2)

    qtbot.waitUntil(
        lambda: any(
            editor.isVisible()
            for editor in tree.findChildren(QtWidgets.QLineEdit)
        )
    )
    editor = next(
        editor
        for editor in tree.findChildren(QtWidgets.QLineEdit)
        if editor.isVisible()
    )
    editor.setFocus()
    editor.selectAll()
    qtbot.keyClicks(editor, "Renamed chapter")
    qtbot.keyClick(editor, QtCore.Qt.Key_Return)

    qtbot.waitUntil(lambda: item.text(0) == "Renamed chapter")
    assert item.text(0) == "Renamed chapter"
    assert item.toolTip(0) == "Renamed chapter"
    assert changes == ["changed"]


def test_delete_and_backspace_remove_selection_and_notify_once(qtbot):
    changes = []
    tree = _make_tree(qtbot, preview_changed=lambda: changes.append("changed"))
    first = QtWidgets.QTreeWidgetItem(["First", "1", "1"])
    second = QtWidgets.QTreeWidgetItem(["Second", "2", "2"])
    tree.addTopLevelItems([first, second])
    changes.clear()
    tree.setCurrentItem(first)
    tree.setFocus()

    qtbot.keyClick(tree, QtCore.Qt.Key_Delete)

    assert tree.topLevelItemCount() == 1
    assert tree.topLevelItem(0) is second
    assert changes == ["changed"]

    changes.clear()
    tree.setCurrentItem(second)
    qtbot.keyClick(tree, QtCore.Qt.Key_Backspace)

    assert tree.topLevelItemCount() == 0
    assert changes == ["changed"]


def test_keyboard_context_menu_and_localized_delete_label(qtbot):
    tree = _make_tree(qtbot)
    item = QtWidgets.QTreeWidgetItem(["Chapter", "1", "1"])
    tree.addTopLevelItem(item)
    tree.setCurrentItem(item)
    tree.setFocus()
    shown = []
    tree.context_menu.aboutToShow.connect(lambda: shown.append(True))

    tree.set_delete_action_label("Delete bookmark")
    qtbot.keyClick(
        tree,
        QtCore.Qt.Key_F10,
        modifier=QtCore.Qt.ShiftModifier,
    )

    qtbot.waitUntil(lambda: bool(shown))
    assert tree.delete_action.text() == "Delete bookmark"
    assert tree.remove_action is tree.delete_action
    tree.context_menu.close()

    shown.clear()
    tree.setFocus()
    qtbot.keyClick(tree, QtCore.Qt.Key_Menu)

    qtbot.waitUntil(lambda: bool(shown))
    tree.context_menu.close()


def test_accepted_drop_notifies_preview_change(qtbot, monkeypatch):
    changes = []
    tree = _make_tree(qtbot, preview_changed=lambda: changes.append("changed"))

    class AcceptedDrop:
        accepted = False

        def accept(self):
            self.accepted = True

        def isAccepted(self):
            return self.accepted

    event = AcceptedDrop()
    monkeypatch.setattr(
        tree,
        "_perform_drop_event",
        lambda current_event: current_event.accept(),
    )

    tree.dropEvent(event)

    assert changes == ["changed"]


def test_set_pagenum_updates_both_columns_tooltips_and_callback(qtbot):
    changes = []
    tree = _make_tree(qtbot, preview_changed=lambda: changes.append("changed"))
    item = QtWidgets.QTreeWidgetItem(["Chapter", "1", "2"])
    tree.addTopLevelItem(item)
    changes.clear()

    tree.set_pagenum(item, 42, 45)

    assert item.text(1) == "42"
    assert item.text(2) == "45"
    assert item.toolTip(1) == "42"
    assert item.toolTip(2) == "45"
    assert changes == ["changed"]
