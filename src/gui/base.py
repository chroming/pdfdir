# -*- coding:utf-8 -*-

from functools import partial

from PyQt5.QtWidgets import QTreeWidget, QMenu
from PyQt5.QtCore import pyqtSlot, Qt


class MixinContextMenu(object):
    def __init__(self):
        self._init_context_menu()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._base_pos = None

    def _init_context_menu(self):
        self.context_menu = QMenu()

    @property
    def base_pos(self):
        """
        If this class is inherited by a child widget,
        you should set instance.base_pos = parent.pos()
        """
        if not self._base_pos:
            self._base_pos = self.pos()
        return self._base_pos

    @base_pos.setter
    def base_pos(self, value):
        self._base_pos = value

    def _show_context_menu(self, pos):
        self.context_menu.move(self.base_pos + pos)
        self.context_menu.show()

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
    def init_connect(self, parent=None):
        super(TreeWidget, self).__init__()
        self.itemClicked.connect(self.item_clicked)
        self.itemDoubleClicked.connect(self.item_double_clicked)
        if parent:
            self.base_pos = parent.pos()
        m = self.add_menu("添加")
        m.add_action('删除', lambda : None)

    def _set_all_items(self, items):
        self.clear()
        self.addTopLevelItems(items)

    def set_items(self, items):
        self._set_all_items(items)

    def item_clicked(self, item):
        self.closePersistentEditor(item, self.currentColumn())

    def item_double_clicked(self, item):
        self.openPersistentEditor(item, self.currentColumn())



    def to_dict(self):
        pass