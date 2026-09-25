"""An export writes bookmarks and reader page labels to the same PDF."""

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.constants import PageLabelStyle

from src.pdf.bookmark import add_bookmark
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
