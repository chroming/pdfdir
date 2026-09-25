"""Plain-text TOC editor with a non-editable line-number gutter."""

from PySide6 import QtCore, QtGui, QtWidgets


class _LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QtCore.QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


class NumberedTextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_width()

    def append(self, text):
        """Preserve the QTextEdit API used by existing callers."""
        self.appendPlainText(text)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * max(2, digits)

    def _update_line_number_width(self, _count=0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.line_number_area.setGeometry(
            rect.left(), rect.top(), self.line_number_area_width(), rect.height()
        )

    def paint_line_numbers(self, event):
        painter = QtGui.QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QtGui.QColor("#f7f9fc"))
        painter.setPen(QtGui.QColor("#8b95a5"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        while block.isValid() and top <= event.rect().bottom():
            height = int(self.blockBoundingRect(block).height())
            if block.isVisible() and top + height >= event.rect().top():
                painter.drawText(
                    0, top, self.line_number_area.width() - 8, height,
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, str(number + 1),
                )
            block = block.next()
            number += 1
            top += height

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.FontChange:
            self._update_line_number_width()
