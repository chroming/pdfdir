"""Interaction roles shared by the workbench's native Qt controls."""

from PySide6 import QtCore, QtWidgets

from src.gui.product_style import icon


def configure_command(button):
    """Keep Designer-owned commands on the same secondary action grammar."""
    button.setProperty("variant", "secondary")
    button.setFocusPolicy(QtCore.Qt.StrongFocus)


class DisclosureButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("variant", "disclosure")
        self.setCheckable(True)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QtCore.QSize(16, 16))
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.toggled.connect(self._update_indicator)
        self._update_indicator(False)

    def _update_indicator(self, expanded):
        self.setIcon(icon("chevron-down" if expanded else "chevron-right"))


class DetailButton(QtWidgets.QToolButton):
    def __init__(self, parent=None, *, compact=False):
        super().__init__(parent)
        self.setProperty("variant", "detail")
        self.setProperty("density", "compact" if compact else "regular")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)


class BookmarkItemDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setProperty("variant", "cell-editor")
        editor.setFont(option.font)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        # A cell is not a form field: never let the global field height expand
        # it into its neighbour, or a long title cover the page columns.
        editor.setGeometry(option.rect)
