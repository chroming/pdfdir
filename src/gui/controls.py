"""Interaction roles shared by the workbench's native Qt controls."""

from PySide6 import QtCore, QtWidgets

from src.gui.product_style import icon


def configure_command(button):
    """Keep Designer-owned commands on the same secondary action grammar."""
    button.setProperty("variant", "secondary")
    button.setFocusPolicy(QtCore.Qt.StrongFocus)


def reserve_command_width(buttons, labels):
    """One command slot keeps its geometry through working/result states."""
    width = 124
    for button in buttons:
        button.setMinimumWidth(0)
        button.setMaximumWidth(16777215)
        option = QtWidgets.QStyleOptionButton()
        option.initFrom(button)
        for label in labels:
            text_size = QtCore.QSize(button.fontMetrics().horizontalAdvance(label),
                                    button.fontMetrics().height())
            width = max(width, button.style().sizeFromContents(
                QtWidgets.QStyle.CT_PushButton, option, text_size, button).width())
    for button in buttons:
        button.setFixedWidth(width)


class InlineErrorLabel(QtWidgets.QLabel):
    """Keep recovery text readable beside a vertically stretching editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("regex_error_label")
        self.setWordWrap(True)
        self.setTextFormat(QtCore.Qt.PlainText)
        self.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

    def _sync_height(self):
        # QLabel's ordinary minimumSizeHint only reserves a single line.
        # Clear the old constraint before measuring: heightForWidth otherwise
        # retains the minimum from an earlier, narrower or larger-font state.
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)  # Qt's QWIDGETSIZE_MAX.
        self.setFixedHeight(max(0, self.heightForWidth(self.width())))

    def setText(self, text):
        super().setText(text)
        self._sync_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_height()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QtCore.QEvent.FontChange, QtCore.QEvent.StyleChange):
            self._sync_height()


class KeyboardFocusMixin:
    """Mouse activation is not a persistent selection/focus decoration."""

    def _set_keyboard_focus(self, visible):
        self.setProperty("keyboardFocus", visible)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._set_keyboard_focus(event.reason() != QtCore.Qt.MouseFocusReason)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._set_keyboard_focus(False)

    def mousePressEvent(self, event):
        self._set_keyboard_focus(False)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        self._set_keyboard_focus(True)
        super().keyPressEvent(event)


class DisclosureButton(KeyboardFocusMixin, QtWidgets.QToolButton):
    def __init__(self, parent=None, *, compact=False):
        super().__init__(parent)
        self.setProperty("variant", "disclosure")
        self.setProperty("density", "compact" if compact else "regular")
        self.setCheckable(True)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QtCore.QSize(16, 16))
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.toggled.connect(self._update_indicator)
        self._update_indicator(False)

    def _update_indicator(self, expanded):
        self.setIcon(icon("chevron-down" if expanded else "chevron-right"))


class DetailButton(KeyboardFocusMixin, QtWidgets.QToolButton):
    def __init__(self, parent=None, *, compact=False):
        super().__init__(parent)
        self.setProperty("variant", "detail")
        self.setProperty("density", "compact" if compact else "regular")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)


class ViewTabs(KeyboardFocusMixin, QtWidgets.QTabBar):
    """Peer views of the same object, with the shared underline treatment."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("variant", "view-tabs")
        self.setExpanding(False)
        self.setDrawBase(False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)


class MenuButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("variant", "menu")
        self.setPopupMode(QtWidgets.QToolButton.InstantPopup)
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
