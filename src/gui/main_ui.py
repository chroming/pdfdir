# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.10.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QSplitter,
    QStatusBar, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_PDFdir(object):
    def setupUi(self, PDFdir):
        if not PDFdir.objectName():
            PDFdir.setObjectName(u"PDFdir")
        PDFdir.resize(1040, 720)
        PDFdir.setMinimumSize(QSize(780, 560))
        PDFdir.setStyleSheet(u"")
        self.home_page_action = QAction(PDFdir)
        self.home_page_action.setObjectName(u"home_page_action")
        self.help_action = QAction(PDFdir)
        self.help_action.setObjectName(u"help_action")
        self.update_action = QAction(PDFdir)
        self.update_action.setObjectName(u"update_action")
        self.english_action = QAction(PDFdir)
        self.english_action.setObjectName(u"english_action")
        self.chinese_action = QAction(PDFdir)
        self.chinese_action.setObjectName(u"chinese_action")
        self.fix_non_seq_action = QAction(PDFdir)
        self.fix_non_seq_action.setObjectName(u"fix_non_seq_action")
        self.fix_non_seq_action.setCheckable(True)
        self.fix_non_seq_action.setChecked(True)
        self.keep_exist_dir_action = QAction(PDFdir)
        self.keep_exist_dir_action.setObjectName(u"keep_exist_dir_action")
        self.keep_exist_dir_action.setCheckable(True)
        self.read_exist_dir_action = QAction(PDFdir)
        self.read_exist_dir_action.setObjectName(u"read_exist_dir_action")
        self.read_exist_dir_action.setCheckable(True)
        self.read_exist_dir_action.setChecked(True)
        self.main_widget = QWidget(PDFdir)
        self.main_widget.setObjectName(u"main_widget")
        self.root_layout = QVBoxLayout(self.main_widget)
        self.root_layout.setSpacing(12)
        self.root_layout.setObjectName(u"root_layout")
        self.root_layout.setContentsMargins(20, 16, 20, 14)
        self.file_layout = QHBoxLayout()
        self.file_layout.setSpacing(8)
        self.file_layout.setObjectName(u"file_layout")
        self.pdf_path_label = QLabel(self.main_widget)
        self.pdf_path_label.setObjectName(u"pdf_path_label")

        self.file_layout.addWidget(self.pdf_path_label)

        self.pdf_path_edit = QLineEdit(self.main_widget)
        self.pdf_path_edit.setObjectName(u"pdf_path_edit")
        self.pdf_path_edit.setClearButtonEnabled(True)

        self.file_layout.addWidget(self.pdf_path_edit)

        self.open_button = QPushButton(self.main_widget)
        self.open_button.setObjectName(u"open_button")

        self.file_layout.addWidget(self.open_button)


        self.root_layout.addLayout(self.file_layout)

        self.workspace_splitter = QSplitter(self.main_widget)
        self.workspace_splitter.setObjectName(u"workspace_splitter")
        self.workspace_splitter.setOrientation(Qt.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.editor_pane = QWidget(self.workspace_splitter)
        self.editor_pane.setObjectName(u"editor_pane")
        self.editor_layout = QVBoxLayout(self.editor_pane)
        self.editor_layout.setSpacing(6)
        self.editor_layout.setObjectName(u"editor_layout")
        self.editor_layout.setContentsMargins(0, 0, 6, 0)
        self.editor_header_layout = QHBoxLayout()
        self.editor_header_layout.setObjectName(u"editor_header_layout")
        self.dir_text_label = QLabel(self.editor_pane)
        self.dir_text_label.setObjectName(u"dir_text_label")

        self.editor_header_layout.addWidget(self.dir_text_label)

        self.editor_header_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.editor_header_layout.addItem(self.editor_header_spacer)

        self.auto_toc_button = QPushButton(self.editor_pane)
        self.auto_toc_button.setObjectName(u"auto_toc_button")

        self.editor_header_layout.addWidget(self.auto_toc_button)


        self.editor_layout.addLayout(self.editor_header_layout)

        self.editor_hint_label = QLabel(self.editor_pane)
        self.editor_hint_label.setObjectName(u"editor_hint_label")
        self.editor_hint_label.setWordWrap(True)

        self.editor_layout.addWidget(self.editor_hint_label)

        self.dir_text_edit = QTextEdit(self.editor_pane)
        self.dir_text_edit.setObjectName(u"dir_text_edit")
        self.dir_text_edit.setAcceptRichText(False)

        self.editor_layout.addWidget(self.dir_text_edit)

        self.workspace_splitter.addWidget(self.editor_pane)
        self.preview_pane = QWidget(self.workspace_splitter)
        self.preview_pane.setObjectName(u"preview_pane")
        self.preview_layout = QVBoxLayout(self.preview_pane)
        self.preview_layout.setSpacing(6)
        self.preview_layout.setObjectName(u"preview_layout")
        self.preview_layout.setContentsMargins(6, 0, 0, 0)
        self.preview_label = QLabel(self.preview_pane)
        self.preview_label.setObjectName(u"preview_label")

        self.preview_layout.addWidget(self.preview_label)

        self.preview_hint_label = QLabel(self.preview_pane)
        self.preview_hint_label.setObjectName(u"preview_hint_label")
        self.preview_hint_label.setWordWrap(True)

        self.preview_layout.addWidget(self.preview_hint_label)

        self.dir_tree_widget = QTreeWidget(self.preview_pane)
        self.dir_tree_widget.setObjectName(u"dir_tree_widget")
        self.dir_tree_widget.setAlternatingRowColors(False)
        self.dir_tree_widget.setRootIsDecorated(True)
        self.dir_tree_widget.setColumnCount(3)

        self.preview_layout.addWidget(self.dir_tree_widget)

        self.workspace_splitter.addWidget(self.preview_pane)

        self.root_layout.addWidget(self.workspace_splitter)

        self.quick_settings_layout = QHBoxLayout()
        self.quick_settings_layout.setSpacing(8)
        self.quick_settings_layout.setObjectName(u"quick_settings_layout")
        self.level_mode_label = QLabel(self.main_widget)
        self.level_mode_label.setObjectName(u"level_mode_label")

        self.quick_settings_layout.addWidget(self.level_mode_label)

        self.level_mode_box = QComboBox(self.main_widget)
        self.level_mode_box.addItem("")
        self.level_mode_box.addItem("")
        self.level_mode_box.setObjectName(u"level_mode_box")

        self.quick_settings_layout.addWidget(self.level_mode_box)

        self.offset_label = QLabel(self.main_widget)
        self.offset_label.setObjectName(u"offset_label")

        self.quick_settings_layout.addWidget(self.offset_label)

        self.offset_edit = QLineEdit(self.main_widget)
        self.offset_edit.setObjectName(u"offset_edit")
        self.offset_edit.setMaximumSize(QSize(72, 16777215))
        self.offset_edit.setAlignment(Qt.AlignCenter)

        self.quick_settings_layout.addWidget(self.offset_edit)

        self.auto_offset_button = QPushButton(self.main_widget)
        self.auto_offset_button.setObjectName(u"auto_offset_button")

        self.quick_settings_layout.addWidget(self.auto_offset_button)

        self.quick_settings_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.quick_settings_layout.addItem(self.quick_settings_spacer)

        self.advanced_button = QPushButton(self.main_widget)
        self.advanced_button.setObjectName(u"advanced_button")
        self.advanced_button.setCheckable(False)

        self.quick_settings_layout.addWidget(self.advanced_button)


        self.root_layout.addLayout(self.quick_settings_layout)

        self.advanced_widget = QWidget(self.main_widget)
        self.advanced_widget.setObjectName(u"advanced_widget")
        self.advanced_widget.setVisible(False)
        self.advanced_layout = QVBoxLayout(self.advanced_widget)
        self.advanced_layout.setSpacing(6)
        self.advanced_layout.setObjectName(u"advanced_layout")
        self.advanced_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_dir_group = QGroupBox(self.advanced_widget)
        self.sub_dir_group.setObjectName(u"sub_dir_group")
        self.regex_grid = QGridLayout(self.sub_dir_group)
        self.regex_grid.setObjectName(u"regex_grid")
        self.regex_grid.setHorizontalSpacing(8)
        self.regex_grid.setVerticalSpacing(5)
        self.level0_box = QCheckBox(self.sub_dir_group)
        self.level0_box.setObjectName(u"level0_box")

        self.regex_grid.addWidget(self.level0_box, 0, 0, 1, 1)

        self.level0_edit = QLineEdit(self.sub_dir_group)
        self.level0_edit.setObjectName(u"level0_edit")

        self.regex_grid.addWidget(self.level0_edit, 0, 1, 1, 1)

        self.level1_box = QCheckBox(self.sub_dir_group)
        self.level1_box.setObjectName(u"level1_box")

        self.regex_grid.addWidget(self.level1_box, 0, 2, 1, 1)

        self.level1_edit = QLineEdit(self.sub_dir_group)
        self.level1_edit.setObjectName(u"level1_edit")

        self.regex_grid.addWidget(self.level1_edit, 0, 3, 1, 1)

        self.level2_box = QCheckBox(self.sub_dir_group)
        self.level2_box.setObjectName(u"level2_box")

        self.regex_grid.addWidget(self.level2_box, 1, 0, 1, 1)

        self.level2_edit = QLineEdit(self.sub_dir_group)
        self.level2_edit.setObjectName(u"level2_edit")

        self.regex_grid.addWidget(self.level2_edit, 1, 1, 1, 1)

        self.level3_box = QCheckBox(self.sub_dir_group)
        self.level3_box.setObjectName(u"level3_box")

        self.regex_grid.addWidget(self.level3_box, 1, 2, 1, 1)

        self.level3_edit = QLineEdit(self.sub_dir_group)
        self.level3_edit.setObjectName(u"level3_edit")

        self.regex_grid.addWidget(self.level3_edit, 1, 3, 1, 1)

        self.level4_box = QCheckBox(self.sub_dir_group)
        self.level4_box.setObjectName(u"level4_box")

        self.regex_grid.addWidget(self.level4_box, 2, 0, 1, 1)

        self.level4_edit = QLineEdit(self.sub_dir_group)
        self.level4_edit.setObjectName(u"level4_edit")

        self.regex_grid.addWidget(self.level4_edit, 2, 1, 1, 1)

        self.level5_box = QCheckBox(self.sub_dir_group)
        self.level5_box.setObjectName(u"level5_box")

        self.regex_grid.addWidget(self.level5_box, 2, 2, 1, 1)

        self.level5_edit = QLineEdit(self.sub_dir_group)
        self.level5_edit.setObjectName(u"level5_edit")

        self.regex_grid.addWidget(self.level5_edit, 2, 3, 1, 1)


        self.advanced_layout.addWidget(self.sub_dir_group)

        self.advanced_options_layout = QHBoxLayout()
        self.advanced_options_layout.setObjectName(u"advanced_options_layout")
        self.unknown_level_label = QLabel(self.advanced_widget)
        self.unknown_level_label.setObjectName(u"unknown_level_label")

        self.advanced_options_layout.addWidget(self.unknown_level_label)

        self.unknown_level_box = QComboBox(self.advanced_widget)
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.setObjectName(u"unknown_level_box")

        self.advanced_options_layout.addWidget(self.unknown_level_box)

        self.fix_non_seq_box = QCheckBox(self.advanced_widget)
        self.fix_non_seq_box.setObjectName(u"fix_non_seq_box")
        self.fix_non_seq_box.setChecked(True)

        self.advanced_options_layout.addWidget(self.fix_non_seq_box)

        self.read_exist_dir_box = QCheckBox(self.advanced_widget)
        self.read_exist_dir_box.setObjectName(u"read_exist_dir_box")
        self.read_exist_dir_box.setChecked(True)

        self.advanced_options_layout.addWidget(self.read_exist_dir_box)

        self.advanced_options_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.advanced_options_layout.addItem(self.advanced_options_spacer)


        self.advanced_layout.addLayout(self.advanced_options_layout)


        self.root_layout.addWidget(self.advanced_widget)

        self.output_layout = QHBoxLayout()
        self.output_layout.setSpacing(8)
        self.output_layout.setObjectName(u"output_layout")
        self.keep_exist_dir_box = QCheckBox(self.main_widget)
        self.keep_exist_dir_box.setObjectName(u"keep_exist_dir_box")

        self.output_layout.addWidget(self.keep_exist_dir_box)

        self.output_label = QLabel(self.main_widget)
        self.output_label.setObjectName(u"output_label")

        self.output_layout.addWidget(self.output_label)

        self.output_path_edit = QLineEdit(self.main_widget)
        self.output_path_edit.setObjectName(u"output_path_edit")
        self.output_path_edit.setReadOnly(True)

        self.output_layout.addWidget(self.output_path_edit)

        self.cancel_button = QPushButton(self.main_widget)
        self.cancel_button.setObjectName(u"cancel_button")
        self.cancel_button.setVisible(False)

        self.output_layout.addWidget(self.cancel_button)

        self.export_button = QPushButton(self.main_widget)
        self.export_button.setObjectName(u"export_button")
        self.export_button.setEnabled(False)

        self.output_layout.addWidget(self.export_button)


        self.root_layout.addLayout(self.output_layout)

        PDFdir.setCentralWidget(self.main_widget)
        self.statusbar = QStatusBar(PDFdir)
        self.statusbar.setObjectName(u"statusbar")
        PDFdir.setStatusBar(self.statusbar)
        self.menuBar = QMenuBar(PDFdir)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1040, 24))
        self.help_menu = QMenu(self.menuBar)
        self.help_menu.setObjectName(u"help_menu")
        self.language_menu = QMenu(self.menuBar)
        self.language_menu.setObjectName(u"language_menu")
        PDFdir.setMenuBar(self.menuBar)
#if QT_CONFIG(shortcut)
        self.pdf_path_label.setBuddy(self.pdf_path_edit)
        self.dir_text_label.setBuddy(self.dir_text_edit)
        self.preview_label.setBuddy(self.dir_tree_widget)
        self.level_mode_label.setBuddy(self.level_mode_box)
        self.offset_label.setBuddy(self.offset_edit)
        self.unknown_level_label.setBuddy(self.unknown_level_box)
        self.output_label.setBuddy(self.output_path_edit)
#endif // QT_CONFIG(shortcut)
        QWidget.setTabOrder(self.pdf_path_edit, self.open_button)
        QWidget.setTabOrder(self.open_button, self.auto_toc_button)
        QWidget.setTabOrder(self.auto_toc_button, self.dir_text_edit)
        QWidget.setTabOrder(self.dir_text_edit, self.dir_tree_widget)
        QWidget.setTabOrder(self.dir_tree_widget, self.level_mode_box)
        QWidget.setTabOrder(self.level_mode_box, self.offset_edit)
        QWidget.setTabOrder(self.offset_edit, self.auto_offset_button)
        QWidget.setTabOrder(self.auto_offset_button, self.advanced_button)
        QWidget.setTabOrder(self.advanced_button, self.keep_exist_dir_box)
        QWidget.setTabOrder(self.keep_exist_dir_box, self.output_path_edit)
        QWidget.setTabOrder(self.output_path_edit, self.cancel_button)
        QWidget.setTabOrder(self.cancel_button, self.export_button)

        self.menuBar.addAction(self.help_menu.menuAction())
        self.menuBar.addAction(self.language_menu.menuAction())
        self.help_menu.addAction(self.home_page_action)
        self.help_menu.addAction(self.help_action)
        self.help_menu.addAction(self.update_action)
        self.language_menu.addAction(self.english_action)
        self.language_menu.addAction(self.chinese_action)

        self.retranslateUi(PDFdir)

        QMetaObject.connectSlotsByName(PDFdir)
    # setupUi

    def retranslateUi(self, PDFdir):
        PDFdir.setWindowTitle(QCoreApplication.translate("PDFdir", u"PDFdir", None))
        self.home_page_action.setText(QCoreApplication.translate("PDFdir", u"\u9879\u76ee\u4e3b\u9875", None))
        self.help_action.setText(QCoreApplication.translate("PDFdir", u"\u4f7f\u7528\u8bf4\u660e", None))
        self.update_action.setText(QCoreApplication.translate("PDFdir", u"\u68c0\u67e5\u66f4\u65b0", None))
        self.english_action.setText(QCoreApplication.translate("PDFdir", u"English", None))
        self.chinese_action.setText(QCoreApplication.translate("PDFdir", u"\u4e2d\u6587", None))
        self.fix_non_seq_action.setText(QCoreApplication.translate("PDFdir", u"\u4fee\u590d\u4e71\u5e8f\u9875\u7801", None))
        self.keep_exist_dir_action.setText(QCoreApplication.translate("PDFdir", u"\u4fdd\u7559\u5df2\u6709\u4e66\u7b7e", None))
        self.read_exist_dir_action.setText(QCoreApplication.translate("PDFdir", u"\u8bfb\u53d6\u5df2\u6709\u4e66\u7b7e", None))
        self.pdf_path_label.setText(QCoreApplication.translate("PDFdir", u"PDF \u6587\u4ef6", None))
        self.pdf_path_edit.setPlaceholderText(QCoreApplication.translate("PDFdir", u"\u9009\u62e9\u8981\u6dfb\u52a0\u4e66\u7b7e\u7684 PDF", None))
        self.open_button.setText(QCoreApplication.translate("PDFdir", u"\u9009\u62e9 PDF\u2026", None))
        self.dir_text_label.setText(QCoreApplication.translate("PDFdir", u"\u76ee\u5f55\u6587\u672c", None))
        self.auto_toc_button.setText(QCoreApplication.translate("PDFdir", u"\u4ece PDF \u8bc6\u522b\u76ee\u5f55", None))
        self.editor_hint_label.setText(QCoreApplication.translate("PDFdir", u"\u6bcf\u884c\u8f93\u5165\u6807\u9898\u548c\u6807\u6ce8\u9875\u7801\uff1b\u53ef\u76f4\u63a5\u7f16\u8f91\u8bc6\u522b\u7ed3\u679c\u3002", None))
        self.dir_text_edit.setPlaceholderText(QCoreApplication.translate("PDFdir", u"\u793a\u4f8b\uff1a\n"
"\u7b2c 1 \u7ae0 \u5165\u95e8  1\n"
"  1.1 \u5b89\u88c5  3", None))
        self.dir_text_edit.setPlainText("")
        self.preview_label.setText(QCoreApplication.translate("PDFdir", u"\u4e66\u7b7e\u9884\u89c8", None))
        self.preview_hint_label.setText(QCoreApplication.translate("PDFdir", u"\u786e\u8ba4\u5c42\u7ea7\u4e0e\u5b9e\u9645 PDF \u9875\u7801\u540e\u518d\u751f\u6210\u3002", None))
        ___qtreewidgetitem = self.dir_tree_widget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("PDFdir", u"PDF \u9875\u7801", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("PDFdir", u"\u6807\u6ce8\u9875\u7801", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("PDFdir", u"\u4e66\u7b7e\u6807\u9898", None))
        self.level_mode_label.setText(QCoreApplication.translate("PDFdir", u"\u5c42\u7ea7\u8bc6\u522b", None))
        self.level_mode_box.setItemText(0, QCoreApplication.translate("PDFdir", u"\u6309\u7f29\u8fdb\u8bc6\u522b\u5c42\u7ea7", None))
        self.level_mode_box.setItemText(1, QCoreApplication.translate("PDFdir", u"\u6309\u7f16\u53f7\u89c4\u5219\u8bc6\u522b\u5c42\u7ea7", None))

        self.offset_label.setText(QCoreApplication.translate("PDFdir", u"\u9875\u5dee", None))
#if QT_CONFIG(tooltip)
        self.offset_edit.setToolTip(QCoreApplication.translate("PDFdir", u"PDF \u9875\u7801\u51cf\u53bb\u4e66\u4e0a\u6807\u6ce8\u9875\u7801", None))
#endif // QT_CONFIG(tooltip)
        self.offset_edit.setText(QCoreApplication.translate("PDFdir", u"0", None))
        self.auto_offset_button.setText(QCoreApplication.translate("PDFdir", u"\u8bc6\u522b\u9875\u5dee", None))
        self.advanced_button.setText(QCoreApplication.translate("PDFdir", u"\u8bc6\u522b\u8bbe\u7f6e\u2026", None))
        self.sub_dir_group.setTitle(QCoreApplication.translate("PDFdir", u"\u7f16\u53f7\u89c4\u5219\uff08\u6b63\u5219\u8868\u8fbe\u5f0f\uff09", None))
        self.level0_box.setText(QCoreApplication.translate("PDFdir", u"\u9996\u5c42", None))
        self.level0_edit.setText(QCoreApplication.translate("PDFdir", u"^\\d+\\.\\s?", None))
        self.level1_box.setText(QCoreApplication.translate("PDFdir", u"\u4e8c\u5c42", None))
        self.level1_edit.setText(QCoreApplication.translate("PDFdir", u"^\\d+\\.\\d+\\w?\\s?", None))
        self.level2_box.setText(QCoreApplication.translate("PDFdir", u"\u4e09\u5c42", None))
        self.level2_edit.setText(QCoreApplication.translate("PDFdir", u"^\\d+\\.\\d+\\.\\d+\\w?\\s?", None))
        self.level3_box.setText(QCoreApplication.translate("PDFdir", u"\u56db\u5c42", None))
        self.level3_edit.setText(QCoreApplication.translate("PDFdir", u"^\\d+\\.\\d+\\.\\d+\\.\\d+\\w?\\s?", None))
        self.level4_box.setText(QCoreApplication.translate("PDFdir", u"\u4e94\u5c42", None))
        self.level4_edit.setText(QCoreApplication.translate("PDFdir", u"^\\d+\\.\\d+\\.\\d+\\.\\d+\\.\\d+\\w?\\s?", None))
        self.level5_box.setText(QCoreApplication.translate("PDFdir", u"\u516d\u5c42", None))
        self.level5_edit.setText(QCoreApplication.translate("PDFdir", u"^\\d+\\.\\d+\\.\\d+\\.\\d+\\.\\d+\\.\\d+\\w?\\s?", None))
        self.unknown_level_label.setText(QCoreApplication.translate("PDFdir", u"\u672a\u8bc6\u522b\u884c\u4f5c\u4e3a", None))
        self.unknown_level_box.setItemText(0, QCoreApplication.translate("PDFdir", u"\u9996\u5c42", None))
        self.unknown_level_box.setItemText(1, QCoreApplication.translate("PDFdir", u"\u4e8c\u5c42", None))
        self.unknown_level_box.setItemText(2, QCoreApplication.translate("PDFdir", u"\u4e09\u5c42", None))
        self.unknown_level_box.setItemText(3, QCoreApplication.translate("PDFdir", u"\u56db\u5c42", None))
        self.unknown_level_box.setItemText(4, QCoreApplication.translate("PDFdir", u"\u4e94\u5c42", None))
        self.unknown_level_box.setItemText(5, QCoreApplication.translate("PDFdir", u"\u516d\u5c42", None))

        self.fix_non_seq_box.setText(QCoreApplication.translate("PDFdir", u"\u6cbf\u7528\u4e0a\u4e00\u6709\u6548\u9875\u7801\uff0c\u4fee\u590d\u4e71\u5e8f\u6216\u7f3a\u5931\u9875\u7801", None))
        self.read_exist_dir_box.setText(QCoreApplication.translate("PDFdir", u"\u6253\u5f00 PDF \u65f6\u8be2\u95ee\u662f\u5426\u5bfc\u5165\u5df2\u6709\u4e66\u7b7e", None))
        self.keep_exist_dir_box.setText(QCoreApplication.translate("PDFdir", u"\u4fdd\u7559\u5df2\u6709\u4e66\u7b7e", None))
        self.output_label.setText(QCoreApplication.translate("PDFdir", u"\u8f93\u51fa", None))
        self.output_path_edit.setPlaceholderText(QCoreApplication.translate("PDFdir", u"\u9009\u62e9 PDF \u540e\u663e\u793a\u8f93\u51fa\u4f4d\u7f6e", None))
        self.cancel_button.setText(QCoreApplication.translate("PDFdir", u"\u53d6\u6d88\u4efb\u52a1", None))
        self.export_button.setText(QCoreApplication.translate("PDFdir", u"\u751f\u6210\u5e26\u4e66\u7b7e\u7684 PDF", None))
        self.help_menu.setTitle(QCoreApplication.translate("PDFdir", u"\u5e2e\u52a9", None))
        self.language_menu.setTitle(QCoreApplication.translate("PDFdir", u"\u8bed\u8a00", None))
    # retranslateUi
