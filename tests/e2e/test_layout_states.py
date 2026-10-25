"""State-pair evidence for the comparison workspace, not just a happy screen.

Set PDFDIR_UI_CAPTURE_DIR to retain the rendered native Qt evidence and manifest.
"""

import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtGui
from pypdf import PdfReader

import src.gui.main as main_module
from tests.gui_test_utils import track_main_window, edit_output_settings


@pytest.mark.e2e
@pytest.mark.parametrize("size", [(780, 560), (1100, 760), (1440, 900)])
@pytest.mark.parametrize("language", ["zh", "en"])
def test_comparison_workspace_state_pairs(qapp, qtbot, tmp_path, size, language):
    source = tmp_path / "软件设计实践.pdf"
    writer = QtGui.QPdfWriter(str(source))
    painter = QtGui.QPainter(writer)
    for page in range(1, 33):
        if page > 1:
            writer.newPage()
        painter.setFont(QtGui.QFont(qapp.font().family(), 24))
        painter.drawText(100, 300, "软件设计实践 · Software product design")
        painter.setFont(QtGui.QFont(qapp.font().family(), 14))
        painter.drawText(100, 600, f"用户目标、使用场景与关键决策 / Page {page}")
    painter.end()
    del writer
    original = source.read_bytes()
    window = main_module.Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    (window.to_english if language == "en" else window.to_chinese)()
    window.show()
    window.raise_()
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    if qapp.platformName() == "windows":
        available = window.screen().availableGeometry().size()
        chrome = window.frameGeometry().size() - window.size()
        if size[0] + chrome.width() > available.width() or size[1] + chrome.height() > available.height():
            pytest.skip(f"Native Windows desktop {available.width()}x{available.height()} cannot render viewport {size}")
    window.resize(*size)
    window.read_exist_dir_box.setChecked(False)
    assert window._activate_document(str(source))
    lines = []
    for chapter, title in enumerate(("理解用户", "信息架构", "交互设计", "视觉与布局", "验证与交付"), 1):
        lines.append(f"第{chapter}章 {title} {chapter * 5}")
        for section, subtitle in enumerate(("用户目标与使用场景", "任务流程与关键决策", "复杂信息的组织方式"), 1):
            lines.append(f"  {chapter}.{section} {subtitle} {chapter * 5 + section}")
    text = "\n".join(lines)
    window.dir_text_edit.setPlainText(text)
    capture_dir = os.environ.get("PDFDIR_UI_CAPTURE_DIR")
    folder = Path(capture_dir) / f"{language}-{size[0]}" if capture_dir else None
    if folder:
        folder.mkdir(parents=True, exist_ok=True)
    states = {}

    def capture(name, settle=True):
        if settle:
            qtbot.wait(35)
        assert window.size() == QtCore.QSize(*size)
        assert window.dir_tree_widget.horizontalScrollBar().maximum() == 0
        header = window.dir_tree_widget.header()
        edit = window.hierarchy_button
        assert header.viewport().rect().contains(edit.geometry())
        for index in range(window.source_tabs.count()):
            assert window.source_tabs.rect().contains(window.source_tabs.tabRect(index))
        command = window.cancel_button if window.cancel_button.isVisible() else window.export_button
        for widget in (command, window.action_status_label, window.dir_tree_widget):
            rect = QtCore.QRect(widget.mapTo(window, QtCore.QPoint()), widget.size())
            assert window.rect().contains(rect)
        if folder:
            assert window.grab().save(str(folder / f"{name}.png"))
        states[name] = {
            "source_height": window.dir_text_edit.height(),
            "bookmarks_height": window.dir_tree_widget.height(),
            "primary_width": command.width(),
            "footer": window.action_frame.geometry().getRect(),
        }

    capture("source")
    def baseline(label):
        ink = label.fontMetrics().boundingRect(label.contentsRect(), int(label.alignment()), label.text())
        return label.mapTo(window, ink.topLeft()).y() + label.fontMetrics().ascent()
    assert abs(baseline(window.preview_label) - baseline(window.preview_count_label)) <= 1
    editor, tree = window.dir_text_edit, window.dir_tree_widget
    source_origin = editor.viewport().mapTo(window, QtCore.QPoint()).y()
    tree_origin = tree.viewport().mapTo(window, QtCore.QPoint()).y()
    for index, item in enumerate(tree.all_items):
        block = editor.document().findBlockByNumber(index)
        source_rect = editor.blockBoundingGeometry(block).translated(editor.contentOffset())
        tree_rect = tree.visualItemRect(item)
        assert abs(source_origin + source_rect.top() - tree_origin - tree_rect.top()) <= 1
    qtbot.mouseClick(window.source_tabs, QtCore.Qt.LeftButton,
                     pos=window.source_tabs.tabRect(1).center())
    capture("pdf-pointer")
    window.dir_tree_widget.setFocus()
    window.source_tabs.setFocus(QtCore.Qt.TabFocusReason)
    qtbot.keyClick(window.source_tabs, QtCore.Qt.Key_Left)
    capture("source-keyboard")
    qtbot.mouseClick(window.advanced_button, QtCore.Qt.LeftButton)
    capture("indent-rules")
    window.level_mode_box.setCurrentIndex(1)
    assert window.level0_box.isChecked() and window.level1_box.isChecked()
    capture("numbering-defaults")
    for index, pattern in enumerate((r"^第\d+章", r"^\s*\d+\.\d+\s", r"^\s*\d+\.\d+\.\d+\s")):
        window._add_rule_level(index)
        getattr(window, f"level{index}_edit").setText(pattern)
    qtbot.waitUntil(lambda: not window._rules_pending)
    capture("three-rules")
    if size[0] == 780:
        assert window.rules_scroll.verticalScrollBar().maximum() == 0
        viewport = window.rules_scroll.viewport()
        for control in (window.unknown_level_box, window.fix_non_seq_box):
            assert viewport.rect().contains(QtCore.QRect(
                control.mapTo(viewport, QtCore.QPoint()), control.size()))
        for button in window.rule_counts[:3]:
            assert viewport.rect().contains(QtCore.QRect(
                button.mapTo(viewport, QtCore.QPoint()), button.size()))
    assert window.rules_options.isVisible()
    window.level1_box.setChecked(False)
    capture("disabled-rule")
    assert window.level1_box.isVisible()
    for index in (0, 2):
        getattr(window, f"level{index}_box").setChecked(False)
    before = window._tree_snapshot()
    capture("no-rules")
    assert not window.export_button.isEnabled()
    assert window._tree_snapshot() == before
    for index in range(3):
        getattr(window, f"level{index}_box").setChecked(True)
    qtbot.waitUntil(lambda: not window._rules_pending)
    window.level0_edit.setText("[")
    capture("rule-error")
    window.level0_edit.setText(r"^第\d+章")
    qtbot.waitUntil(lambda: not window._rules_pending)
    window.advanced_button.click()
    capture("rules-closed")
    window.calibrate_button.click()
    capture("calibration")
    signature = window._current_draft_signature()
    window.calibration_offset.setText("2")
    capture("offset-candidate")
    assert window._current_draft_signature() == signature
    window.pdf_anchor.setText("999")
    capture("calibration-error")
    qtbot.keyClick(window.pdf_anchor, QtCore.Qt.Key_Escape)
    capture("calibration-closed")
    assert window.source_tabs.currentIndex() == 0
    assert window._current_draft_signature() == signature
    window.dir_tree_widget.topLevelItem(0).setText(0, "手工校对的标题 / Corrected title")
    window.dir_text_edit.appendPlainText("附录 31")
    capture("manual-edit-guard")
    assert not window.export_button.isEnabled()
    window.source_restore_button.click()
    window.dir_text_edit.setPlainText("前言 iii")
    window.rules_accept_button.click()
    assert window.source_error_label.isVisible()
    capture("source-error")
    window.source_restore_button.click()
    # Repeated reversal cannot leave stale geometry or lose the draft.
    signature = window._current_draft_signature()
    for _ in range(5):
        window.source_tabs.setCurrentIndex(1)
        window.source_tabs.setCurrentIndex(0)
        window.advanced_button.click()
        window.advanced_button.click()
    assert window._current_draft_signature() == signature
    capture("ready")
    assert not window.guard_panel.isVisible()
    tree_before_export = window.dir_tree_widget.geometry()
    def inspect_output(dialog):
        if folder:
            assert dialog.grab().save(str(folder / "output-settings.png"))
        assert dialog.apply_button.isEnabled()
    edit_output_settings(window, qtbot, name="cancelled.pdf", accept=False, inspect=inspect_output)
    assert window._current_draft_signature() == signature
    window.export_button.click()
    window._reflow_controls()
    capture("working", settle=False)
    assert not window.guard_panel.isVisible()
    assert window.dir_tree_widget.geometry() == tree_before_export
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=15000)
    capture("result")
    assert not window.guard_panel.isVisible()
    assert window.dir_tree_widget.geometry() == tree_before_export
    assert states["ready"]["footer"] == states["working"]["footer"] == states["result"]["footer"]
    assert PdfReader(window.output_path_edit.text()).outline
    assert source.read_bytes() == original
    required = {"source", "pdf-pointer", "source-keyboard", "indent-rules", "numbering-defaults", "three-rules",
                "disabled-rule", "no-rules", "rule-error", "rules-closed", "calibration", "offset-candidate",
                "calibration-error", "calibration-closed", "manual-edit-guard", "source-error",
                "ready", "working", "result"}
    assert set(states) == required
    if folder:
        implementation = Path(main_module.__file__).parent
        identity = hashlib.sha256(b"".join(path.read_bytes() for path in sorted(implementation.glob("*.py")))).hexdigest()
        (folder / "manifest.json").write_text(json.dumps({
            "runtime": str(implementation), "source_sha256": identity,
            "platform": qapp.platformName(), "language": language, "size": size,
            "states": states,
        }, ensure_ascii=False, indent=2))


def _exercise_workflow_roles(qapp, qtbot, tmp_path, size, language):
    source = tmp_path / "Product design - review.pdf"
    writer = QtGui.QPdfWriter(str(source))
    painter = QtGui.QPainter(writer)
    painter.drawText(100, 300, "Document workflow")
    painter.end()
    del writer
    window = main_module.Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    (window.to_english if language == "en" else window.to_chinese)()
    window.resize(*size)
    window.show()
    qtbot.wait(40)
    root = os.environ.get("PDFDIR_UI_CAPTURE_DIR")
    points = qapp.font().pointSizeF()
    folder = Path(root) / f"workflow-{language}-{size[0]}-{points:g}" if root else None
    if folder:
        folder.mkdir(parents=True, exist_ok=True)

    def capture(name):
        qtbot.wait(40)
        for control in (window.open_button, window.document_identity, window.export_button):
            assert window.rect().contains(QtCore.QRect(control.mapTo(window, QtCore.QPoint()), control.size()))
        if folder:
            assert window.grab().save(str(folder / f"{name}.png"))

    capture("no-document")
    assert window.open_button.isEnabled()
    assert window.open_button.property("variant") == "primary"
    assert not window.export_button.isEnabled()
    assert window.document_name_label.fontMetrics().height() <= window.open_button.fontMetrics().height()
    assert window.document_name_label.font().weight() < window.open_button.font().weight()
    assert not window.output_label.isVisible()
    assert not window.output_summary_label.isVisible()
    assert not window.action_status_label.text()
    # Preparing the TOC before choosing a file remains a supported entry path.
    text = "Chapter 1\n  Section 1"
    window.dir_text_edit.setPlainText(text)
    assert window.dir_tree_widget.topLevelItemCount() > 0
    assert window.open_button.property("variant") == "primary"
    capture("toc-before-document")
    window.dir_text_edit.clear()
    window.read_exist_dir_box.setChecked(False)
    assert window._activate_document(str(source))
    capture("document-without-toc")
    assert window.open_button.property("variant") == "secondary"
    assert window.source_import_button.property("suggested")
    assert window.source_import_button.isEnabled()
    assert not window.export_button.isEnabled()
    assert window.document_pages_label.isVisible()
    assert window.document_pages_label.font().weight() < window.document_name_label.font().weight()
    assert window.document_identity.rect().contains(window.document_pages_label.geometry())
    gap = window.document_pages_label.x() - window.document_name_label.geometry().right()
    assert 0 < gap < window.document_name_label.fontMetrics().height()
    assert window.output_label.isVisible()
    assert not window.action_status_label.text()
    assert len({button.height() for button in (
        window.source_import_button, window.advanced_button, window.calibrate_button)}) == 1
    window.dir_text_edit.setPlainText(text)
    capture("bookmarks-ready")
    assert window.export_button.isEnabled()
    assert window.export_button.property("variant") == "primary"
    assert not window.source_import_button.property("suggested")
    signature = window._current_draft_signature()
    for _ in range(3):
        window._reflow_controls()
    assert window._current_draft_signature() == signature
    window.pdf_path_edit.clear()
    capture("document-cleared")
    assert window.open_button.property("variant") == "primary"
    assert not window.document_pages_label.isVisible()
    assert not window.output_label.isVisible()
    assert window.dir_text == text
    if folder:
        implementation = Path(main_module.__file__).parent
        (folder / "manifest.json").write_text(json.dumps({
            "runtime": str(implementation), "platform": qapp.platformName(),
            "source_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in sorted(implementation.glob("*.py")))).hexdigest(),
            "language": language, "size": window.size().toTuple(), "font_points": points,
            "states": ["no-document", "toc-before-document", "document-without-toc", "bookmarks-ready", "document-cleared"],
        }, ensure_ascii=False, indent=2))


@pytest.mark.e2e
@pytest.mark.parametrize("size", [(780, 560), (1100, 760), (1440, 900)])
@pytest.mark.parametrize("language", ["zh", "en"])
def test_workflow_primary_action_follows_stage(qapp, qtbot, tmp_path, size, language):
    _exercise_workflow_roles(qapp, qtbot, tmp_path, size, language)


@pytest.mark.e2e
@pytest.mark.parametrize("language", ["zh", "en"])
def test_workflow_roles_remain_clear_with_large_text(qapp, qtbot, tmp_path, language):
    original = qapp.font()
    font = QtGui.QFont(original)
    font.setPointSize(24)
    try:
        qapp.setFont(font)
        _exercise_workflow_roles(qapp, qtbot, tmp_path, (1100, 800), language)
    finally:
        qapp.setFont(original)
