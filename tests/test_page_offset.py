# -*- coding:utf-8 -*-

import pytest

import src.pdf.page_offset as page_offset_module

from src.pdf.page_offset import (
    OcrCancelledError,
    _render_matrix,
    _tesseract_config,
    extract_pdf_texts,
    infer_page_offset_by_ocr,
    infer_page_offset_from_texts,
    normalize_page_text,
    page_contains_title,
)


def test_normalize_page_text_ignores_whitespace_and_case():
    assert normalize_page_text("Chapter\n One") == "chapterone"


def test_infer_page_offset_uses_consistent_title_matches():
    page_texts = [""] * 50
    page_texts[4] = "Contents\nChapter One 1\nChapter Two 20\nChapter Three 40"
    page_texts[9] = "Chapter One\nBody text"
    page_texts[28] = "Chapter Two\nBody text"
    page_texts[48] = "Chapter Three\nBody text"

    offset = infer_page_offset_from_texts(
        "Chapter One 1\nChapter Two 20\nChapter Three 40",
        page_texts,
    )

    assert offset == 9


def test_infer_page_offset_ignores_contents_page_matches():
    page_texts = [""] * 50
    page_texts[4] = "Contents\nChapter One 1\nChapter Two 20\nChapter Three 40"
    page_texts[9] = "Chapter One\nBody text"
    page_texts[28] = "Chapter Two\nBody text"

    offset = infer_page_offset_from_texts(
        "Chapter One 1\nChapter Two 20\nChapter Three 40",
        page_texts,
    )

    assert offset == 9


def test_infer_page_offset_rejects_single_page_multi_title_match():
    page_texts = ["Book Title\nBook Subtitle"]

    offset = infer_page_offset_from_texts(
        "Book Title 1\nBook Subtitle 1",
        page_texts,
    )

    assert offset is None


def test_infer_page_offset_returns_none_without_candidates():
    assert infer_page_offset_from_texts("", ["Chapter One"]) is None


def test_infer_page_offset_returns_none_for_ambiguous_single_match():
    page_texts = ["Contents Chapter One 1", "Chapter One"]

    assert infer_page_offset_from_texts("Chapter One 1", page_texts) is None


def test_infer_page_offset_requires_multiple_candidates():
    assert infer_page_offset_from_texts("Chapter One 1", ["Chapter One"]) is None


def test_infer_page_offset_skips_title_only_toc_entries():
    page_texts = ["Preface Chapter One Chapter Two"] + [""] * 30
    page_texts[9] = "Section One"
    page_texts[18] = "Section Two"

    offset = infer_page_offset_from_texts(
        "Chapter One\nChapter Two\nSection One 1\nSection Two 10",
        page_texts,
    )

    assert offset == 9


def test_page_contains_title_allows_ocr_noise():
    assert page_contains_title("密码学原理与实践", "党码学原理与实践 第三版")


def test_infer_page_offset_supports_negative_offsets():
    page_texts = [""] * 10
    page_texts[0] = "Chapter Ten"
    page_texts[9] = "Chapter Nineteen"

    offset = infer_page_offset_from_texts(
        "Chapter Ten 10\nChapter Nineteen 19",
        page_texts,
    )

    assert offset == -9


def test_infer_page_offset_rejects_equally_supported_offsets():
    page_texts = [""] * 21
    page_texts[9] = "Chapter One"
    page_texts[10] = "Chapter Two"
    page_texts[19] = "Chapter One"
    page_texts[20] = "Chapter Two"

    offset = infer_page_offset_from_texts(
        "Chapter One 1\nChapter Two 2",
        page_texts,
    )

    assert offset is None


def test_tesseract_config_quotes_tessdata_path(monkeypatch):
    monkeypatch.setattr(page_offset_module.sys, "prefix", "/tmp/Python Env")
    monkeypatch.setattr(page_offset_module.os.path, "isdir", lambda path: True)

    assert _tesseract_config() == '--tessdata-dir "/tmp/Python Env/tessdata"'


def test_render_matrix_limits_oversized_pdf_pages():
    class FakeRect(object):
        width = 10_000
        height = 10_000

    class FakePage(object):
        rect = FakeRect()

    class FakeFitz(object):
        Matrix = staticmethod(lambda x, y: (x, y))

    matrix = _render_matrix(FakeFitz, FakePage(), dpi=240, max_pixels=1_000_000)

    assert matrix[0] == pytest.approx(0.1)
    assert matrix[1] == pytest.approx(0.1)


def test_page_offset_ocr_skips_a_failed_page(monkeypatch):
    texts = iter([RuntimeError("timeout"), "Chapter One", "Chapter Two"])

    class FakePixmap(object):
        def tobytes(self, image_format):
            return b""

    class FakePage(object):
        def get_pixmap(self, matrix, alpha):
            return FakePixmap()

    class FakeDocument(object):
        def __len__(self):
            return 3

        def load_page(self, page_index):
            return FakePage()

        def close(self):
            pass

    class FakeFitz(object):
        Matrix = staticmethod(lambda x, y: object())
        open = staticmethod(lambda pdf_path: FakeDocument())

    class FakeTesseract(object):
        def image_to_string(self, image, **kwargs):
            result = next(texts)
            if isinstance(result, Exception):
                raise result
            return result

    class FakeImage(object):
        open = staticmethod(lambda data: object())

    monkeypatch.setattr(
        page_offset_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, FakeTesseract(), FakeImage),
    )

    offset = infer_page_offset_by_ocr(
        "book.pdf",
        "Chapter One 1\nChapter Two 2",
        max_pages=3,
    )

    assert offset == 1


def test_extract_pdf_texts_respects_page_limit(monkeypatch, tmp_path):
    class FakePage(object):
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class FakeReader(object):
        def __init__(self, handle, strict=False):
            self.pages = [FakePage(str(index)) for index in range(5)]

    monkeypatch.setattr(page_offset_module, "PdfReader", FakeReader)
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"pdf")

    assert extract_pdf_texts(str(pdf_path), max_pages=2) == ["0", "1"]


def test_extract_pdf_texts_can_be_cancelled(monkeypatch, tmp_path):
    class FakeReader(object):
        def __init__(self, handle, strict=False):
            self.pages = [object()]

    monkeypatch.setattr(page_offset_module, "PdfReader", FakeReader)
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"pdf")

    with pytest.raises(OcrCancelledError):
        extract_pdf_texts(str(pdf_path), cancel_callback=lambda: True)
