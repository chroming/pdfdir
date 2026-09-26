"""Inline rule editing: one live preview, a recoverable trial, and source links."""

import re

from PySide6 import QtCore, QtGui, QtWidgets

from src.convert import split_page_num
from src.gui.product_style import configure_select, icon
from src.gui.base import SOURCE_ROLE, RULE_ROLE


class RuleWorkbenchMixin:
    def _build_rule_workbench(self):
        self._rule_baseline = None
        self._rules_pending = False
        self._rule_guarded = False
        self._rule_restore_running = False
        self._active_rule = None
        self._last_rule_values = None
        self._rules_timer = QtCore.QTimer(self)
        self._rules_timer.setSingleShot(True)
        self._rules_timer.setInterval(250)
        self._rules_timer.timeout.connect(self._apply_rule_preview)

        self.editor_layout.removeWidget(self.dir_text_edit)
        self.editor_layout.removeWidget(self.left_tools)
        self.rule_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.editor_pane)
        self.rule_splitter.setObjectName("rule_splitter")
        self.rule_splitter.setChildrenCollapsible(False)
        self.rule_splitter.setHandleWidth(5)
        self.rule_splitter.addWidget(self.dir_text_edit)
        self.rules_section = QtWidgets.QWidget(self.rule_splitter)
        section = QtWidgets.QVBoxLayout(self.rules_section)
        section.setContentsMargins(0, 0, 0, 0)
        section.setSpacing(8)
        section.addWidget(self.left_tools)
        self.rules_scroll = QtWidgets.QScrollArea(self.rules_section)
        self.rules_scroll.setObjectName("rules_scroll")
        self.rules_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.rules_scroll.setWidgetResizable(True)
        self.rules_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.rules_scroll.setWidget(self.advanced_widget)
        self.advanced_widget.setVisible(True)
        self.advanced_layout.setContentsMargins(0, 0, 8, 4)
        self.advanced_layout.setSpacing(8)
        section.addWidget(self.rules_scroll, 1)
        self.rule_splitter.addWidget(self.rules_section)
        self.rule_splitter.setStretchFactor(0, 1)
        self.rule_splitter.setStretchFactor(1, 0)
        self.editor_layout.addWidget(self.rule_splitter, 1)
        self.rules_scroll.hide()
        self.advanced_button.setCheckable(True)

        # The Designer fields remain the single owners of each rule. Only their
        # composition changes; all controls use product_style's shared grammar.
        self.sub_dir_group.setTitle("")
        self.sub_dir_group.setFlat(True)
        self.regex_grid.setContentsMargins(0, 0, 0, 0)
        self.regex_grid.setVerticalSpacing(6)
        self.rule_counts = []
        for i in range(6):
            box = getattr(self, f"level{i}_box")
            editor = getattr(self, f"level{i}_edit")
            self.regex_grid.removeWidget(box)
            self.regex_grid.removeWidget(editor)
            editor.setMinimumWidth(40)
            self.regex_grid.addWidget(box, i, 0)
            self.regex_grid.addWidget(editor, i, 1)
            count = QtWidgets.QToolButton(self.sub_dir_group)
            count.setProperty("variant", "quiet")
            count.clicked.connect(lambda _checked=False, rule=i: self._show_rule_matches(rule))
            self.rule_counts.append(count)
            self.regex_grid.addWidget(count, i, 2)
        for column in range(4):
            self.regex_grid.setColumnStretch(column, 1 if column == 1 else 0)

        self.regex_error_label = QtWidgets.QLabel(self.advanced_widget)
        self.regex_error_label.setObjectName("regex_error_label")
        self.regex_error_label.setWordWrap(True)
        self.regex_error_label.hide()
        self.advanced_layout.insertWidget(0, self.regex_error_label)
        self.rules_indent_hint = QtWidgets.QLabel(self.advanced_widget)
        self.rules_indent_hint.setWordWrap(True)
        self.advanced_layout.insertWidget(1, self.rules_indent_hint)

        self.rules_guard_label = QtWidgets.QLabel(self.advanced_widget)
        self.rules_guard_label.setWordWrap(True)
        self.rules_guard_label.hide()
        self.rules_accept_button = QtWidgets.QPushButton(self.advanced_widget)
        self.rules_accept_button.clicked.connect(self._accept_rule_trial)
        self.rules_accept_button.hide()
        self.advanced_layout.insertWidget(0, self.rules_accept_button)
        self.advanced_layout.insertWidget(0, self.rules_guard_label)

        while self.advanced_options_layout.count():
            self.advanced_options_layout.takeAt(0)
        self.rules_options_button = QtWidgets.QToolButton(self.advanced_widget)
        self.rules_options_button.setProperty("variant", "quiet")
        self.rules_options_button.setCheckable(True)
        self.rules_options_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.rules_options_button.setIcon(icon("chevron-right"))
        self.rules_options_button.toggled.connect(self._toggle_rule_options)
        self.advanced_layout.addWidget(self.rules_options_button, 0, QtCore.Qt.AlignLeft)
        self.rules_options = QtWidgets.QWidget(self.advanced_widget)
        options = QtWidgets.QVBoxLayout(self.rules_options)
        options.setContentsMargins(0, 0, 0, 0)
        self.rules_unmatched_layout = QtWidgets.QGridLayout()
        options.addLayout(self.rules_unmatched_layout)
        options.addWidget(self.fix_non_seq_box)
        options.addWidget(self.read_exist_dir_box)
        self.advanced_layout.addWidget(self.rules_options)
        self.rules_options.hide()
        self.rules_unmatched_button = QtWidgets.QToolButton(self.advanced_widget)
        self.rules_unmatched_button.setProperty("variant", "quiet")
        self.rules_unmatched_button.clicked.connect(lambda: self._show_rule_matches(-1))
        self.advanced_layout.addStretch(1)

        self.rules_restore_button = QtWidgets.QToolButton(self.rules_section)
        self.rules_restore_button.setProperty("variant", "quiet")
        self.rules_restore_button.clicked.connect(self._restore_rule_trial)
        self.rules_footer = QtWidgets.QWidget(self.rules_section)
        footer = QtWidgets.QHBoxLayout(self.rules_footer)
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(self.rules_restore_button)
        footer.addStretch(1)
        footer.addWidget(self.rules_unmatched_button)
        section.addWidget(self.rules_footer)
        self.rules_footer.hide()
        self.rules_restore_button.hide()
        self._rules_escape = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), self.rules_section)
        self._rules_escape.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self._rules_escape.activated.connect(
            lambda: self.advanced_button.click() if self.advanced_button.isChecked() else None
        )
        for combo in (self.level_mode_box, self.unknown_level_box):
            configure_select(combo)
        self.dir_tree_widget.currentItemChanged.connect(self._link_rule_source)

    def _translate_rule_workbench(self):
        english = self._language == "en"
        self.advanced_button.setText(
            ("Hide rules" if english else "收起规则") if self.advanced_button.isChecked()
            else ("Rules" if english else "规则")
        )
        self.advanced_button.setAccessibleDescription(
            "Show or hide the inline rule editor" if english else "展开或收起内嵌规则编辑区"
        )
        self.sub_dir_group.setTitle("")
        self.rules_indent_hint.setText(
            "Indent TOC lines to set their hierarchy; preview updates alongside."
            if english else "在上方调整目录缩进，右侧同步显示层级。"
        )
        self.rules_options_button.setText("More levels & handling" if english else "更多层级与处理")
        self.read_exist_dir_box.setText("Ask to import bookmarks" if english else "打开 PDF 时询问导入书签")
        self.fix_non_seq_box.setText("Keep pages in order" if english else "修正倒序页码")
        self.rules_restore_button.setText("Restore trial" if english else "恢复试调前")
        self.rules_restore_button.setToolTip(
            "Restore rules, TOC text, page offset and bookmarks from before this trial."
            if english else "恢复本次试调前的规则、目录文本、页差及书签；不修改 PDF。"
        )
        self.rules_guard_label.setText(
            "Preview has manual edits. Trying rules will replace them; a restore point is kept."
            if english else "书签已有手工修改。试调将重建书签，原修改会保留在恢复点中。"
        )
        self.rules_accept_button.setText("Try rules" if english else "试调规则")
        self._update_rule_rows()
        self._update_rule_feedback()

    def _toggle_rule_options(self, expanded):
        self.rules_options.setVisible(expanded)
        self.rules_options_button.setIcon(icon("chevron-down" if expanded else "chevron-right"))
        self._update_rule_rows()
        self.advanced_widget.layout().activate()

    def _update_rule_rows(self):
        for i, count in enumerate(self.rule_counts):
            box = getattr(self, f"level{i}_box")
            visible = i < 2 or box.isChecked() or self.rules_options_button.isChecked()
            for control in (box, getattr(self, f"level{i}_edit"), count):
                control.setVisible(visible)

    def _toggle_rule_workbench(self):
        """Show tools beside their live result, without changing the main shell."""
        expanded = self.advanced_button.isChecked()
        if expanded and self._rule_baseline is None:
            self._capture_rule_trial()
        self.rules_scroll.setVisible(expanded)
        self.rules_restore_button.setVisible(expanded)
        self.rules_footer.setVisible(expanded)
        self._resize_rule_workbench()
        self._translate_rule_workbench()
        if expanded:
            total = self.rule_splitter.height()
            self.rule_splitter.setSizes([max(100, total - 225), 225])
        else:
            self._active_rule = None
            self._highlight_rule_matches()
            self.advanced_button.setFocus()

    def _resize_rule_workbench(self):
        if not hasattr(self, "rules_section"):
            return
        expanded = self.advanced_button.isChecked()
        self.dir_text_edit.setMinimumHeight(
            self.dir_text_edit.fontMetrics().lineSpacing() * 3 + 12
        )
        line = self.rules_restore_button.sizeHint().height()
        self.rules_section.setMinimumHeight(self.left_tools.sizeHint().height() + line * 3 + 16 if expanded else 0)
        self.rules_section.setMaximumHeight(
            16777215 if expanded else self.left_tools.sizeHint().height()
        )
        layout = self.rules_unmatched_layout
        self._clear_layout(layout)
        layout.addWidget(self.unknown_level_label, 0, 0)
        layout.addWidget(self.unknown_level_box, 1 if self._large_text_mode() else 0,
                         0 if self._large_text_mode() else 1)
        layout.setColumnStretch(2, 1)

    def _rule_values(self):
        return (
            self.level_mode_box.currentIndex(),
            tuple((getattr(self, f"level{i}_box").isChecked(), getattr(self, f"level{i}_edit").text()) for i in range(6)),
            self.unknown_level_box.currentIndex(), self.fix_non_seq_box.isChecked(),
        )

    def _capture_rule_trial(self, values=None):
        tree = self.dir_tree_widget
        self._rule_baseline = {
            "values": values or self._rule_values(),
            "text": self.dir_text, "offset": self.offset_edit.text(),
            "items": tree._snapshot(),
            "view": self._capture_rule_view(),
            "manual": self._preview_manually_adjusted,
            "history": list(tree._history), "history_index": tree._history_index,
        }

    def _queue_rule_preview(self):
        if self._rule_restore_running or not hasattr(self, "_regex_editors"):
            return
        if self._rule_baseline is None:
            self._capture_rule_trial(self._last_rule_values)
        self._rules_pending = True
        self._update_rule_rows()
        self._rules_timer.stop()
        self._validate_regex_settings()
        if self._preview_manually_adjusted:
            if not self._rule_guarded:
                self._capture_rule_trial(self._last_rule_values)
            self._rule_guarded = True
            if not self.advanced_button.isChecked():
                self.advanced_button.click()
            self.rules_guard_label.show()
            self.rules_accept_button.show()
            self.rules_scroll.ensureWidgetVisible(self.rules_guard_label)
        if not self._rule_guarded and not self._regex_validation_error:
            # Debounce real typing, while discrete choices and programmatic
            # changes remain immediate and use the same guarded path.
            if self.focusWidget() in self._regex_editors:
                self._rules_timer.start()
            else:
                self._apply_rule_preview()
        self._refresh_dirty_state()
        self._update_action_availability()
        self._update_rule_feedback()

    def _accept_rule_trial(self):
        self._rule_guarded = False
        self._preview_manually_adjusted = False
        self.rules_guard_label.hide()
        self.rules_accept_button.hide()
        self._apply_rule_preview()

    def _apply_rule_preview(self):
        if self._close_requested or self._rule_guarded:
            return
        if self._preview_manually_adjusted:
            self._queue_rule_preview()
            return
        self.make_dir_tree()

    def _restore_rule_trial(self):
        state = self._rule_baseline
        if state is None or self._has_active_task():
            return
        self._rules_timer.stop()
        self._rule_restore_running = True
        controls = [self.level_mode_box, self.unknown_level_box, self.fix_non_seq_box,
                    self.dir_text_edit, self.offset_edit, *self._regex_boxes, *self._regex_editors]
        blockers = [QtCore.QSignalBlocker(control) for control in controls]
        mode, rules, unknown, fix = state["values"]
        self.level_mode_box.setCurrentIndex(mode)
        for (checked, text), box, editor in zip(rules, self._regex_boxes, self._regex_editors):
            box.setChecked(checked)
            editor.setText(text)
            editor.setEnabled(checked)
        self.unknown_level_box.setCurrentIndex(unknown)
        self.fix_non_seq_box.setChecked(fix)
        self.dir_text_edit.setPlainText(state["text"])
        self.offset_edit.setText(state["offset"])
        del blockers
        tree = self.dir_tree_widget
        self._rebuilding_tree = True
        tree._history_paused = True
        tree.load_snapshot(state["items"])
        tree._history = state["history"]
        tree._history_index = state["history_index"]
        tree._history_paused = False
        tree._update_history_actions()
        self._restore_rule_view(state["view"])
        self._rebuilding_tree = False
        self._preview_offset = self.offset_num
        self._preview_manually_adjusted = state["manual"]
        self._preview_validation_error = ""
        self._rule_restore_running = False
        self._clear_rule_trial()
        self._last_rule_values = self._rule_values()
        self._update_level_mode(mode)
        self.fix_non_seq_action.setChecked(fix)
        self._refresh_preview_hint()
        self._update_preview_empty_state()
        self._refresh_dirty_state()
        self._update_action_availability()

    def _clear_rule_trial(self):
        self._rules_timer.stop()
        self._rule_baseline = None
        self._rules_pending = False
        self._rule_guarded = False
        self.rules_guard_label.hide()
        self.rules_accept_button.hide()
        self._active_rule = None
        self._highlight_rule_matches()
        self._update_rule_rows()
        self._update_rule_feedback()

    def _capture_rule_view(self):
        tree = self.dir_tree_widget
        current = tree.currentItem()
        return {
            "expanded": {item.data(0, SOURCE_ROLE): item.isExpanded() for item in tree.all_items
                         if item.data(0, SOURCE_ROLE) is not None},
            "current": current.data(0, SOURCE_ROLE) if current else None,
            "scroll": tree.verticalScrollBar().value(),
        }

    def _restore_rule_view(self, state):
        for item in self.dir_tree_widget.all_items:
            key = item.data(0, SOURCE_ROLE)
            item.setExpanded(state["expanded"].get(key, True))
            if key is not None and key == state["current"]:
                self.dir_tree_widget.setCurrentItem(item)
        self.dir_tree_widget.verticalScrollBar().setValue(state["scroll"])

    def _annotate_rule_sources(self, items):
        blocker = QtCore.QSignalBlocker(self.dir_tree_widget)
        source_lines = [(number, line) for number, line in enumerate(self.dir_text.splitlines()) if line.strip()]
        patterns = [editor.text() if box.isChecked() else None for box, editor in zip(self._regex_boxes, self._regex_editors)]
        for index, item in items.items():
            number, line = source_lines[index]
            title, _page = split_page_num(line.rstrip())
            rule = next((i for i in reversed(range(6)) if patterns[i] and re.match(patterns[i], title)), -1) if not self.level_by_space else -2
            item.setData(0, SOURCE_ROLE, number)
            item.setData(0, RULE_ROLE, rule)
            item.setToolTip(0, self._source_description(number, rule))
        del blocker

    def _source_description(self, number, rule):
        if self._language == "en":
            kind = f"Rule {rule + 1}" if rule >= 0 else ("Indentation" if rule == -2 else "Unmatched · fallback level")
            return f"Source line {number + 1} · {kind}"
        kind = f"第 {rule + 1} 层规则" if rule >= 0 else ("按缩进" if rule == -2 else "未匹配 · 使用默认层级")
        return f"原文第 {number + 1} 行 · {kind}"

    def _update_rule_feedback(self):
        if not hasattr(self, "rule_counts"):
            return
        english = self._language == "en"
        counts = {i: 0 for i in range(-1, 6)}
        for item in self.dir_tree_widget.all_items:
            rule = item.data(0, RULE_ROLE)
            if rule in counts:
                counts[rule] += 1
        stale = self._rules_pending or bool(self._regex_validation_error)
        for i, button in enumerate(self.rule_counts):
            button.setText("—" if stale else str(counts[i]))
            button.setToolTip(("Show matches for rule {}" if english else "定位第 {} 层规则匹配的书签").format(i + 1))
            button.setAccessibleName(button.toolTip())
            button.setEnabled(bool(counts[i]) and not stale)
        self.rules_unmatched_button.setText(
            ("Unmatched: {}" if english else "未匹配：{} 条").format("—" if stale else counts[-1])
        )
        self.rules_unmatched_button.setVisible(not self.level_by_space)
        self.rules_unmatched_button.setEnabled(bool(counts[-1]) and not stale)
        state = self._rule_baseline
        changed = state is not None and (
            state["values"] != self._rule_values() or state["text"] != self.dir_text
            or state["offset"] != self.offset_edit.text()
            or state["items"] != self.dir_tree_widget._snapshot()
        )
        self.rules_restore_button.setEnabled(changed and not self._has_active_task())
        if stale:
            self.preview_count_label.setText("Not updated" if english else "尚未更新")
        else:
            count = sum(1 for _ in self.dir_tree_widget.all_items)
            self.preview_count_label.setText(("{} items" if english else "{} 条").format(count))

    def _show_rule_matches(self, rule):
        self._active_rule = rule
        self._highlight_rule_matches()
        item = next((item for item in self.dir_tree_widget.all_items if item.data(0, RULE_ROLE) == rule), None)
        if item:
            self.dir_tree_widget.setCurrentItem(item)
            self.dir_tree_widget.scrollToItem(item)

    def _highlight_rule_matches(self):
        blocker = QtCore.QSignalBlocker(self.dir_tree_widget)
        for item in self.dir_tree_widget.all_items:
            color = QtGui.QColor("#f0f5fc") if self._active_rule is not None and item.data(0, RULE_ROLE) == self._active_rule else QtGui.QColor()
            for column in range(3):
                item.setBackground(column, QtGui.QBrush(color) if color.isValid() else QtGui.QBrush())
        del blocker
        for i, editor in enumerate(getattr(self, "_regex_editors", ())):
            editor.setProperty("matchedRule", i == self._active_rule)
            editor.style().unpolish(editor)
            editor.style().polish(editor)

    def _link_rule_source(self, item, _previous):
        if self._rebuilding_tree or item is None:
            return
        number = item.data(0, SOURCE_ROLE)
        if number is None:
            return
        block = self.dir_text_edit.document().findBlockByNumber(number)
        if not block.isValid():
            return
        cursor = QtGui.QTextCursor(block)
        self.dir_text_edit.setTextCursor(cursor)
        self.dir_text_edit.ensureCursorVisible()
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format.setBackground(QtGui.QColor("#e4efff"))
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        self.dir_text_edit.setExtraSelections([selection])
        self.dir_text_edit.setToolTip(self._source_description(number, item.data(0, RULE_ROLE)))
        self._active_rule = item.data(0, RULE_ROLE)
        self._highlight_rule_matches()

    def _rule_event_filter(self, watched, event):
        if watched not in getattr(self, "_advanced_focus_chain", ()):
            return False
        if event.type() == QtCore.QEvent.FocusIn:
            self.rules_scroll.ensureWidgetVisible(watched)
            QtCore.QTimer.singleShot(0, lambda: self.rules_scroll.ensureWidgetVisible(watched))
            if watched in self._regex_editors:
                self._active_rule = self._regex_editors.index(watched)
                self._highlight_rule_matches()
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Escape and self.advanced_button.isChecked():
                self.advanced_button.click()
                return True
            if event.key() in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab):
                return self.focusNextPrevChild(not (event.modifiers() & QtCore.Qt.ShiftModifier or event.key() == QtCore.Qt.Key_Backtab))
        return False
