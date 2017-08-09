# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file './gui/main.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
	_fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
	def _fromUtf8(s):
		return s

try:
	_encoding = QtGui.QApplication.UnicodeUTF8
	def _translate(context, text, disambig):
		return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
	def _translate(context, text, disambig):
		return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		MainWindow.setObjectName(_fromUtf8("MainWindow"))
		MainWindow.resize(315, 386)
		sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
		MainWindow.setSizePolicy(sizePolicy)
		MainWindow.setMinimumSize(QtCore.QSize(315, 386))
		MainWindow.setMaximumSize(QtCore.QSize(315, 386))
		self.centralwidget = QtGui.QWidget(MainWindow)
		self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
		self.pdf_path_edit = QtGui.QLineEdit(self.centralwidget)
		self.pdf_path_edit.setGeometry(QtCore.QRect(9, 30, 217, 20))
		self.pdf_path_edit.setObjectName(_fromUtf8("pdf_path_edit"))
		self.open_button = QtGui.QPushButton(self.centralwidget)
		self.open_button.setGeometry(QtCore.QRect(237, 30, 70, 20))
		self.open_button.setObjectName(_fromUtf8("open_button"))
		self.dir_text_edit = QtGui.QTextEdit(self.centralwidget)
		self.dir_text_edit.setGeometry(QtCore.QRect(9, 87, 217, 244))
		self.dir_text_edit.setAcceptRichText(False)
		self.dir_text_edit.setObjectName(_fromUtf8("dir_text_edit"))
		self.export_button = QtGui.QPushButton(self.centralwidget)
		self.export_button.setGeometry(QtCore.QRect(237, 312, 70, 20))
		self.export_button.setObjectName(_fromUtf8("export_button"))
		self.label = QtGui.QLabel(self.centralwidget)
		self.label.setGeometry(QtCore.QRect(9, 9, 73, 16))
		self.label.setObjectName(_fromUtf8("label"))
		self.label_2 = QtGui.QLabel(self.centralwidget)
		self.label_2.setGeometry(QtCore.QRect(9, 66, 54, 12))
		self.label_2.setObjectName(_fromUtf8("label_2"))
		self.label_3 = QtGui.QLabel(self.centralwidget)
		self.label_3.setGeometry(QtCore.QRect(237, 66, 54, 12))
		self.label_3.setObjectName(_fromUtf8("label_3"))
		self.offset_edit = QtGui.QLineEdit(self.centralwidget)
		self.offset_edit.setGeometry(QtCore.QRect(237, 87, 70, 20))
		self.offset_edit.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
		self.offset_edit.setMaxLength(3)
		self.offset_edit.setObjectName(_fromUtf8("offset_edit"))
		MainWindow.setCentralWidget(self.centralwidget)
		self.statusbar = QtGui.QStatusBar(MainWindow)
		font = QtGui.QFont()
		font.setPointSize(7)
		self.statusbar.setFont(font)
		self.statusbar.setObjectName(_fromUtf8("statusbar"))
		MainWindow.setStatusBar(self.statusbar)
		self.menuBar = QtGui.QMenuBar(MainWindow)
		self.menuBar.setGeometry(QtCore.QRect(0, 0, 315, 23))
		self.menuBar.setObjectName(_fromUtf8("menuBar"))
		self.help_menu = QtGui.QMenu(self.menuBar)
		self.help_menu.setObjectName(_fromUtf8("help_menu"))
		MainWindow.setMenuBar(self.menuBar)
		self.home_page_action = QtGui.QAction(MainWindow)
		self.home_page_action.setObjectName(_fromUtf8("home_page_action"))
		self.help_action = QtGui.QAction(MainWindow)
		self.help_action.setObjectName(_fromUtf8("help_action"))
		self.update_action = QtGui.QAction(MainWindow)
		self.update_action.setObjectName(_fromUtf8("update_action"))
		self.help_menu.addAction(self.home_page_action)
		self.help_menu.addAction(self.help_action)
		self.help_menu.addAction(self.update_action)
		self.menuBar.addAction(self.help_menu.menuAction())

		self.retranslateUi(MainWindow)
		QtCore.QMetaObject.connectSlotsByName(MainWindow)

	def retranslateUi(self, MainWindow):
		MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
		self.open_button.setText(_translate("MainWindow", "打开", None))
		self.export_button.setText(_translate("MainWindow", "写入目录", None))
		self.label.setText(_translate("MainWindow", "PDF文件路径", None))
		self.label_2.setText(_translate("MainWindow", "目录文本", None))
		self.label_3.setText(_translate("MainWindow", "偏移页", None))
		self.offset_edit.setText(_translate("MainWindow", "0", None))
		self.help_menu.setTitle(_translate("MainWindow", "帮助", None))
		self.home_page_action.setText(_translate("MainWindow", "主页", None))
		self.help_action.setText(_translate("MainWindow", "帮助手册", None))
		self.update_action.setText(_translate("MainWindow", "检查更新", None))

