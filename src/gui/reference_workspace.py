"""Source/reference views beside the one authoritative bookmark draft."""

from PySide6 import QtCore, QtGui, QtWidgets

from src.gui.controls import DetailButton, DisclosureButton, MenuButton, ViewTabs, configure_command
from src.gui.pdf_reference import PdfReferencePane


class ReferenceWorkspaceMixin:
    def _build_reference_workspace(self):
        self.source_tabs = ViewTabs(self.editor_pane)
        self.source_tabs.addTab("")
        self.source_tabs.addTab("")
        self.dir_text_label.hide()
        self.source_import_button = MenuButton(self.editor_pane)
        import_menu = QtWidgets.QMenu(self.source_import_button)
        self.source_import_button.setMenu(import_menu)
        self.import_pdf_action = import_menu.addAction("")
        self.import_paste_action = import_menu.addAction("")
        self.import_pdf_action.triggered.connect(self.auto_toc_button.click)
        self.import_paste_action.triggered.connect(self.paste_button.click)
        self.auto_toc_button.hide()
        self.paste_button.hide()

        self.rules_section.layout().removeWidget(self.left_tools)
        self.left_tools_layout.setContentsMargins(0, 0, 0, 0)
        self.left_tools.setObjectName("context_tools")
        self.editor_layout.insertWidget(1, self.left_tools)
        self.editor_layout.removeWidget(self.rule_splitter)
        self.reference_stack = QtWidgets.QStackedWidget(self.editor_pane)
        self.reference_stack.addWidget(self.rule_splitter)
        self.pdf_reference = PdfReferencePane(self.editor_pane)
        self.reference_stack.addWidget(self.pdf_reference)
        self.editor_layout.addWidget(self.reference_stack, 1)
        self.rules_section.hide()
        self.source_tabs.currentChanged.connect(self._reference_tab_changed)

        self.preview_layout.removeWidget(self.right_tools)
        self.right_tools.setObjectName("context_tools")
        self.right_tools_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.insertWidget(1, self.right_tools)
        self.calibrate_button = DisclosureButton(self.preview_pane)
        self.calibrate_button.toggled.connect(self._toggle_calibration)
        self.offset_summary = QtWidgets.QLabel(self.preview_pane)
        self.offset_summary.setObjectName("offset_formula_label")
        self.hierarchy_button = MenuButton(self.preview_pane)
        hierarchy_menu = QtWidgets.QMenu(self.hierarchy_button)
        self.hierarchy_button.setMenu(hierarchy_menu)
        self.indent_action = hierarchy_menu.addAction("")
        self.outdent_action = hierarchy_menu.addAction("")
        self.indent_action.triggered.connect(lambda: self.dir_tree_widget.move_current_level(1))
        self.outdent_action.triggered.connect(lambda: self.dir_tree_widget.move_current_level(-1))
        hierarchy_menu.aboutToShow.connect(self._sync_hierarchy_actions)

        self.calibration_panel = QtWidgets.QWidget(self.preview_pane)
        calibration = QtWidgets.QGridLayout(self.calibration_panel)
        calibration.setContentsMargins(0, 0, 0, 8)
        calibration.setSpacing(8)
        self.printed_anchor = QtWidgets.QLineEdit("1", self.calibration_panel)
        self.pdf_anchor = QtWidgets.QLineEdit("1", self.calibration_panel)
        for field in (self.printed_anchor, self.pdf_anchor):
            field.setValidator(QtGui.QIntValidator(1, 2147483647, field))
            field.setMinimumWidth(56)
            field.setMaximumWidth(96)
            field.textChanged.connect(self._validate_calibration)
        self.printed_anchor_label = QtWidgets.QLabel(self.calibration_panel)
        self.pdf_anchor_label = QtWidgets.QLabel(self.calibration_panel)
        self.printed_anchor_label.setBuddy(self.printed_anchor)
        self.pdf_anchor_label.setBuddy(self.pdf_anchor)
        calibration.addWidget(self.printed_anchor_label, 0, 0)
        calibration.addWidget(self.pdf_anchor_label, 0, 1)
        calibration.addWidget(self.printed_anchor, 1, 0)
        calibration.addWidget(self.pdf_anchor, 1, 1)
        self.calibration_apply_button = QtWidgets.QPushButton(self.calibration_panel)
        configure_command(self.calibration_apply_button)
        self.calibration_apply_button.clicked.connect(self._apply_calibration)
        calibration.addWidget(self.calibration_apply_button, 1, 2, QtCore.Qt.AlignLeft)
        calibration.setColumnStretch(2, 1)
        self.calibration_error = QtWidgets.QLabel(self.calibration_panel)
        self.calibration_error.setObjectName("regex_error_label")
        self.calibration_error.setWordWrap(True)
        calibration.addWidget(self.calibration_error, 2, 0, 1, 3)
        self.calibration_direct = QtWidgets.QWidget(self.calibration_panel)
        direct = QtWidgets.QHBoxLayout(self.calibration_direct)
        direct.setContentsMargins(0, 0, 0, 0)
        direct.setSpacing(8)
        direct.addWidget(self.offset_label)
        direct.addWidget(self.offset_edit)
        direct.addStretch(1)
        direct.addWidget(self.auto_offset_button)
        calibration.addWidget(self.calibration_direct, 3, 0, 1, 3)
        self.offset_formula_label.hide()
        self.preview_layout.insertWidget(2, self.calibration_panel)
        self.calibration_panel.hide()
        self.pdf_reference.pageChanged.connect(self._calibration_page_changed)
        self._calibration_escape = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), self.calibration_panel)
        self._calibration_escape.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self._calibration_escape.activated.connect(lambda: self.calibrate_button.setChecked(False))

        self.guard_panel = QtWidgets.QWidget(self.preview_pane)
        guard = QtWidgets.QVBoxLayout(self.guard_panel)
        guard.setContentsMargins(0, 4, 0, 8)
        guard.setSpacing(6)
        guard.addWidget(self.rules_guard_label)
        guard_actions = QtWidgets.QHBoxLayout()
        guard_actions.addWidget(self.rules_accept_button)
        self.source_restore_button = DetailButton(self.guard_panel)
        self.source_restore_button.clicked.connect(self._restore_rule_trial)
        guard_actions.addWidget(self.source_restore_button)
        guard_actions.addStretch(1)
        guard.addLayout(guard_actions)
        self.preview_layout.insertWidget(3, self.guard_panel)
        self.guard_panel.hide()
        self.dir_tree_widget.currentItemChanged.connect(self._follow_bookmark_page)
        self._headers_large = None
        self._tools_layout_key = None
        self._layout_pane_headers()
        self._layout_tool_controls(False)

    def _layout_reference_headers(self):
        for layout in (self.source_header_layout, self.preview_header_layout):
            self._clear_layout(layout)
            for column in range(5):
                layout.setColumnStretch(column, 0)
        self.source_header_layout.addWidget(self.source_tabs, 0, 0)
        self.source_header_layout.setColumnStretch(1, 1)
        self.source_header_layout.addWidget(self.source_import_button, 0, 2)
        self.preview_header_layout.addWidget(self.preview_label, 0, 0)
        self.preview_header_layout.addWidget(self.preview_count_label, 0, 1)
        self.preview_header_layout.setColumnStretch(2, 1)
        self.preview_header_layout.addWidget(self.undo_button, 0, 3)
        self.preview_header_layout.addWidget(self.redo_button, 0, 4)

    def _layout_reference_tools(self):
        large = self._large_text_mode()
        self._tools_compact = large
        for layout in (self.left_tools_layout, self.right_tools_layout):
            self._clear_layout(layout)
            for column in range(5):
                layout.setColumnStretch(column, 0)
        self.level_mode_label.setVisible(not large)
        self.left_tools_layout.addWidget(self.level_mode_label, 0, 0)
        self.left_tools_layout.addWidget(self.level_mode_box, 0, 1)
        self.left_tools_layout.addWidget(self.advanced_button, 0, 2)
        self.left_tools_layout.setColumnStretch(3, 1)
        self.right_tools_layout.addWidget(self.hierarchy_button, 0, 0)
        self.right_tools_layout.setColumnStretch(1, 1)
        self.right_tools_layout.addWidget(self.offset_summary, 0, 2)
        self.right_tools_layout.addWidget(self.calibrate_button, 0, 3)
        self.offset_summary.setVisible(not large)
        english = self._language == "en"
        self.printed_anchor_label.setText(("Printed" if large else "Printed page") if english else "书上标注页")
        self.pdf_anchor_label.setText(("PDF" if large else "PDF page") if english else "对应 PDF 页")
        self.calibration_apply_button.setText(("Apply" if large else "Apply mapping") if english else "应用对应关系")
        self.pdf_reference.reflow(large)
        self.calibration_panel.setMinimumHeight(self.calibration_panel.layout().sizeHint().height())

    def _reference_tab_changed(self, index):
        self.reference_stack.setCurrentIndex(index)
        self.left_tools.setVisible(index == 0)
        self.source_import_button.setVisible(index == 0)
        if index == 1:
            self.pdf_reference.set_source(self.pdf_path.strip())
            self._follow_bookmark_page(self.dir_tree_widget.currentItem())

    def _follow_bookmark_page(self, item, _previous=None):
        if self.source_tabs.currentIndex() != 1 or item is None:
            return
        try:
            self.pdf_reference.go_to_page(int(item.text(2)))
        except ValueError:
            self.pdf_reference.show_group()

    def _toggle_calibration(self, expanded):
        self.calibration_panel.setVisible(expanded)
        if expanded:
            self.source_tabs.setCurrentIndex(1)
            item = self.dir_tree_widget.currentItem()
            try:
                printed = int(item.text(1)) if item else 1
            except ValueError:
                printed = 1
            self.printed_anchor.setText(str(printed))
            self.pdf_anchor.setText(str(max(1, printed + self.offset_num)))
            self._validate_calibration()
        else:
            self.calibrate_button.setFocus()

    def _calibration_page_changed(self, page):
        if self.calibrate_button.isChecked():
            self.pdf_anchor.setText(str(page))

    def _validate_calibration(self):
        if not hasattr(self, "calibration_error"):
            return
        valid = self.printed_anchor.hasAcceptableInput() and self.pdf_anchor.hasAcceptableInput()
        count = self._document_page_count
        in_range = valid and (not count or int(self.pdf_anchor.text()) <= count)
        self.calibration_apply_button.setEnabled(bool(in_range) and not self._has_active_task())
        self.calibration_error.setText(
            ("Enter a valid page in this PDF." if self._language == "en" else "请输入此 PDF 范围内的有效页码。")
            if not in_range else ""
        )
        self.calibration_error.setVisible(not in_range)

    def _apply_calibration(self):
        self._validate_calibration()
        if not self.calibration_apply_button.isEnabled():
            return
        page = int(self.pdf_anchor.text())
        offset = page - int(self.printed_anchor.text())
        self.offset_edit.setText(str(offset))
        self.pdf_reference.go_to_page(page)

    def _sync_hierarchy_actions(self):
        tree = self.dir_tree_widget
        self.indent_action.setEnabled(tree.can_move_current_level(1))
        self.outdent_action.setEnabled(tree.can_move_current_level(-1))

    def _sync_reference_workspace(self, has_pdf, write_running):
        self.import_pdf_action.setEnabled(self.auto_toc_button.isEnabled())
        self.import_paste_action.setEnabled(self.paste_button.isEnabled())
        self.source_import_button.setEnabled(not self._has_active_task())
        if self._rule_guarded and self.calibrate_button.isChecked():
            self.calibrate_button.setChecked(False)
        self.calibrate_button.setEnabled(has_pdf and not write_running and not self._rule_guarded)
        self.calibration_panel.setEnabled(has_pdf and not write_running)
        self.hierarchy_button.setEnabled(not write_running and self.dir_tree_widget.topLevelItemCount() > 0)
        manual_trial = self._rule_baseline and self._rule_baseline["manual"]
        self.guard_panel.setVisible(bool(self._rule_guarded or manual_trial))
        if self._rule_guarded:
            self.rules_guard_label.setText(
                "Source or rules changed. Your bookmark edits are preserved until you rebuild."
                if self._language == "en" else "原文或规则已变化。重新生成前，手工校对的书签会保留。"
            )
        elif manual_trial:
            self.rules_guard_label.hide()
        self.source_restore_button.setToolTip(
            "Restore the source, rules and manual bookmark edits from before rebuilding."
            if self._language == "en" else "恢复重新生成前的原文、规则与手工校对的书签。"
        )
        self.guard_panel.setEnabled(not write_running)
        self.source_restore_button.setEnabled(not self._has_active_task())
        self.offset_summary.setText(("Offset {:+d}" if self._language == "en" else "页差 {:+d}").format(self.offset_num))
        self.offset_summary.setToolTip(self.offset_edit.toolTip())
        if self.source_tabs.currentIndex() == 1:
            self.pdf_reference.set_source(self.pdf_path.strip() if has_pdf else "")
        self._validate_calibration()

    def _translate_reference_workspace(self):
        english = self._language == "en"
        self.source_tabs.setTabText(0, "TOC text" if english else "目录原文")
        self.source_tabs.setTabText(1, "PDF pages" if english else "PDF 页面")
        self.source_tabs.setAccessibleName("Reference view" if english else "参考视图")
        self.source_import_button.setText("Import" if english else "导入目录")
        self.level_mode_label.setText("Parse" if english else "识别")
        self.import_pdf_action.setText("Recognize from PDF…" if english else "从 PDF 识别…")
        self.import_paste_action.setText("Paste text" if english else "粘贴文本")
        self.hierarchy_button.setText("Hierarchy" if english else "调整层级")
        self.indent_action.setText("Indent bookmark" if english else "降低一级（缩进）")
        self.outdent_action.setText("Outdent bookmark" if english else "提升一级（取消缩进）")
        self.calibrate_button.setText("Calibrate" if english else "校准页码")
        self.printed_anchor_label.setText("Printed page" if english else "书上标注页")
        self.pdf_anchor_label.setText("PDF page" if english else "对应 PDF 页")
        self.calibration_apply_button.setText("Apply mapping" if english else "应用对应关系")
        self.source_restore_button.setText("Restore changes" if english else "恢复修改前")
        self.pdf_reference.set_language(self._language)
