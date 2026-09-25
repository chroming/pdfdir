"""An export writes bookmarks and reader page labels to the same PDF."""

import os
import stat
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.constants import PageLabelStyle

from src.pdf import pdf as pdf_module
from src.pdf.bookmark import add_bookmark, check_bookmarks
from src.pdf.page_labels import PageLabelPlan


def make_source(tmp_path, labeled=False):
    path = Path(tmp_path) / "book.pdf"
    writer = PdfWriter()
    for _ in range(6):
        writer.add_blank_page(width=72, height=72)
    if labeled:
        writer.set_page_label(0, 2, style=PageLabelStyle.LOWERCASE_ROMAN, start=1)
        writer.set_page_label(3, 5, style=PageLabelStyle.DECIMAL, prefix="Body-", start=1)
    with path.open("wb") as output:
        writer.write(output)
    return path


def test_export_writes_bookmark_and_roman_body_labels(tmp_path):
    source = make_source(tmp_path)
    output = add_bookmark(
        str(source),
        {0: {"title": "Chapter One", "real_num": 4}},
        page_label_plan=PageLabelPlan("roman-body", 4),
    )
    reader = PdfReader(output)
    assert reader.page_labels == ["i", "ii", "iii", "1", "2", "3"]
    assert reader.get_destination_page_number(reader.outline[0]) == 3


def test_export_preserves_existing_custom_labels_by_default(tmp_path):
    source = make_source(tmp_path, labeled=True)
    output = add_bookmark(str(source), {0: {"title": "Chapter One", "real_num": 4}})
    reader = PdfReader(output)
    assert reader.page_labels == ["i", "ii", "iii", "Body-1", "Body-2", "Body-3"]
    assert reader.get_destination_page_number(reader.outline[0]) == 3


@pytest.mark.parametrize("body_start", [0, 7, -1])
def test_invalid_start_does_not_replace_previous_export(tmp_path, body_start):
    source = make_source(tmp_path)
    output_path = Path(str(source).replace(".pdf", "_new.pdf"))
    output_path.write_bytes(b"existing output")
    with pytest.raises(ValueError, match="Body start page"):
        add_bookmark(
            str(source),
            {0: {"title": "Chapter One", "real_num": 4}},
            page_label_plan=PageLabelPlan("roman-body", body_start),
        )
    assert output_path.read_bytes() == b"existing output"


def test_bookmark_page_validation_rejects_zero(tmp_path):
    source = make_source(tmp_path)
    with pytest.raises(ValueError, match="Bookmark page"):
        add_bookmark(str(source), {0: {"title": "Bad", "real_num": 0}})


def test_bookmark_page_validation_rejects_bool(tmp_path):
    source = make_source(tmp_path)
    with pytest.raises(ValueError, match="Bookmark page"):
        add_bookmark(str(source), {0: {"title": "Bad", "real_num": True}})


def test_bookmark_validation_can_reuse_known_page_count(tmp_path):
    check_bookmarks(
        str(tmp_path / "not-opened.pdf"),
        {0: {"title": "Chapter", "real_num": 4}},
        page_count=6,
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_export_retains_file_permissions(tmp_path):
    source = make_source(tmp_path)
    source.chmod(0o666)
    previous_umask = os.umask(0o027)
    try:
        output = Path(add_bookmark(str(source), {}))
    finally:
        os.umask(previous_umask)
    assert stat.S_IMODE(output.stat().st_mode) == 0o640

    output.chmod(0o600)
    add_bookmark(str(source), {})
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_export_closes_validation_handle_before_replace(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    original_reader = pdf_module.PdfReader
    original_replace = os.replace
    validation_streams = []

    def tracked_reader(stream, *args, **kwargs):
        if hasattr(stream, "name") and Path(stream.name).name.startswith(".pdfdir-"):
            validation_streams.append(stream)
        return original_reader(stream, *args, **kwargs)

    def checked_replace(src, dst):
        assert validation_streams and validation_streams[-1].closed
        return original_replace(src, dst)

    monkeypatch.setattr(pdf_module, "PdfReader", tracked_reader)
    monkeypatch.setattr(pdf_module.os, "replace", checked_replace)
    output = add_bookmark(str(source), {})
    assert PdfReader(output).pages


def test_failed_write_keeps_previous_export_and_removes_temp_file(tmp_path, monkeypatch):
    source = make_source(tmp_path)
    previous = tmp_path / "book_new.pdf"
    previous.write_bytes(b"previous export")

    def fail_write(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(PdfWriter, "write", fail_write)
    with pytest.raises(OSError, match="disk full"):
        add_bookmark(
            str(source),
            {0: {"title": "Chapter One", "real_num": 4}},
            page_label_plan=PageLabelPlan("roman-body", 4),
        )
    assert previous.read_bytes() == b"previous export"
    assert list(tmp_path.glob(".pdfdir-*")) == []
