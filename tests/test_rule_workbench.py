"""Contracts for iterative rule editing, independent of panel decoration."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore
from pypdf import PdfWriter

from src.gui.base import SOURCE_ROLE, RULE_ROLE
from src.gui.main import Main
from tests.gui_test_utils import track_main_window


@pytest.fixture
def window(qtbot, qapp, tmp_path):
    window = Main(qapp, QtCore.QTranslator())
    track_main_window(qtbot, qapp, window)
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(20):
        writer.add_blank_page(width=72, height=72)
    with source.open("wb") as stream:
        writer.write(stream)
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("1. Chapter 1\n1.1 Section 2\n\n2. Chapter 3\nAppendix 4")
    window.level_mode_box.setCurrentIndex(1)
    window.level0_box.setChecked(True)
    window.level1_box.setChecked(True)
    window.level0_edit.setText(r"^\d+\.")
    window.level1_edit.setText(r"^\d+\.\d+")
    window._clear_rule_trial()
    window.show()
    window.advanced_button.click()
    qtbot.waitUntil(window.rules_scroll.isVisible)
    return window


def test_invalid_rule_retains_last_good_tree_and_blocks_stale_export(window, qtbot):
    before = window._tree_snapshot()
    window.level0_edit.setText("[")
    assert window._tree_snapshot() == before
    assert window._rules_pending
    assert not window.export_button.isEnabled()
    assert window.preview_count_label.text() == "尚未更新"
    window.level0_edit.setText(r"^\d+\.")
    qtbot.waitUntil(lambda: not window._rules_pending)
    assert window.export_button.isEnabled()


def test_rule_panel_remembers_user_size_across_disclosure(window, qtbot):
    window.resize(1040, 720)
    qtbot.wait(30)
    window.rule_splitter.setSizes([400, 175])
    qtbot.wait(30)
    before = window.rule_splitter.sizes()
    window.advanced_button.click()
    window.advanced_button.click()
    qtbot.wait(30)
    assert abs(window.rule_splitter.sizes()[1] - before[1]) <= 2


def test_initial_rule_panel_leaves_most_small_window_for_source(window, qtbot):
    window.advanced_button.click()
    window.resize(780, 560)
    qtbot.wait(30)
    window.advanced_button.click()
    qtbot.wait(30)
    source, rules = window.rule_splitter.sizes()
    assert source >= rules


def test_collapsing_rules_returns_space_to_source(window, qtbot):
    window.advanced_button.click()
    qtbot.wait(30)
    available = window.rule_splitter.height() - window.rule_splitter.handleWidth()
    assert abs(window.dir_text_edit.height() + window.rules_section.height() - available) <= 2


def test_real_typing_debounces_without_blanking_preview(window, qtbot):
    before = window._tree_snapshot()
    window.level1_edit.setEnabled(True)
    window.level1_edit.setFocus()
    window.level1_edit.selectAll()
    qtbot.keyClicks(window.level1_edit, r"^\d+\.\d+")
    assert window._rules_pending
    assert not window.export_button.isEnabled()
    assert window._tree_snapshot() == before
    qtbot.waitUntil(lambda: not window._rules_pending)
    assert window.export_button.isEnabled()


def test_rebuild_keeps_selected_source_and_collapsed_nodes(window, qtbot):
    tree = window.dir_tree_widget
    first = tree.topLevelItem(0)
    first.setExpanded(False)
    selected = tree.topLevelItem(1)
    tree.setCurrentItem(selected)
    source = selected.data(0, SOURCE_ROLE)
    window.level0_edit.setText(r"^\d+\. ?")
    qtbot.waitUntil(lambda: not window._rules_pending)
    assert tree.currentItem().data(0, SOURCE_ROLE) == source
    assert not tree.topLevelItem(0).isExpanded()


def test_match_counts_follow_effective_priority_and_link_to_source(window):
    # The child matches both rules, but the same highest-level precedence as
    # conversion assigns it only to rule 2, not to both counts.
    assert [button.text() for button in window.rule_counts[:2]] == ["2 条匹配", "1 条匹配"]
    assert "1" in window.rules_unmatched_button.text()
    window.rule_counts[1].click()
    item = window.dir_tree_widget.currentItem()
    assert item.data(0, RULE_ROLE) == 1
    assert window.dir_text_edit.textCursor().blockNumber() == 1
    assert not window._preview_manually_adjusted
    window.rules_unmatched_button.click()
    assert window.dir_text_edit.textCursor().blockNumber() == 4


def test_manual_edits_need_explicit_trial_and_restore_exact_draft(window, qtbot):
    tree = window.dir_tree_widget
    tree.topLevelItem(0).setText(0, "Manually corrected")
    before = window._tree_snapshot()
    previous_rule = window.level0_edit.text()
    window.level0_edit.setText(r"^Appendix")
    assert window._rule_guarded
    assert window._tree_snapshot() == before
    assert not window.export_button.isEnabled()
    window.rules_accept_button.click()
    qtbot.waitUntil(lambda: not window._rules_pending)
    assert window._tree_snapshot() != before
    window.offset_edit.setText("2")
    window.rules_restore_button.click()
    assert window._tree_snapshot() == before
    assert window.level0_edit.text() == previous_rule
    assert window.offset_edit.text() == "0"
    assert window._preview_manually_adjusted
    assert not window._rules_pending
    assert window.export_button.isEnabled()


def test_collapse_retains_trial_and_escape_returns_focus(window, qtbot):
    initial = window.level0_edit.text()
    window.level0_edit.setText("^Appendix")
    qtbot.waitUntil(lambda: not window._rules_pending)
    qtbot.keyClick(window.level0_edit, QtCore.Qt.Key_Escape)
    assert not window.rules_scroll.isVisible()
    assert window.advanced_button.hasFocus()
    assert window.level0_edit.text() == "^Appendix"
    window.advanced_button.click()
    window.rules_restore_button.click()
    assert window.level0_edit.text() == initial


def test_undo_keeps_source_link_metadata(window):
    tree = window.dir_tree_widget
    item = tree.topLevelItem(0)
    source = item.data(0, SOURCE_ROLE)
    item.setText(0, "Corrected")
    tree.undo()
    assert tree.topLevelItem(0).data(0, SOURCE_ROLE) == source


def test_manual_edit_during_debounce_is_not_overwritten(window, qtbot):
    window.level0_edit.setEnabled(True)
    window.level0_edit.setFocus()
    window.level0_edit.setText("^Appendix")
    window.dir_tree_widget.topLevelItem(0).setText(0, "Concurrent correction")
    qtbot.waitUntil(lambda: window._rule_guarded)
    assert window.dir_tree_widget.topLevelItem(0).text(0) == "Concurrent correction"
    window.rules_restore_button.click()
    assert window.dir_tree_widget.topLevelItem(0).text(0) == "Concurrent correction"


def test_escape_from_disclosure_closes_inline_tools(window, qtbot):
    window.rules_options_button.setFocus()
    qtbot.keyClick(window.rules_options_button, QtCore.Qt.Key_Escape)
    assert not window.rules_scroll.isVisible()
    assert window.advanced_button.hasFocus()


@pytest.mark.parametrize("english", [False, True])
def test_minimum_window_keeps_preview_and_output_visible(window, qtbot, english):
    if english:
        window.to_english()
    window.resize(window.minimumSize())
    qtbot.wait(20)
    assert window.rules_scroll.viewport().width() >= window.advanced_widget.minimumSizeHint().width()
    for widget in (window.dir_tree_widget, window.export_button, window.rules_restore_button):
        rect = QtCore.QRect(widget.mapTo(window, QtCore.QPoint()), widget.size())
        assert window.rect().contains(rect)
    assert window.dir_text_edit.viewport().height() >= window.dir_text_edit.fontMetrics().height() * 2


def test_restoring_trial_does_not_write_source_pdf(window):
    from pathlib import Path

    path = Path(window.pdf_path)
    before = path.read_bytes()
    window.level0_edit.setText("^Appendix")
    window.rules_restore_button.click()
    assert path.read_bytes() == before
