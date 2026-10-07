"""Read-only PDF reference surface; bookmark editing never owns this document."""

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from src.gui.controls import DetailButton
from src.gui.product_style import configure_select

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
except ImportError:  # Some downstream Qt builds omit the PDF module.
    QPdfDocument = QPdfView = None


class PdfReferencePane(QtWidgets.QWidget):
    pageChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._language = "zh"
        self._source_key = None
        self._message = "empty"
        self._ready = False
        self.document = QPdfDocument(self) if QPdfDocument else None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.toolbar = QtWidgets.QWidget(self)
        bar = QtWidgets.QGridLayout(self.toolbar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(6)
        self.previous_button = DetailButton(self)
        self.previous_button.setText("‹")
        self.next_button = DetailButton(self)
        self.next_button.setText("›")
        self.page_edit = QtWidgets.QLineEdit(self)
        self.page_edit.setFixedWidth(56)
        self.page_edit.setAlignment(QtCore.Qt.AlignCenter)
        self.page_edit.setValidator(QtGui.QIntValidator(1, 2147483647, self))
        self.page_count_label = QtWidgets.QLabel(self)
        self.zoom_box = QtWidgets.QComboBox(self)
        configure_select(self.zoom_box)
        self.zoom_box.addItems(["", "", "100%", "150%"])
        for column, control in enumerate((self.previous_button, self.page_edit, self.page_count_label, self.next_button)):
            bar.addWidget(control, 0, column)
        bar.setColumnStretch(4, 1)
        bar.addWidget(self.zoom_box, 0, 5)
        layout.addWidget(self.toolbar)
        self.stack = QtWidgets.QStackedWidget(self)
        self.message_label = QtWidgets.QLabel(self)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("reference_message")
        self.stack.addWidget(self.message_label)
        self.view = QPdfView(self) if QPdfView else None
        if self.view:
            self.view.setDocument(self.document)
            self.view.setPageMode(QPdfView.PageMode.SinglePage)
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.stack.addWidget(self.view)
            self.view.pageNavigator().currentPageChanged.connect(self._page_changed)
        layout.addWidget(self.stack, 1)
        self.previous_button.clicked.connect(lambda: self.go_to_page(self.current_page - 1))
        self.next_button.clicked.connect(lambda: self.go_to_page(self.current_page + 1))
        self.page_edit.editingFinished.connect(self._page_entered)
        self.zoom_box.currentIndexChanged.connect(self._zoom_changed)
        self.set_language("zh")
        self._sync_controls()

    @property
    def current_page(self):
        return self.view.pageNavigator().currentPage() + 1 if self._ready else 0

    @property
    def page_count(self):
        return self.document.pageCount() if self._ready else 0

    def set_source(self, path):
        try:
            source = Path(path) if path else None
            stat = source.stat() if source else None
            key = (str(source), stat.st_size, stat.st_mtime_ns) if stat else None
        except OSError:
            key = None
        if key == self._source_key:
            return
        self._source_key = key
        self._ready = False
        self.stack.setCurrentWidget(self.message_label)
        if self.document:
            self.document.close()
        if not key:
            self._show_message("empty")
        elif not self.document:
            self._show_message("unavailable")
        else:
            error = self.document.load(str(source))
            if error != QPdfDocument.Error.None_ or not self.document.pageCount():
                self._show_message("error")
            else:
                self._ready = True
                self.go_to_page(1)
        self._sync_controls()

    def close_document(self):
        """Release native file ownership without leaving a stale source cache."""
        self._ready = False
        self._source_key = None
        if self.document:
            self.document.close()
        self._show_message("empty")
        self._sync_controls()

    def go_to_page(self, page):
        if not self._ready:
            return
        if not 1 <= page <= self.page_count:
            self._show_message("range")
            return
        self.view.pageNavigator().jump(page - 1, QtCore.QPointF())
        self.stack.setCurrentWidget(self.view)
        self._message = None
        self._sync_controls()

    def show_group(self):
        if self._ready:
            self._show_message("group")

    def _show_message(self, kind):
        self._message = kind
        self.stack.setCurrentWidget(self.message_label)
        self._translate_message()

    def _page_changed(self, index):
        self._sync_controls()
        self.pageChanged.emit(index + 1)

    def _page_entered(self):
        try:
            page = int(self.page_edit.text())
        except ValueError:
            page = self.current_page
        self.go_to_page(page)
        self._sync_controls()

    def _zoom_changed(self, index):
        if not self.view:
            return
        if index < 2:
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView if index == 0 else QPdfView.ZoomMode.FitToWidth)
        else:
            self.view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.view.setZoomFactor(1.0 if index == 2 else 1.5)

    def _sync_controls(self):
        self.toolbar.setEnabled(self._ready)
        self.page_edit.setText(str(self.current_page) if self._ready else "")
        self.page_count_label.setText(f"/ {self.page_count}" if self._ready else "/ —")
        self.page_edit.setFixedWidth(max(56, self.page_edit.fontMetrics().horizontalAdvance(str(self.page_count)) + 24))
        self.previous_button.setEnabled(self._ready and self.current_page > 1)
        self.next_button.setEnabled(self._ready and self.current_page < self.page_count)

    def reflow(self, large):
        layout = self.toolbar.layout()
        layout.removeWidget(self.zoom_box)
        layout.addWidget(self.zoom_box, 1 if large else 0, 0 if large else 5,
                         1, 6 if large else 1, QtCore.Qt.AlignLeft)
        self._sync_controls()

    def set_language(self, language):
        self._language = language
        english = language == "en"
        for button, text in ((self.previous_button, "Previous page" if english else "上一页"),
                             (self.next_button, "Next page" if english else "下一页")):
            button.setToolTip(text)
            button.setAccessibleName(text)
        self.page_edit.setAccessibleName("PDF page" if english else "PDF 页码")
        self.zoom_box.setAccessibleName("Zoom" if english else "缩放")
        self.zoom_box.setItemText(0, "Fit page" if english else "整页")
        self.zoom_box.setItemText(1, "Fit width" if english else "适合宽度")
        self._translate_message()

    def _translate_message(self):
        messages = {
            "empty": ("Open a PDF to compare its pages with bookmarks.", "打开 PDF 后，在这里对照页面与书签。"),
            "unavailable": ("PDF viewing is unavailable in this Qt build. Bookmark editing is still available.", "当前 Qt 环境不支持页面预览，仍可正常编辑和生成书签。"),
            "error": ("This PDF cannot be previewed (it may be encrypted or damaged). Bookmark editing is still available.", "无法预览此 PDF（可能已加密或损坏），仍可继续编辑书签。"),
            "range": ("The bookmark points outside this PDF. Calibrate pages or edit its page number.", "此书签超出 PDF 页数。请校准页码或修改该条书签。"),
            "group": ("This is a bookmark group without a destination page.", "这是书签分组，没有跳转页面。"),
        }
        if self._message:
            self.message_label.setText(messages[self._message][0 if self._language == "en" else 1])
