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
from tests.gui_test_utils import track_main_window


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
    for index, pattern in enumerate((r"^第\d+章", r"^\s*\d+\.\d+\s", r"^\s*\d+\.\d+\.\d+\s")):
        window._add_rule_level(index)
        getattr(window, f"level{index}_edit").setText(pattern)
    qtbot.waitUntil(lambda: not window._rules_pending)
    capture("three-rules")
    window.rules_options_button.click()
    capture("rules-options")
    window.rules_options_button.click()
    window.level0_edit.setText("[")
    capture("rule-error")
    window.level0_edit.setText(r"^第\d+章")
    qtbot.waitUntil(lambda: not window._rules_pending)
    window.advanced_button.click()
    capture("rules-closed")
    window.calibrate_button.click()
    capture("calibration")
    window.calibration_more_button.click()
    capture("direct-offset")
    window.calibration_more_button.click()
    window.pdf_anchor.setText("999")
    capture("calibration-error")
    qtbot.keyClick(window.pdf_anchor, QtCore.Qt.Key_Escape)
    capture("calibration-closed")
    assert window.source_tabs.currentIndex() == 0
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
    window.export_button.click()
    window._reflow_controls()
    capture("working", settle=False)
    qtbot.waitUntil(lambda: window._worker_thread is None, timeout=15000)
    capture("result")
    assert states["ready"]["footer"] == states["working"]["footer"] == states["result"]["footer"]
    assert PdfReader(window.output_path_edit.text()).outline
    assert source.read_bytes() == original
    required = {"source", "pdf-pointer", "source-keyboard", "indent-rules", "three-rules",
                "rules-options", "rule-error", "rules-closed", "calibration", "direct-offset",
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
