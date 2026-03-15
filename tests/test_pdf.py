# -*- coding:utf-8 -*-

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from src.pdf.bookmark import add_bookmark
from src.pdf.pdf import Pdf


class _FakeIndirectReference:
    def __init__(self, idnum):
        self.idnum = idnum


class _FakePage:
    def __init__(self, idnum, page_number):
        self.indirect_reference = _FakeIndirectReference(idnum)
        self.page_number = page_number


def test_get_pages_num_supports_indirect_reference(monkeypatch):
    monkeypatch.setattr("src.pdf.pdf.PageObject", _FakePage)

    pages_num = Pdf._get_pages_num([_FakePage(7, 3)])

    assert pages_num == {7: 3}


def test_add_bookmark_preserves_pdf_pages(tmp_path):
    source_path = Path(tmp_path) / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as handle:
        writer.write(handle)

    output_path = add_bookmark(
        str(source_path),
        {0: {"title": "Chapter 1", "real_num": 1}},
    )

    output_reader = PdfReader(output_path)

    assert len(output_reader.pages) == 2
    assert len(output_reader.outline) == 1
