import os
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pypdf import PdfWriter
from PySide6 import QtCore, QtWidgets

import src.gui.main as main_module
from src.gui.main import BookmarkWorkerThread, Main


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    main_window = Main(qapp, QtCore.QTranslator())
    yield main_window
    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


def test_main_builds_nested_bookmark_tree(window):
    window.dir_text_edit.setPlainText("Chapter 1 1\n  Section 1 2")
    window.space_level_box.setChecked(True)
    window.make_dir_tree()

    assert window.dir_tree_widget.topLevelItemCount() == 1
    assert window.tree_to_dict()[1]["parent"] == 0


def test_translation_loader_finds_packaged_translation(window):
    loaded_paths = []

    class FakeTranslator:
        def load(self, path):
            loaded_paths.append(path)
            return path.endswith("src/language/en.qm")

    window.trans = FakeTranslator()

    assert window._load_translation("en") is True
    assert any(path.endswith("src/language/en.qm") for path in loaded_paths)


def test_importing_gui_module_does_not_replace_excepthook():
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "original = sys.excepthook; "
                "import src.gui.main; "
                "assert sys.excepthook is original"
            ),
        ],
        check=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )


def test_bookmark_worker_reports_success(monkeypatch, qapp):
    calls = []
    monkeypatch.setattr(
        main_module,
        "check_bookmarks",
        lambda path, bookmarks, keep: calls.append(("check", path, bookmarks, keep)),
    )
    monkeypatch.setattr(
        main_module,
        "add_bookmark",
        lambda path, bookmarks, keep: "/tmp/output.pdf",
    )
    results = []
    worker = BookmarkWorkerThread("input.pdf", {0: {"title": "A"}}, True)
    worker.result.connect(lambda *result: results.append(result))

    worker.run()

    assert calls == [("check", "input.pdf", {0: {"title": "A"}}, True)]
    assert results == [(True, "/tmp/output.pdf Finished!")]


def test_bookmark_worker_reports_validation_error(monkeypatch, qapp):
    def fail_check(*_args):
        raise ValueError("Page number is out of range")

    monkeypatch.setattr(main_module, "check_bookmarks", fail_check)
    results = []
    worker = BookmarkWorkerThread("input.pdf", {}, False)
    worker.result.connect(lambda *result: results.append(result))

    worker.run()

    assert results == [(False, "Page number is out of range")]


def test_main_writes_pdf_in_background(window, qapp, tmp_path):
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as handle:
        writer.write(handle)

    messages = []
    window.alert_msg = lambda message, level="info", **_kwargs: messages.append(
        (level, message)
    )
    window.pdf_path_edit.setText(str(source))
    window.dir_text_edit.setPlainText("Chapter One 1")
    window.make_dir_tree()

    window.write_tree_to_pdf()
    worker = window._worker
    assert worker is not None
    assert worker.wait(15_000)
    qapp.processEvents()

    assert (tmp_path / "source_new.pdf").exists()
    assert messages[-1][0] == "info"
    assert window.export_button.isEnabled()
    assert window._worker is None
