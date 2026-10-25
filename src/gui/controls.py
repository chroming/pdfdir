"""Interaction roles shared by the workbench's native Qt controls."""

import math

from PySide6 import QtCore, QtGui, QtWidgets

from src.gui.product_style import icon


def configure_command(button):
    """Keep Designer-owned commands on the same secondary action grammar."""
    button.setProperty("variant", "secondary")
    button.setFocusPolicy(QtCore.Qt.StrongFocus)
    if not hasattr(button, "_keyboard_focus_filter"):
        button._keyboard_focus_filter = CommandFocusFilter(button)
        button.installEventFilter(button._keyboard_focus_filter)


def align_label_baselines(title, metadata):
    """Align mixed-size labels while their layout centers the whole group."""
    heading, detail = title.fontMetrics(), metadata.fontMetrics()
    offset = 2 * (heading.ascent() - detail.ascent()) - (heading.height() - detail.height())
    metadata.setContentsMargins(0, max(0, offset), 0, max(0, -offset))


def set_presentation(widget, name, value):
    """Refresh a semantic role only when it changes, without affecting state."""
    if widget.property(name) != value:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.updateGeometry()
        widget.update()


class DocumentIdentity(QtWidgets.QWidget):
    """Elided object identity followed immediately by quiet, complete metadata."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = ""
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.name_label = QtWidgets.QLabel(self)
        self.name_label.setObjectName("document_name_label")
        self.name_label.setTextFormat(QtCore.Qt.PlainText)
        self.pages_label = QtWidgets.QLabel(self)
        self.pages_label.setObjectName("document_pages_label")
        self.pages_label.setTextFormat(QtCore.Qt.PlainText)
        layout.addWidget(self.name_label)
        layout.addWidget(self.pages_label)
        layout.addStretch(1)
        self.setMinimumWidth(40)

    def set_document(self, name, pages, loaded):
        self._name = name
        set_presentation(self.name_label, "documentState", "loaded" if loaded else "empty")
        self.pages_label.setText(pages)
        self.pages_label.setVisible(bool(pages))
        description = " · ".join(part for part in (name, pages) if part)
        self.name_label.setAccessibleDescription(description)
        self._refresh()

    def _refresh(self):
        if not hasattr(self, "pages_label"):
            return
        label = self.name_label
        pages_width = self.pages_label.sizeHint().width() if self.pages_label.text() else 0
        available = max(0, self.width() - pages_width - (6 if pages_width else 0))
        width = min(available, label.fontMetrics().horizontalAdvance(self._name) + 2)
        label.setFixedWidth(width)
        label.setText(label.fontMetrics().elidedText(self._name, QtCore.Qt.ElideMiddle, width))
        align_label_baselines(label, self.pages_label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QtCore.QEvent.FontChange, QtCore.QEvent.StyleChange):
            self._refresh()


class CommandFocusFilter(QtCore.QObject):
    def eventFilter(self, widget, event):
        kind = event.type()
        if kind in (QtCore.QEvent.FocusIn, QtCore.QEvent.FocusOut,
                    QtCore.QEvent.MouseButtonPress, QtCore.QEvent.KeyPress):
            visible = kind == QtCore.QEvent.KeyPress or (
                kind == QtCore.QEvent.FocusIn and event.reason() in (
                    QtCore.Qt.TabFocusReason, QtCore.Qt.BacktabFocusReason, QtCore.Qt.ShortcutFocusReason))
            widget.setProperty("keyboardFocus", visible)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        return False


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
    def __init__(self, parent=None, *, compact=False, command=False):
        super().__init__(parent)
        self.setProperty("variant", "disclosure")
        self.setProperty("density", "compact" if compact else "regular")
        self.setProperty("emphasis", "command" if command else "quiet")
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


class MenuButton(KeyboardFocusMixin, QtWidgets.QToolButton):
    def __init__(self, parent=None, *, in_header=False, command=False):
        super().__init__(parent)
        self.setProperty("variant", "menu")
        self.setProperty("density", "header" if in_header else "regular")
        self.setProperty("emphasis", "command" if command else "quiet")
        self.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)


class InspectorHeader(QtWidgets.QWidget):
    """The same title and close affordance for the two inline tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.title = QtWidgets.QLabel(self)
        self.title.setObjectName("inspector_title")
        layout.addWidget(self.title)
        layout.addStretch(1)
        self.close_button = DetailButton(self, compact=True)
        self.close_button.setText("×")
        self.close_button.setProperty("variant", "utility")
        layout.addWidget(self.close_button)


class OutputSettingsDialog(QtWidgets.QDialog):
    """Output edits are a cancellable transaction, not a permanent form."""

    def __init__(self, parent, name, folder, validate, english=False):
        super().__init__(parent)
        self.setWindowTitle("Output settings" if english else "输出设置")
        self.setWindowModality(QtCore.Qt.WindowModal)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.name_edit = QtWidgets.QLineEdit(name, self)
        form.addRow("Filename" if english else "文件名", self.name_edit)
        directory = QtWidgets.QWidget(self)
        row = QtWidgets.QHBoxLayout(directory)
        row.setContentsMargins(0, 0, 0, 0)
        self.folder_edit = QtWidgets.QLineEdit(folder, self)
        self.folder_edit.setReadOnly(True)
        row.addWidget(self.folder_edit, 1)
        self.folder_button = QtWidgets.QPushButton("Choose…" if english else "选择…", self)
        configure_command(self.folder_button)
        row.addWidget(self.folder_button)
        self.folder_button.clicked.connect(lambda: self._choose_folder(english))
        form.addRow("Folder" if english else "保存到", directory)
        layout.addLayout(form)
        # A full Windows path can be hundreds of characters. A selectable,
        # horizontally navigable value keeps every character available without
        # letting wrapped metadata grow the dialog beyond the desktop window.
        self.path_label = QtWidgets.QLineEdit(self)
        self.path_label.setReadOnly(True)
        self.path_label.setAccessibleName("Full output path" if english else "完整输出路径")
        self.path_label.setMinimumWidth(0)
        self.path_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(self.path_label)
        source_note = QtWidgets.QLabel(
            "Creates a new PDF. The source remains unchanged." if english
            else "生成一份新 PDF，原文件保持不变。", self)
        source_note.setWordWrap(True)
        layout.addWidget(source_note)
        self.error_label = InlineErrorLabel(self)
        layout.addWidget(self.error_label)
        buttons = QtWidgets.QDialogButtonBox(self)
        cancel = buttons.addButton("Cancel" if english else "取消", QtWidgets.QDialogButtonBox.RejectRole)
        self.apply_button = buttons.addButton("Apply" if english else "应用", QtWidgets.QDialogButtonBox.AcceptRole)
        for button in (cancel, self.apply_button):
            configure_command(button)
        self.apply_button.setProperty("variant", "primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._validate = validate
        self.name_edit.textChanged.connect(self._refresh)
        self.folder_edit.textChanged.connect(self._refresh)
        # Top-level dialogs need the same resolved control roles as the shell,
        # including properties assigned after QDialogButtonBox creates buttons.
        self.setStyleSheet(parent.styleSheet())
        self.resize(540, self.sizeHint().height())
        self._refresh()
        self.name_edit.selectAll()

    def _choose_folder(self, english):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose output folder" if english else "选择输出文件夹",
            self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def _refresh(self):
        from pathlib import Path
        target = str(Path(self.folder_edit.text()) / self.name_edit.text())
        self.path_label.setText(target)
        self.path_label.setToolTip(target)
        self.path_label.setCursorPosition(0)
        error = self._validate(target, self.name_edit.text())
        self.error_label.setText(error)
        self.error_label.setVisible(bool(error))
        self.apply_button.setEnabled(not error)


class BookmarkItemDelegate(QtWidgets.QStyledItemDelegate):
    def set_source_line_height(self, height):
        if getattr(self, "_source_line_height", None) == height:
            return False
        self._source_line_height = height
        return True

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        # Cocoa adds native item padding; the comparison editor uses one
        # unwrapped text line. Keep both reading units on the same rhythm.
        size.setHeight(max(math.ceil(QtGui.QFontMetricsF(option.font).height()),
                           getattr(self, "_source_line_height", 0)))
        return size

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setProperty("variant", "cell-editor")
        editor.setFont(option.font)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        # A cell is not a form field: never let the global field height expand
        # it into its neighbour, or a long title cover the page columns.
        editor.setGeometry(option.rect)
