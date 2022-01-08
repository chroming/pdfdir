# -*- coding:utf-8 -*-

from functools import partial

from PyQt5.QtWidgets import QTreeWidget, QMenu, QTreeWidgetItemIterator
from PyQt5.QtCore import pyqtSlot, Qt, QPoint


class MixinContextMenu(object):
    def __init__(self, parents=None):
        self._init_context_menu()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._base_pos = self.pos()
        self.parents = parents

    def _init_context_menu(self):
        self.context_menu = QMenu()

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
        if self.currentItem():
            self.context_menu.exec_(self.viewport().mapToGlobal(pos))

    def add_action(self, name, handler, menu=None):
        menu = menu or self.context_menu
        action = menu.addAction(name)
        action.triggered.connect(handler)

    def add_menu(self, name, menu=None):
        menu = menu or self.context_menu
        child_menu = menu.addMenu(name)
        child_menu.add_action = partial(self.add_action, menu=menu)
        child_menu.add_menu = partial(self.add_menu, menu=menu)
        return child_menu


class TreeWidget(MixinContextMenu):
    def init_connect(self, parents=None):
        super(TreeWidget, self).__init__(parents)
        self.itemPressed.connect(self.close_editor)
        self.itemDoubleClicked.connect(self.item_double_clicked)
        self.add_action('删除', self.item_remove_current)
        self.last_item = None
        self.last_column = None

    # TODO: Fix page num when drop item
    def dropEvent(self, event):
        """"""
        # self.current_item.setText('')
        super(TreeWidget, self).dropEvent(event)

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

    def item_double_clicked(self, item):
        current_column = self.currentColumn()
        if self.last_item == item:
            if self.last_column == current_column:
                self.closePersistentEditor(item, current_column)
                return
            else:
                self.closePersistentEditor(item, self.last_column)

        self.openPersistentEditor(item, current_column)
        self.last_item = item
        self.last_column = current_column

    def remove_item(self, item):
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))

    def item_remove_current(self):
        selecteds = self.selectedItems()
        for item in selecteds:
            self.remove_item(item)

    def children(self, item):
        child_items = []
        for i in range(item.childCount()):
            child_item = item.child(i)
            if not hasattr(child_item, '__hash__'):
                child_item.__hash__ = lambda: child_item.id
            child_items.append((child_item, self.children(child_item)))
        return child_items

    def to_qtree(self):
        items = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            items.append((item, self.children(item)))
        return items

    def children_to_dict(self, children, parent_index):
        children_list = []
        for child in children:
            k, vs = child
            children_list.append({'title': k.text(0),
                                  'num': int(k.text(1)),
                                  'real_num': int(k.text(2)),
                                  'parent': parent_index})
            children_list.extend(self.children_to_dict(vs, k.text(1)))
        return children_list

    def to_dict(self):
        qtrees = self.to_qtree()
        i = 0
        dir_dict = {}
        for r in qtrees:
            k, vs = r
            dir_dict[i] = {'title': k.text(0), 'num': int(k.text(1)), 'real_num': int(k.text(2))}
            for c in self.children_to_dict(vs, i):
                i += 1
                dir_dict[i] = c
            i += 1
        return dir_dict

    @staticmethod
    def set_pagenum(item, num, real_num):
        item.setText(1, str(num), str(real_num))

    def from_dict(self, dir_dict):
        pass