import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from src.gui.base import TreeWidgetController


def _tree_item(title, page):
    return QtWidgets.QTreeWidgetItem([title, str(page), str(page)])


def test_tree_controller_serializes_multiple_nested_branches(qtbot):
    widget = QtWidgets.QTreeWidget()
    widget.setColumnCount(3)
    qtbot.addWidget(widget)
    controller = TreeWidgetController(widget)
    first = _tree_item("First", 1)
    child = _tree_item("Child", 2)
    grandchild = _tree_item("Grandchild", 3)
    second_child = _tree_item("Second child", 4)
    second = _tree_item("Second", 5)
    child.addChild(grandchild)
    first.addChildren([child, second_child])
    widget.addTopLevelItems([first, second])

    assert controller.to_dict() == {
        0: {"title": "First", "num": 1, "real_num": 1},
        1: {"title": "Child", "num": 2, "real_num": 2, "parent": 0},
        2: {"title": "Grandchild", "num": 3, "real_num": 3, "parent": 1},
        3: {"title": "Second child", "num": 4, "real_num": 4, "parent": 0},
        4: {"title": "Second", "num": 5, "real_num": 5},
    }


def test_tree_controller_removes_selected_top_level_and_child_items(qtbot):
    widget = QtWidgets.QTreeWidget()
    widget.setColumnCount(3)
    widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
    qtbot.addWidget(widget)
    controller = TreeWidgetController(widget)
    parent = _tree_item("Parent", 1)
    child = _tree_item("Child", 2)
    other = _tree_item("Other", 3)
    parent.addChild(child)
    widget.addTopLevelItems([parent, other])
    child.setSelected(True)
    other.setSelected(True)

    controller.item_remove_current()

    assert parent.childCount() == 0
    assert widget.topLevelItemCount() == 1
    assert widget.topLevelItem(0).text(0) == "Parent"


def test_tree_controller_toggles_persistent_editor(qtbot):
    widget = QtWidgets.QTreeWidget()
    widget.setColumnCount(3)
    qtbot.addWidget(widget)
    controller = TreeWidgetController(widget)
    item = _tree_item("Editable", 1)
    widget.addTopLevelItem(item)
    widget.setCurrentItem(item, 0)

    controller.item_double_clicked(item)
    assert widget.isPersistentEditorOpen(item, 0)

    controller.item_double_clicked(item)
    assert not widget.isPersistentEditorOpen(item, 0)
    assert controller.last_item is None


def test_tree_controller_clear_resets_editor_state(qtbot):
    widget = QtWidgets.QTreeWidget()
    qtbot.addWidget(widget)
    controller = TreeWidgetController(widget)
    controller.last_item = object()
    controller.last_column = 1

    controller.clear()

    assert controller.last_item is None
    assert controller.last_column is None


def test_tree_controller_builds_nested_menus_and_tracks_parent_position(qtbot):
    parent = QtWidgets.QWidget()
    parent.move(10, 20)
    widget = QtWidgets.QTreeWidget(parent)
    widget.move(3, 4)
    qtbot.addWidget(parent)
    controller = TreeWidgetController(widget, parents=[parent, widget])
    calls = []

    child_menu = controller.add_menu("More")
    action = child_menu.add_action("Action", lambda: calls.append("called"))
    action.trigger()

    assert calls == ["called"]
    assert controller.base_pos.x() == 13
    assert controller.base_pos.y() == 24

    controller.base_pos = widget.pos()
    controller.parents = None
    assert controller.base_pos == widget.pos()


def test_tree_controller_opens_context_menu_only_for_current_item(
    qtbot, monkeypatch
):
    widget = QtWidgets.QTreeWidget()
    qtbot.addWidget(widget)
    controller = TreeWidgetController(widget)
    calls = []
    monkeypatch.setattr(
        controller.context_menu,
        "exec",
        lambda position: calls.append(position),
    )

    controller._show_context_menu(widget.pos())
    assert calls == []

    item = _tree_item("Current", 1)
    widget.addTopLevelItem(item)
    widget.setCurrentItem(item)
    controller._show_context_menu(widget.pos())
    assert len(calls) == 1
