"""Exercise PDF switching in a separate Qt process (avoids pytest/Qt teardown)."""

import os
import subprocess
import sys
from pathlib import Path

from pypdf import PdfWriter


def test_manual_pdf_switch_guards_draft_and_export_feedback(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    for path in (first, second):
        writer = PdfWriter()
        for _ in range(8):
            writer.add_blank_page(width=72, height=72)
        with path.open("wb") as output:
            writer.write(output)

    script = """
import sys
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from pypdf import PdfReader
from src.gui.main import Main

app = QtWidgets.QApplication([])
window = Main(app, QtCore.QTranslator())
first, second = sys.argv[1:]
window.pdf_path_edit.setText(first)
window.pdf_path_edit.editingFinished.emit()
window.dir_text_edit.setPlainText('First Chapter 1')
window.offset_edit.setText('3')
window.page_label_mode.setCurrentIndex(1)

def choose(label):
    def exec_dialog(box):
        for button in box.buttons():
            if button.text() == label:
                button.click()
                return 0
        raise AssertionError('Missing dialog button: ' + label)
    QtWidgets.QMessageBox.exec_ = exec_dialog

choose('取消')
window.pdf_path_edit.setText(second)
window.pdf_path_edit.editingFinished.emit()
assert window.pdf_path == first
assert window.dir_text == 'First Chapter 1'
assert window.page_label_plan.body_start_page == 4

choose('放弃修改')
window.pdf_path_edit.setText(second)
window.pdf_path_edit.editingFinished.emit()
assert window.pdf_path == second
assert window.dir_text == ''
assert window.page_label_plan.mode == 'preserve'

window.dir_text_edit.setPlainText('Second Chapter 1')
window.offset_edit.setText('2')
window.page_label_mode.setCurrentIndex(1)
window.alert_msg = lambda *args, **kwargs: None
assert window.write_tree_to_pdf() is True
assert window.statusbar.currentMessage().startswith('已导出：')
output = PdfReader(str(Path(second).with_name('second_new.pdf')))
assert output.page_labels[:4] == ['i', 'ii', '1', '2']
assert output.outline[0].title == 'Second Chapter'
assert output.get_destination_page_number(output.outline[0]) == 2

window.offset_edit.setText('100')
assert window.write_tree_to_pdf() is False
assert window.statusbar.currentMessage().startswith('导出失败：')
window.offset_edit.setText('2')
window.dir_text_edit.setPlainText('Second Updated 1')

def export_and_replace(box):
    for button in box.buttons():
        if button.text() in ('导出当前 PDF', '替换'):
            button.click()
            return 0
    raise AssertionError('Missing export or replace button')

QtWidgets.QMessageBox.exec_ = export_and_replace
window.pdf_path_edit.setText(first)
window.pdf_path_edit.editingFinished.emit()
assert window.pdf_path == first
assert window.dir_text == ''
assert PdfReader(str(Path(second).with_name('second_new.pdf'))).outline[0].title == 'Second Updated'
window.close()
"""
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, "-c", script, str(first), str(second)],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
