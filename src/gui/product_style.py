"""Shared type, control, and icon grammar for the bookmark workbench."""

from PySide6 import QtCore, QtGui, QtWidgets

from src.gui import icons_rc  # Registers the bundled selector arrow.

ERROR_COLOR = "#b43d3d"


class SelectListView(QtWidgets.QListView):
    def __init__(self, combo):
        super().__init__(combo)
        self.combo = combo

    def showEvent(self, event):
        super().showEvent(event)
        self.setCurrentIndex(self.model().index(self.combo.currentIndex(), 0))

    def currentChanged(self, current, previous):
        super().currentChanged(current, previous)
        if current.isValid():
            self.selectionModel().select(
                current, QtCore.QItemSelectionModel.ClearAndSelect
            )


def control_height(app_font):
    if app_font.pointSizeF() >= 18:
        return QtGui.QFontMetrics(app_font).height() + 12
    return 32


def configure_select(combo):
    # Use Qt's list popup on every platform. Mixing a native macOS menu with
    # a styled field leaves the arrow, selection, and popup geometry unrelated.
    style = QtWidgets.QStyleFactory.create("Fusion")
    style.setParent(combo)
    combo.setStyle(style)
    combo.setView(SelectListView(combo))
    combo.setItemDelegate(QtWidgets.QStyledItemDelegate(combo))
    combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
    combo.setMinimumContentsLength(6)


def icon(name):
    """Small monochrome toolbar symbols, drawn on the same 16-unit grid."""
    result = QtGui.QIcon()
    for mode, color in (
        (QtGui.QIcon.Normal, "#525b68"),
        (QtGui.QIcon.Disabled, "#b5bbc4"),
    ):
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.setDevicePixelRatio(2)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor(color), 1.4,
                                QtCore.Qt.SolidLine, QtCore.Qt.RoundCap,
                                QtCore.Qt.RoundJoin))
        path = QtGui.QPainterPath()
        if name == "folder":
            path.moveTo(2, 5)
            path.lineTo(2, 3.5)
            path.lineTo(6, 3.5)
            path.lineTo(7.5, 5)
            path.lineTo(14, 5)
            path.lineTo(14, 12.5)
            path.lineTo(2, 12.5)
            path.closeSubpath()
            path.moveTo(2, 7)
            path.lineTo(14, 7)
        elif name in ("chevron-right", "chevron-down"):
            if name == "chevron-down":
                painter.translate(16, 0)
                painter.rotate(90)
            path.moveTo(6, 4)
            path.lineTo(10, 8)
            path.lineTo(6, 12)
        elif name in ("undo", "redo"):
            if name == "redo":
                painter.translate(16, 0)
                painter.scale(-1, 1)
            path.moveTo(5, 3)
            path.lineTo(2, 6)
            path.lineTo(5, 9)
            path.moveTo(2, 6)
            path.lineTo(9, 6)
            path.cubicTo(14, 6, 14, 13, 9, 13)
            path.lineTo(6, 13)
        else:
            painter.drawEllipse(QtCore.QRectF(1.75, 1.75, 12.5, 12.5))
            if name == "info":
                path.moveTo(8, 7)
                path.lineTo(8, 11)
                painter.drawPoint(QtCore.QPointF(8, 4.8))
            else:
                path.moveTo(5.8, 5.7)
                path.cubicTo(6.1, 3.1, 10.7, 3.4, 10.1, 6)
                path.cubicTo(9.8, 7.2, 8, 7.1, 8, 9)
                painter.drawPoint(QtCore.QPointF(8, 11.4))
        painter.drawPath(path)
        painter.end()
        result.addPixmap(pixmap, mode)
    return result


def stylesheet(app_font):
    large = app_font.pointSizeF() >= 18
    size = app_font.pointSizeF() if large else 13
    unit = "pt" if large else "px"
    body = f"{size:g}{unit}"
    metadata = f"{max(size - 1, 12):g}{unit}"
    heading = f"{size if large else 15:g}{unit}"
    content = f"{size if large else 14:g}{unit}"
    height = control_height(app_font) - 2
    row = QtGui.QFontMetrics(app_font).height() + 6 if large else 24
    arrow = ":/pdfdir/chevron-down.svg"
    return f"""
        QWidget {{ font-family: "{app_font.family()}"; font-size: {body}; color: #252a32; }}
        QMainWindow, QWidget#main_widget, QFrame#workspace_frame,
        QWidget#editor_pane, QWidget#preview_pane, QWidget#pane_tools {{
            background: #ffffff;
        }}
        QFrame#document_frame, QFrame#action_frame {{
            background: #f7f8fa; border: 0; border-radius: 0;
        }}
        QFrame#document_frame {{ border-bottom: 1px solid #dfe3e8; }}
        QFrame#action_frame {{ border-top: 1px solid #dfe3e8; }}
        QSplitter::handle {{ background: #e4e7ec; width: 1px; }}
        QLabel {{ background: transparent; }}
        QLabel#document_name_label, QLabel#dir_text_label, QLabel#preview_label {{
            font-size: {heading}; font-weight: 600;
        }}
        QLabel#preview_count_label, QLabel#offset_formula_label,
        QLabel#output_location_label, QLabel#level_mode_label,
        QLabel#offset_label, QLabel#output_label {{
            color: #68707d; font-size: {metadata};
        }}
        QLabel#preview_empty_label {{ color: #7c8490; font-size: {body}; }}
        QLabel#action_status_label {{ color: #68707d; font-size: {body}; }}
        QLabel#action_status_label[statusKind="working"] {{ color: #246ac2; }}
        QLabel#action_status_label[statusKind="success"] {{ color: #26734d; }}
        QLabel#action_status_label[statusKind="error"],
        QLabel#regex_error_label, QLabel#output_error_label {{ color: {ERROR_COLOR}; }}

        QPushButton, QToolButton, QLineEdit, QComboBox {{
            min-height: {height}px; max-height: {height}px;
            border: 1px solid #d3d8e0; border-radius: 6px;
            background: #ffffff; color: #343b46; padding: 0 10px;
            font-size: {body}; font-weight: 400;
            selection-background-color: #dceaff; selection-color: #253e60;
        }}
        QPushButton:hover, QToolButton:hover, QComboBox:hover {{
            background: #f1f3f6; border-color: #bac2cd;
        }}
        QPushButton:pressed, QToolButton:pressed, QComboBox:on {{
            background: #e9edf3;
        }}
        QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus {{
            border-color: #4385d7;
        }}
        QPushButton:disabled, QToolButton:disabled, QLineEdit:disabled, QComboBox:disabled {{
            color: #a2a9b4; background: #f3f5f7; border-color: #e1e5eb;
        }}
        QPushButton[variant="quiet"], QToolButton[variant="quiet"],
        QPushButton[variant="icon"], QToolButton[variant="icon"] {{
            background: transparent; border-color: transparent;
        }}
        QPushButton[variant="quiet"]:hover, QToolButton[variant="quiet"]:hover,
        QPushButton[variant="icon"]:hover, QToolButton[variant="icon"]:hover {{
            background: #edf0f4;
        }}
        QPushButton[variant="quiet"]:focus, QToolButton[variant="quiet"]:focus,
        QPushButton[variant="icon"]:focus, QToolButton[variant="icon"]:focus {{
            border-color: #4385d7;
        }}
        QPushButton[variant="icon"], QToolButton[variant="icon"] {{
            min-width: {height}px; max-width: {height}px; padding: 0;
        }}
        QPushButton[variant="primary"] {{
            background: #2675d8; border-color: #2675d8; color: #ffffff;
            font-weight: 600; padding: 0 16px;
        }}
        QPushButton[variant="primary"]:hover {{ background: #1e66c0; border-color: #1e66c0; }}
        QPushButton[variant="primary"]:pressed {{ background: #1958a8; border-color: #1958a8; }}
        QPushButton[variant="primary"]:disabled {{ background: #e6eaf0; border-color: #e6eaf0; color: #929eaf; }}
        QToolButton#output_location_button {{
            color: #246ac2; font-size: {metadata}; padding: 0 4px;
            min-height: {height if large else 20}px; max-height: {height if large else 20}px;
        }}
        QLineEdit[invalid="true"] {{ border-color: #bf4747; background: #fff8f8; }}
        QComboBox {{ padding: 0 32px 0 10px; }}
        QComboBox::drop-down {{
            subcontrol-origin: padding; subcontrol-position: top right;
            width: 28px; border: 0; background: transparent;
        }}
        QComboBox::down-arrow {{ image: url("{arrow}"); width: 14px; height: 14px; }}
        QComboBox QAbstractItemView {{
            background: #ffffff; border: 1px solid #d3d8e0;
            border-radius: 6px; padding: 4px; outline: 0;
            selection-background-color: #e4efff; selection-color: #253e60;
        }}
        QComboBox QAbstractItemView::item {{ min-height: {height}px; padding: 0 8px; border: 0; }}
        QComboBox QAbstractItemView::item:selected {{ background: #e4efff; color: #253e60; }}
        QComboBox QAbstractItemView::item:hover {{ background: #f0f5fc; }}

        QPlainTextEdit#dir_text_edit {{
            font-size: {content}; color: #252a32; background: #ffffff;
            border: 0; padding: 8px 0;
            selection-background-color: #dceaff; selection-color: #253e60;
        }}
        QTreeWidget#dir_tree_widget {{
            font-size: {content}; color: #252a32; background: #ffffff;
            border: 0; show-decoration-selected: 1;
        }}
        QTreeWidget#dir_tree_widget::item {{
            min-height: {row - 1}px; padding: 0 6px;
            border: 0; border-bottom: 1px solid #f0f2f5;
        }}
        QTreeWidget#dir_tree_widget::item:hover {{ background: #f5f7fa; }}
        QTreeWidget#dir_tree_widget::item:selected {{ background: #e4efff; color: #253e60; }}
        QTreeWidget#dir_tree_widget::item:focus {{ border: 1px solid #aac9ef; }}
        QHeaderView::section {{
            font-size: {metadata}; font-weight: 400;
            color: #68707d; background: #ffffff;
            min-height: 26px; padding: 0 8px;
            border: 0; border-bottom: 1px solid #e4e7ec;
        }}
        QWidget#pane_tools {{ border-top: 1px solid #e4e7ec; }}
        QScrollArea#rules_scroll, QWidget#advanced_widget,
        QScrollArea#rules_scroll > QWidget > QWidget {{ background: #ffffff; }}
        QGroupBox#sub_dir_group {{ border: 0; margin: 0; padding: 0; }}
        QSplitter#rule_splitter::handle {{ background: #ffffff; }}
        QSplitter#rule_splitter::handle:hover {{ background: #dfe7f1; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; border: 0; }}
        QScrollBar::handle:vertical {{ background: #a3a9b2; min-height: 24px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: #7c8490; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QLineEdit[matchedRule="true"] {{ border-color: #82ace2; }}
    """
