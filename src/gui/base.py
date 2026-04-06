from functools import partial

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QHeaderView, QMenu


class TreeWidgetWrapper:
    def __init__(self, widget, parents=None):
        self.widget = widget
        self.parents = parents
        self._init_context_menu()
        self.widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.widget.customContextMenuRequested.connect(self._show_context_menu)
        self._base_pos = self.widget.pos()
        
        self.widget.itemPressed.connect(self.close_editor)
        self.widget.itemDoubleClicked.connect(self.item_double_clicked)
        self.add_action("删除", self.item_remove_current)
        self.last_item = None
        self.last_column = None

    def _init_context_menu(self):
        self.context_menu = QMenu()

    @property
    def base_pos(self):
        if self.parents:
            self._base_pos = QPoint()
            for p in self.parents:
                self._base_pos += p.pos()
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

    def add_menu(self, name, menu=None):
        menu = menu or self.context_menu
        child_menu = menu.addMenu(name)
        child_menu.add_action = partial(self.add_action, menu=menu)
        child_menu.add_menu = partial(self.add_menu, menu=menu)
        return child_menu

    def fix_column(self):
        header = self.widget.header()
        # Only resize first column
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def close_editor(self, *args):
        if None not in (self.last_item, self.last_column):
            self.widget.closePersistentEditor(self.last_item, self.last_column)

    def item_double_clicked(self, item):
        current_column = self.widget.currentColumn()
        if self.last_item == item:
            if self.last_column == current_column:
                self.widget.closePersistentEditor(item, current_column)
                return
            else:
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
        selecteds = self.widget.selectedItems()
        for item in selecteds:
            self.remove_item(item)

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
        for i in range(self.widget.topLevelItemCount()):
            item = self.widget.topLevelItem(i)
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

    def clear(self):
        self.last_item = None
        return self.widget.clear()

    def insertTopLevelItem(self, index, item):
        self.widget.insertTopLevelItem(index, item)

    def __getattr__(self, name):
         return getattr(self.widget, name)
