from functools import partial

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QHeaderView, QMenu


class TreeWidgetController:
    """Add bookmark-tree behavior without changing the Qt widget's runtime type."""

    def __init__(self, widget, parents=None):
        self.widget = widget
        self.parents = parents
        self.context_menu = QMenu(widget)
        self._base_pos = widget.pos()
        self.last_item = None
        self.last_column = None

        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(self._show_context_menu)
        widget.itemPressed.connect(self.close_editor)
        widget.itemDoubleClicked.connect(self.item_double_clicked)
        self.add_action("删除", self.item_remove_current)

    @property
    def base_pos(self):
        if self.parents:
            self._base_pos = QPoint()
            for parent in self.parents:
                self._base_pos += parent.pos()
        return self._base_pos

    @base_pos.setter
    def base_pos(self, value):
        self._base_pos = value

    def _show_context_menu(self, pos):
        if self.widget.currentItem():
            self.context_menu.exec(self.widget.viewport().mapToGlobal(pos))

    def add_action(self, name, handler, menu=None):
        menu = menu or self.context_menu
        action = menu.addAction(name)
        action.triggered.connect(handler)
        return action

    def add_menu(self, name, menu=None):
        menu = menu or self.context_menu
        child_menu = menu.addMenu(name)
        child_menu.add_action = partial(self.add_action, menu=child_menu)
        child_menu.add_menu = partial(self.add_menu, menu=child_menu)
        return child_menu

    def fix_column(self):
        self.widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def close_editor(self, *_args):
        if None not in (self.last_item, self.last_column):
            self.widget.closePersistentEditor(self.last_item, self.last_column)

    def item_double_clicked(self, item):
        current_column = self.widget.currentColumn()
        if self.last_item == item:
            if self.last_column == current_column:
                self.widget.closePersistentEditor(item, current_column)
                self.last_item = None
                self.last_column = None
                return
            self.widget.closePersistentEditor(item, self.last_column)

        self.widget.openPersistentEditor(item, current_column)
        self.last_item = item
        self.last_column = current_column

    def remove_item(self, item):
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            self.widget.takeTopLevelItem(self.widget.indexOfTopLevelItem(item))

    def item_remove_current(self):
        for item in self.widget.selectedItems():
            self.remove_item(item)

    def children(self, item):
        return [
            (item.child(index), self.children(item.child(index)))
            for index in range(item.childCount())
        ]

    def to_qtree(self):
        return [
            (
                self.widget.topLevelItem(index),
                self.children(self.widget.topLevelItem(index)),
            )
            for index in range(self.widget.topLevelItemCount())
        ]

    def children_to_dict(self, children, current_index, parent_index):
        children_dict = {}
        for item, descendants in children:
            children_dict[current_index] = {
                "title": item.text(0),
                "num": int(item.text(1)),
                "real_num": int(item.text(2)),
                "parent": parent_index,
            }
            if descendants:
                children_dict.update(
                    self.children_to_dict(descendants, current_index + 1, current_index)
                )
            current_index = max(children_dict) + 1
        return children_dict

    def to_dict(self):
        current_index = 0
        result = {}
        for item, children in self.to_qtree():
            result[current_index] = {
                "title": item.text(0),
                "num": int(item.text(1)),
                "real_num": int(item.text(2)),
            }
            result.update(
                self.children_to_dict(children, current_index + 1, current_index)
            )
            current_index = max(result) + 1
        return result

    def clear(self):
        self.last_item = None
        self.last_column = None
        self.widget.clear()
