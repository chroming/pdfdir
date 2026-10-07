"""Safety regressions from the bookmark-workflow review."""

import builtins

import pytest
from pypdf import PdfWriter

from src.convert import convert_dir_text
from src.pdf import pdf as pdf_module
from src.pdf.bookmark import add_bookmark, check_bookmarks, read_document_info
from src.pdf.cancellation import OperationCancelled


@pytest.fixture
def tracked_source(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(source)
    streams = []
    real_open = builtins.open

    def tracked_open(path, *args, **kwargs):
        stream = real_open(path, *args, **kwargs)
        if str(path) == str(source):
            streams.append(stream)
        return stream

    monkeypatch.setattr(pdf_module, "open", tracked_open, raising=False)
    yield source, streams
    for stream in streams:
        stream.close()


@pytest.mark.parametrize("operation", ["metadata", "check", "export", "invalid_page", "cancel", "output_exists"])
def test_source_is_closed_before_operation_returns(tracked_source, operation):
    source, streams = tracked_source
    bookmarks = {0: {"title": "Chapter", "real_num": 1}}
    if operation == "metadata":
        read_document_info(str(source))
    elif operation == "check":
        check_bookmarks(str(source), bookmarks)
    elif operation == "export":
        add_bookmark(str(source), bookmarks)
    elif operation == "invalid_page":
        with pytest.raises(ValueError):
            check_bookmarks(str(source), {0: {"title": "Outside", "real_num": 2}})
    elif operation == "cancel":
        with pytest.raises(OperationCancelled):
            add_bookmark(str(source), bookmarks, cancel_check=lambda: True)
    else:
        source.with_name("source_new.pdf").write_bytes(b"existing result")
        with pytest.raises(OSError):
            add_bookmark(str(source), bookmarks)
    assert streams
    assert all(stream.closed for stream in streams)


@pytest.mark.parametrize("failure", ["reader", "pages"])
def test_constructor_failure_closes_source(tracked_source, monkeypatch, failure):
    source, streams = tracked_source

    def fail(*args, **kwargs):
        raise ValueError("parse failed")

    if failure == "reader":
        monkeypatch.setattr(pdf_module, "PdfReader", fail)
    else:
        monkeypatch.setattr(pdf_module.Pdf, "_get_pages_num", fail)
    with pytest.raises(ValueError, match="parse failed"):
        read_document_info(str(source))
    assert streams and all(stream.closed for stream in streams)


@pytest.mark.parametrize("text", ["Preface ... iii", "Preface IV", "Preface (ix)", "前言　ⅳ"])
def test_roman_page_labels_cannot_silently_inherit_a_destination(text):
    with pytest.raises(ValueError, match="Roman"):
        convert_dir_text("Chapter 5\n" + text, offset=8)


def test_explicit_groups_and_numeric_pages_remain_supported():
    result = convert_dir_text("Part IV  —\n  Preface iii 3\nBody 4", level_by_space=True)
    assert result[0]["is_group"]
    assert result[1]["title"] == "Preface iii"
    assert result[1]["real_num"] == 3
