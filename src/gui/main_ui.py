# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_ui.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QStatusBar,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_PDFdir(object):
    def setupUi(self, PDFdir):
        if not PDFdir.objectName():
            PDFdir.setObjectName(u"PDFdir")
        PDFdir.resize(859, 450)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(PDFdir.sizePolicy().hasHeightForWidth())
        PDFdir.setSizePolicy(sizePolicy)
        PDFdir.setMinimumSize(QSize(330, 450))
        PDFdir.setMaximumSize(QSize(1000000, 1000000))
        PDFdir.setAcceptDrops(True)
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
        self.keep_exist_dir_action = QAction(PDFdir)
        self.keep_exist_dir_action.setObjectName(u"keep_exist_dir_action")
        self.keep_exist_dir_action.setCheckable(True)
        self.read_exist_dir_action = QAction(PDFdir)
        self.read_exist_dir_action.setObjectName(u"read_exist_dir_action")
        self.read_exist_dir_action.setCheckable(True)
        self.read_exist_dir_action.setChecked(True)
        self.main_widget = QWidget(PDFdir)
        self.main_widget.setObjectName(u"main_widget")
        self.horizontalLayout_5 = QHBoxLayout(self.main_widget)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.pdf_path_label = QLabel(self.main_widget)
        self.pdf_path_label.setObjectName(u"pdf_path_label")

        self.verticalLayout.addWidget(self.pdf_path_label)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pdf_path_edit = QLineEdit(self.main_widget)
        self.pdf_path_edit.setObjectName(u"pdf_path_edit")

        self.horizontalLayout.addWidget(self.pdf_path_edit)

        self.open_button = QPushButton(self.main_widget)
        self.open_button.setObjectName(u"open_button")

        self.horizontalLayout.addWidget(self.open_button)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.dir_text_label = QLabel(self.main_widget)
        self.dir_text_label.setObjectName(u"dir_text_label")

        self.verticalLayout.addWidget(self.dir_text_label)

        self.space_level_box = QCheckBox(self.main_widget)
        self.space_level_box.setObjectName(u"space_level_box")
        font = QFont()
        font.setPointSize(10)
        font.setItalic(True)
        self.space_level_box.setFont(font)

        self.verticalLayout.addWidget(self.space_level_box)

        self.dir_text_edit = QTextEdit(self.main_widget)
        self.dir_text_edit.setObjectName(u"dir_text_edit")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setItalic(True)
        self.dir_text_edit.setFont(font1)
        self.dir_text_edit.setAcceptRichText(False)

        self.verticalLayout.addWidget(self.dir_text_edit)


        self.horizontalLayout_5.addLayout(self.verticalLayout)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_2)

        self.offset_label = QLabel(self.main_widget)
        self.offset_label.setObjectName(u"offset_label")

        self.verticalLayout_3.addWidget(self.offset_label)

        self.offset_edit = QLineEdit(self.main_widget)
        self.offset_edit.setObjectName(u"offset_edit")
        self.offset_edit.setMaximumSize(QSize(220, 16777215))
        self.offset_edit.setInputMethodHints(Qt.ImhDigitsOnly)
        self.offset_edit.setMaxLength(32767)

        self.verticalLayout_3.addWidget(self.offset_edit)

        self.sub_dir_group = QGroupBox(self.main_widget)
        self.sub_dir_group.setObjectName(u"sub_dir_group")
        self.sub_dir_group.setMaximumSize(QSize(240, 16777215))
        font2 = QFont()
        font2.setPointSize(10)
        font2.setBold(True)
        font2.setItalic(False)
        font2.setUnderline(False)
        font2.setKerning(True)
        self.sub_dir_group.setFont(font2)
        self.sub_dir_group.setAutoFillBackground(True)
        self.sub_dir_group.setAlignment(Qt.AlignCenter)
        self.sub_dir_group.setFlat(False)
        self.sub_dir_group.setCheckable(False)
        self.verticalLayout_2 = QVBoxLayout(self.sub_dir_group)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.level0_box = QCheckBox(self.sub_dir_group)
        self.level0_box.setObjectName(u"level0_box")

        self.verticalLayout_2.addWidget(self.level0_box)

        self.level0_edit = QLineEdit(self.sub_dir_group)
        self.level0_edit.setObjectName(u"level0_edit")
        self.level0_edit.setMaximumSize(QSize(220, 16777215))
        self.level0_edit.setEchoMode(QLineEdit.Normal)

        self.verticalLayout_2.addWidget(self.level0_edit)

        self.level1_box = QCheckBox(self.sub_dir_group)
        self.level1_box.setObjectName(u"level1_box")

        self.verticalLayout_2.addWidget(self.level1_box)

        self.level1_edit = QLineEdit(self.sub_dir_group)
        self.level1_edit.setObjectName(u"level1_edit")
        self.level1_edit.setMaximumSize(QSize(220, 16777215))

        self.verticalLayout_2.addWidget(self.level1_edit)

        self.level2_box = QCheckBox(self.sub_dir_group)
        self.level2_box.setObjectName(u"level2_box")

        self.verticalLayout_2.addWidget(self.level2_box)

        self.level2_edit = QLineEdit(self.sub_dir_group)
        self.level2_edit.setObjectName(u"level2_edit")
        self.level2_edit.setMaximumSize(QSize(220, 16777215))

        self.verticalLayout_2.addWidget(self.level2_edit)

        self.level3_box = QCheckBox(self.sub_dir_group)
        self.level3_box.setObjectName(u"level3_box")

        self.verticalLayout_2.addWidget(self.level3_box)

        self.level3_edit = QLineEdit(self.sub_dir_group)
        self.level3_edit.setObjectName(u"level3_edit")
        self.level3_edit.setMaximumSize(QSize(220, 16777215))

        self.verticalLayout_2.addWidget(self.level3_edit)

        self.level4_box = QCheckBox(self.sub_dir_group)
        self.level4_box.setObjectName(u"level4_box")

        self.verticalLayout_2.addWidget(self.level4_box)

        self.level4_edit = QLineEdit(self.sub_dir_group)
        self.level4_edit.setObjectName(u"level4_edit")
        self.level4_edit.setMaximumSize(QSize(220, 16777215))

        self.verticalLayout_2.addWidget(self.level4_edit)

        self.level5_box = QCheckBox(self.sub_dir_group)
        self.level5_box.setObjectName(u"level5_box")

        self.verticalLayout_2.addWidget(self.level5_box)

        self.level5_edit = QLineEdit(self.sub_dir_group)
        self.level5_edit.setObjectName(u"level5_edit")
        self.level5_edit.setMaximumSize(QSize(220, 16777215))

        self.verticalLayout_2.addWidget(self.level5_edit)

        self.unknown_level_label = QLabel(self.sub_dir_group)
        self.unknown_level_label.setObjectName(u"unknown_level_label")

        self.verticalLayout_2.addWidget(self.unknown_level_label)

        self.unknown_level_box = QComboBox(self.sub_dir_group)
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.addItem("")
        self.unknown_level_box.setObjectName(u"unknown_level_box")
        self.unknown_level_box.setMaximumSize(QSize(220, 16777215))

        self.verticalLayout_2.addWidget(self.unknown_level_box)


        self.verticalLayout_3.addWidget(self.sub_dir_group)


        self.horizontalLayout_5.addLayout(self.verticalLayout_3)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.preview_label = QLabel(self.main_widget)
        self.preview_label.setObjectName(u"preview_label")

        self.verticalLayout_4.addWidget(self.preview_label)

        self.dir_tree_widget = QTreeWidget(self.main_widget)
        font3 = QFont()
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setFont(1, font3)
        __qtreewidgetitem.setFont(0, font3)
        self.dir_tree_widget.setHeaderItem(__qtreewidgetitem)
        self.dir_tree_widget.setObjectName(u"dir_tree_widget")
        self.dir_tree_widget.setEnabled(True)
        font4 = QFont()
        font4.setPointSize(8)
        font4.setBold(False)
        self.dir_tree_widget.setFont(font4)
        self.dir_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dir_tree_widget.setAcceptDrops(True)
        self.dir_tree_widget.setAutoScroll(False)
        self.dir_tree_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.dir_tree_widget.setDragDropMode(QAbstractItemView.DragDrop)
        self.dir_tree_widget.setDefaultDropAction(Qt.MoveAction)
        self.dir_tree_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.dir_tree_widget.setAutoExpandDelay(1)
        self.dir_tree_widget.header().setVisible(True)
        self.dir_tree_widget.header().setCascadingSectionResizes(False)
        self.dir_tree_widget.header().setStretchLastSection(False)

        self.verticalLayout_4.addWidget(self.dir_tree_widget)


        self.horizontalLayout_5.addLayout(self.verticalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer)

        self.export_button = QPushButton(self.main_widget)
        self.export_button.setObjectName(u"export_button")

        self.verticalLayout_5.addWidget(self.export_button)


        self.horizontalLayout_5.addLayout(self.verticalLayout_5)

        PDFdir.setCentralWidget(self.main_widget)
        self.statusbar = QStatusBar(PDFdir)
        self.statusbar.setObjectName(u"statusbar")
        font5 = QFont()
        font5.setPointSize(7)
        self.statusbar.setFont(font5)
        PDFdir.setStatusBar(self.statusbar)
        self.menuBar = QMenuBar(PDFdir)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 859, 24))
        self.help_menu = QMenu(self.menuBar)
        self.help_menu.setObjectName(u"help_menu")
        self.language_menu = QMenu(self.menuBar)
        self.language_menu.setObjectName(u"language_menu")
        self.options_menu = QMenu(self.menuBar)
        self.options_menu.setObjectName(u"options_menu")
        PDFdir.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.options_menu.menuAction())
        self.menuBar.addAction(self.help_menu.menuAction())
        self.menuBar.addAction(self.language_menu.menuAction())
        self.help_menu.addAction(self.home_page_action)
        self.help_menu.addAction(self.help_action)
        self.help_menu.addAction(self.update_action)
        self.language_menu.addAction(self.english_action)
        self.language_menu.addAction(self.chinese_action)
        self.options_menu.addAction(self.fix_non_seq_action)
        self.options_menu.addAction(self.read_exist_dir_action)
        self.options_menu.addAction(self.keep_exist_dir_action)

        self.retranslateUi(PDFdir)

        QMetaObject.connectSlotsByName(PDFdir)
    # setupUi

    def retranslateUi(self, PDFdir):
        PDFdir.setWindowTitle(QCoreApplication.translate("PDFdir", u"PDFdir", None))
        self.home_page_action.setText(QCoreApplication.translate("PDFdir", u"\u4e3b\u9875", None))
        self.help_action.setText(QCoreApplication.translate("PDFdir", u"\u5e2e\u52a9\u624b\u518c", None))
        self.update_action.setText(QCoreApplication.translate("PDFdir", u"\u68c0\u67e5\u66f4\u65b0", None))
        self.english_action.setText(QCoreApplication.translate("PDFdir", u"English", None))
        self.chinese_action.setText(QCoreApplication.translate("PDFdir", u"\u4e2d\u6587", None))
        self.fix_non_seq_action.setText(QCoreApplication.translate("PDFdir", u"\u4fee\u590d\u4e71\u5e8f\u9875\u7801", None))
        self.fix_non_seq_action.setIconText(QCoreApplication.translate("PDFdir", u"\u4fee\u590d\u4e71\u5e8f\u9875\u7801", None))
        self.keep_exist_dir_action.setText(QCoreApplication.translate("PDFdir", u"\u4fdd\u7559\u5df2\u6709\u76ee\u5f55", None))
        self.read_exist_dir_action.setText(QCoreApplication.translate("PDFdir", u"\u8bfb\u53d6\u76ee\u5f55\u6587\u672c", None))
        self.pdf_path_label.setText(QCoreApplication.translate("PDFdir", u"PDF\u6587\u4ef6\u8def\u5f84", None))
        self.open_button.setText(QCoreApplication.translate("PDFdir", u"\u6253\u5f00", None))
        self.dir_text_label.setText(QCoreApplication.translate("PDFdir", u"\u76ee\u5f55\u6587\u672c", None))
        self.space_level_box.setText(QCoreApplication.translate("PDFdir", u"\u4ee5\u7a7a\u683c\u5206\u5c42", None))
        self.dir_text_edit.setHtml(QCoreApplication.translate("PDFdir", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"                                        <html><head><meta name=\"qrichtext\" content=\"1\"\n"
"                                        /><style type=\"text/css\">\n"
"                                        p, li { white-space: pre-wrap; }\n"
"                                        </style></head><body style=\"\n"
"                                        font-family:'.AppleSystemUIFont'; font-size:8pt; font-weight:400;\n"
"                                        font-style:italic;\">\n"
"                                        <p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px;\n"
"                                        margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\n"
"                                        font-family:'SimSun'; font-style:normal;\"><br /></p></body></html>\n"
"                                    ", None))
        self.offset_label.setText(QCoreApplication.translate("PDFdir", u"\u9875\u5dee", None))
        self.offset_edit.setInputMask("")
        self.offset_edit.setText(QCoreApplication.translate("PDFdir", u"0", None))
        self.sub_dir_group.setTitle(QCoreApplication.translate("PDFdir", u"\u76ee\u5f55\u5206\u5c42", None))
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
        self.unknown_level_label.setText(QCoreApplication.translate("PDFdir", u"\u672a\u8bc6\u522b", None))
        self.unknown_level_box.setItemText(0, QCoreApplication.translate("PDFdir", u"\u9996\u5c42", None))
        self.unknown_level_box.setItemText(1, QCoreApplication.translate("PDFdir", u"\u4e8c\u5c42", None))
        self.unknown_level_box.setItemText(2, QCoreApplication.translate("PDFdir", u"\u4e09\u5c42", None))
        self.unknown_level_box.setItemText(3, QCoreApplication.translate("PDFdir", u"\u56db\u5c42", None))
        self.unknown_level_box.setItemText(4, QCoreApplication.translate("PDFdir", u"\u4e94\u5c42", None))
        self.unknown_level_box.setItemText(5, QCoreApplication.translate("PDFdir", u"\u516d\u5c42", None))

        self.unknown_level_box.setCurrentText(QCoreApplication.translate("PDFdir", u"\u9996\u5c42", None))
        self.preview_label.setText(QCoreApplication.translate("PDFdir", u"\u9884\u89c8", None))
        ___qtreewidgetitem = self.dir_tree_widget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("PDFdir", u"\u5b9e\u9645\u9875\u6570", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("PDFdir", u"\u6807\u6ce8\u9875\u7801", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("PDFdir", u"\u76ee\u5f55", None))
        self.export_button.setText(QCoreApplication.translate("PDFdir", u"\u5199\u5165", None))
        self.help_menu.setTitle(QCoreApplication.translate("PDFdir", u"\u5e2e\u52a9", None))
        self.language_menu.setTitle(QCoreApplication.translate("PDFdir", u"\u8bed\u8a00", None))
        self.options_menu.setTitle(QCoreApplication.translate("PDFdir", u"\u9009\u9879", None))
    # retranslateUi
