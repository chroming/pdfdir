# -*- coding: utf-8 -*-

from functools import partial

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)


class MixinContextMenu(object):
    def __init__(self, parents=None):
        self._init_context_menu()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._base_pos = self.pos()
        self.parents = parents

    def _init_context_menu(self):
        self.context_menu = QMenu(self)

    @property
    def base_pos(self):
        """
        If this class is inherited by a child widget,
        you should set instance.base_pos = parent.pos()
        """
        if self.parents:
            self._base_pos = QPoint()
            for p in self.parents:
                self._base_pos += p.pos()
        return self._base_pos

    @base_pos.setter
    def base_pos(self, value):
        self._base_pos = value

    def _show_context_menu(self, pos):
        item = self.currentItem()
        if not item and len(getattr(self, '_history', ())) < 2:
            return
        if pos is None or pos.x() < 0 or pos.y() < 0:
            item_rect = self.visualItemRect(item) if item else self.viewport().rect()
            pos = (
                item_rect.bottomLeft()
                if item_rect.isValid()
                else self.viewport().rect().center()
            )
        self.context_menu.popup(self.viewport().mapToGlobal(pos))

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


class TreeWidget(MixinContextMenu):
    _TOOLTIP_COLUMNS = (0, 1, 2)

    def fix_column(self):
        header = self.header()
        # Only resize first column
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setStretchLastSection(False)
        for column in (1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

    def init_connect(
        self,
        parents=None,
        preview_changed=None,
        delete_label="删除",
    ):
        self._preview_changed_callback = preview_changed
        self._suppress_preview_changed = False
        super(TreeWidget, self).__init__(parents)
        self.undo_action = self.add_action("撤销", self.undo)
        self.redo_action = self.add_action("重做", self.redo)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.context_menu.addSeparator()
        self.itemPressed.connect(self.close_editor)
        self.itemDoubleClicked.connect(self.item_double_clicked)
        self.itemChanged.connect(self._item_changed)
        self.model().rowsInserted.connect(self._rows_inserted)
        self.delete_action = self.add_action(
            delete_label,
            self.item_remove_current,
        )
        self.remove_action = self.delete_action
        self.delete_action.setShortcuts(
            [
                QKeySequence(Qt.Key_Delete),
                QKeySequence(Qt.Key_Backspace),
            ]
        )
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setEditTriggers(
            self.editTriggers()
            | QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
        )
        self.setIndentation(18)
        self.setUniformRowHeights(True)
        self.last_item = None
        self.last_column = None
        self._configure_all_items()
        self._history = []
        self._history_index = -1
        self._history_paused = False
        self.reset_history()

    def _snapshot(self):
        def record(item):
            return (tuple(item.text(i) for i in range(self.columnCount())),
                    tuple(record(item.child(i)) for i in range(item.childCount())))
        return tuple(record(self.topLevelItem(i)) for i in range(self.topLevelItemCount()))

    def reset_history(self):
        self._history = [self._snapshot()]
        self._history_index = 0
        self._update_history_actions()

    def _update_history_actions(self):
        self.undo_action.setEnabled(self._history_index > 0)
        self.redo_action.setEnabled(self._history_index < len(self._history) - 1)

    def record_history(self):
        if not hasattr(self, '_history') or self._history_paused:
            return
        state = self._snapshot()
        if state == self._history[self._history_index]:
            return
        del self._history[self._history_index + 1:]
        self._history.append(state)
        self._history = self._history[-100:]
        self._history_index = len(self._history) - 1
        self._update_history_actions()

    def _restore_history(self, direction):
        target = self._history_index + direction
        if not 0 <= target < len(self._history):
            return
        self._history_paused = True
        self._suppress_preview_changed = True
        try:
            self.clear()
            def restore(record, parent):
                texts, children = record
                item = QTreeWidgetItem(list(texts))
                if parent is None:
                    self.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                for child in children:
                    restore(child, item)
                item.setExpanded(True)
            for record in self._history[target]:
                restore(record, None)
            self._history_index = target
            self._configure_all_items()
        finally:
            self._suppress_preview_changed = False
            self._history_paused = False
        self._notify_preview_changed()
        self._update_history_actions()

    def undo(self):
        self._restore_history(-1)

    def redo(self):
        self._restore_history(1)

    def shift_page_offset(self, delta):
        """Shift current and undo states together, preserving manual corrections."""
        if not delta:
            return
        def shifted(text):
            try:
                return str(int(text) + delta)
            except ValueError:
                return text
        def shift_record(record):
            texts, children = record
            texts = list(texts)
            texts[2] = shifted(texts[2])
            return tuple(texts), tuple(shift_record(child) for child in children)
        self._suppress_preview_changed = True
        try:
            for item in self.all_items:
                item.setText(2, shifted(item.text(2)))
                self._refresh_item_tooltips(item)
            self._history = [tuple(shift_record(row) for row in state)
                             for state in self._history]
        finally:
            self._suppress_preview_changed = False

    def dropEvent(self, event):
        self.record_history()
        self._history_paused = True
        try:
            self._perform_drop_event(event)
        finally:
            self._history_paused = False
        if event.isAccepted():
            self._configure_all_items()
            self._notify_preview_changed()

    def _perform_drop_event(self, event):
        super(TreeWidget, self).dropEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            self.redo()
            event.accept()
            return
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key_F2 and self.currentItem():
            item = self.currentItem()
            self._configure_item(item)
            self.editItem(item, self.currentColumn())
            event.accept()
            return
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.item_remove_current()
            event.accept()
            return
        if key == Qt.Key_Menu or (
            key == Qt.Key_F10 and modifiers & Qt.ShiftModifier
        ):
            self._show_context_menu(None)
            event.accept()
            return
        super(TreeWidget, self).keyPressEvent(event)

    def set_preview_changed_callback(self, callback):
        self._preview_changed_callback = callback

    def set_delete_action_label(self, label):
        self.delete_action.setText(label)

    def _notify_preview_changed(self):
        if not self._suppress_preview_changed:
            self.record_history()
        callback = self._preview_changed_callback
        if callback and not self._suppress_preview_changed:
            callback()

    def _rows_inserted(self, parent_index, first, last):
        for row in range(first, last + 1):
            index = self.model().index(row, 0, parent_index)
            item = self.itemFromIndex(index)
            if item:
                self._configure_item_tree(item)
        self.record_history()

    def _configure_all_items(self):
        for item in self.all_items:
            self._configure_item(item)

    def _configure_item_tree(self, item):
        self._configure_item(item)
        for index in range(item.childCount()):
            self._configure_item_tree(item.child(index))

    def _configure_item(self, item):
        previous = self._suppress_preview_changed
        self._suppress_preview_changed = True
        try:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._refresh_item_tooltips(item)
        finally:
            self._suppress_preview_changed = previous

    def _refresh_item_tooltips(self, item):
        for column in self._TOOLTIP_COLUMNS:
            if column < self.columnCount():
                item.setToolTip(column, item.text(column))

    def _item_changed(self, item, column):
        if self._suppress_preview_changed:
            return
        previous = self._suppress_preview_changed
        self._suppress_preview_changed = True
        try:
            if column in self._TOOLTIP_COLUMNS:
                item.setToolTip(column, item.text(column))
        finally:
            self._suppress_preview_changed = previous
        self._notify_preview_changed()

    @property
    def current_item(self):
        return self.currentItem()

    @property
    def all_items(self):
        it = QTreeWidgetItemIterator(self)
        while it.value():
            yield it.value()
            it += 1

    def _set_all_items(self, items):
        self.clear()
        self.addTopLevelItems(items)

    def set_items(self, items):
        self._set_all_items(items)

    def close_editor(self, *args):
        if None not in (self.last_item, self.last_column):
            self.closePersistentEditor(self.last_item, self.last_column)

    def item_clicked(self, item):
        self.closePersistentEditor(item, self.currentColumn())

    def item_double_clicked(self, item, column=None):
        current_column = self.currentColumn() if column is None else column
        self._configure_item(item)
        if self.last_item == item:
            if self.last_column == current_column:
                self.closePersistentEditor(item, current_column)
                self.last_item = None
                self.last_column = None
                return
            else:
                self.closePersistentEditor(item, self.last_column)

        self.openPersistentEditor(item, current_column)
        self.last_item = item
        self.last_column = current_column

    def remove_item(self, item, notify=True):
        removed = False
        parent = item.parent()
        if parent:
            child_index = parent.indexOfChild(item)
            if child_index >= 0:
                parent.takeChild(child_index)
                removed = True
        else:
            item_index = self.indexOfTopLevelItem(item)
            if item_index >= 0:
                self.takeTopLevelItem(item_index)
                removed = True
        if removed and notify:
            self._notify_preview_changed()
        return removed

    def item_remove_current(self):
        selecteds = list(self.selectedItems())
        if not selecteds and self.currentItem():
            selecteds = [self.currentItem()]
        selected_ids = {id(item) for item in selecteds}
        roots = []
        for item in selecteds:
            parent = item.parent()
            while parent and id(parent) not in selected_ids:
                parent = parent.parent()
            if parent is None:
                roots.append(item)
        removed = False
        for item in roots:
            removed = self.remove_item(item, notify=False) or removed
        if removed:
            self._notify_preview_changed()

    def children(self, item):
        child_items = []
        for i in range(item.childCount()):
            child_item = item.child(i)
            if not hasattr(child_item, "__hash__"):
                child_item.__hash__ = lambda: child_item.id
            child_items.append((child_item, self.children(child_item)))
        return child_items

    def to_qtree(self):
        items = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            items.append((item, self.children(item)))
        return items

    def children_to_dict(self, children, current_index, parent_index):
        children_dict = {}
        for child in children:
            k, vs = child
            real_num = int(k.text(2))
            c = {
                "title": k.text(0),
                "num": int(k.text(1)),
                "real_num": real_num,
                "parent": parent_index,
            }
            children_dict[current_index] = c
            if vs:
                children_dict.update(
                    self.children_to_dict(vs, current_index + 1, current_index)
                )
            current_index = max(children_dict.keys()) + 1
        return children_dict

    def to_dict(self):
        qtrees = self.to_qtree()
        current_index = 0
        dir_dict = {}
        for r in qtrees:
            k, vs = r
            dir_dict[current_index] = {
                "title": k.text(0),
                "num": int(k.text(1)),
                "real_num": int(k.text(2)),
            }
            children_dict = self.children_to_dict(vs, current_index + 1, current_index)
            dir_dict.update(children_dict)
            current_index = max(dir_dict.keys()) + 1
        return dir_dict

    @staticmethod
    def set_pagenum(item, num, real_num):
        num_text = str(num)
        real_num_text = str(real_num)
        changed = (
            item.text(1) != num_text
            or item.text(2) != real_num_text
        )
        if not changed:
            return
        tree = item.treeWidget()
        if tree and hasattr(tree, "_suppress_preview_changed"):
            previous = tree._suppress_preview_changed
            tree._suppress_preview_changed = True
            try:
                item.setText(1, num_text)
                item.setText(2, real_num_text)
                tree._refresh_item_tooltips(item)
            finally:
                tree._suppress_preview_changed = previous
            tree._notify_preview_changed()
            return
        item.setText(1, num_text)
        item.setText(2, real_num_text)

    def from_dict(self, dir_dict):
        pass

    def clear(self):
        self.last_item = None
        self.last_column = None
        return super(TreeWidget, self).clear()


class BookmarkTreeWidget(TreeWidget, QTreeWidget):
    """Use a stable Qt subclass instead of reassigning a Shiboken wrapper type."""

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
