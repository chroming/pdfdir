# -*- coding:utf-8 -*-

import pytest

import src.pdf.page_offset as page_offset_module

from src.pdf.cancellation import OperationCancelled
from src.pdf.page_offset import (
    OcrCancelledError,
    OcrUnavailableError,
    _render_matrix,
    _tesseract_config,
    extract_pdf_texts,
    extract_pdf_texts_by_ocr,
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


def test_extract_pdf_texts_by_ocr_remains_importable_and_bounded(monkeypatch):
    calls = []
    progress = []

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
            calls.append(kwargs)
            return "Page {}".format(len(calls))

    class FakeImage(object):
        open = staticmethod(lambda data: object())

    monkeypatch.setattr(
        page_offset_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, FakeTesseract(), FakeImage),
    )

    texts = extract_pdf_texts_by_ocr(
        "book.pdf",
        max_pages=2,
        timeout=7,
        progress_callback=lambda current, total: progress.append((current, total)),
    )

    assert texts == ["Page 1", "Page 2"]
    assert [call["timeout"] for call in calls] == [7, 7]
    assert progress == [(1, 2), (2, 2)]


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


def test_page_offset_ocr_closes_document_after_early_match(monkeypatch):
    closed = []

    class FakePixmap(object):
        def tobytes(self, image_format):
            return b""

    class FakePage(object):
        def get_pixmap(self, matrix, alpha):
            return FakePixmap()

    class FakeDocument(object):
        def __len__(self):
            return 4

        def load_page(self, page_index):
            return FakePage()

        def close(self):
            closed.append(True)

    class FakeFitz(object):
        Matrix = staticmethod(lambda x, y: object())
        open = staticmethod(lambda pdf_path: FakeDocument())

    class FakeTesseract(object):
        texts = iter(["Chapter One", "Chapter Two", "", ""])

        def image_to_string(self, image, **kwargs):
            return next(self.texts)

    class FakeImage(object):
        open = staticmethod(lambda data: object())

    monkeypatch.setattr(
        page_offset_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, FakeTesseract(), FakeImage),
    )

    assert infer_page_offset_by_ocr(
        "book.pdf",
        "Chapter One 1\nChapter Two 2",
        max_pages=4,
    ) == 0
    assert closed == [True]


def test_page_offset_ocr_skips_a_page_when_rendering_fails(monkeypatch):
    class FakePixmap(object):
        def tobytes(self, image_format):
            return b""

    class FakePage(object):
        def __init__(self, page_index):
            self.page_index = page_index

        def get_pixmap(self, matrix, alpha):
            if self.page_index == 0:
                raise RuntimeError("render failed")
            return FakePixmap()

    class FakeDocument(object):
        def __len__(self):
            return 3

        def load_page(self, page_index):
            return FakePage(page_index)

        def close(self):
            pass

    class FakeFitz(object):
        Matrix = staticmethod(lambda x, y: object())
        open = staticmethod(lambda pdf_path: FakeDocument())

    class FakeTesseract(object):
        texts = iter(["Chapter One", "Chapter Two"])

        def image_to_string(self, image, **kwargs):
            return next(self.texts)

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


def test_extract_pdf_texts_by_ocr_reports_when_all_pages_fail_to_render(
    monkeypatch,
):
    class FakePage(object):
        def get_pixmap(self, matrix, alpha):
            raise RuntimeError("render failed")

    class FakeDocument(object):
        def __len__(self):
            return 2

        def load_page(self, page_index):
            return FakePage()

        def close(self):
            pass

    class FakeFitz(object):
        Matrix = staticmethod(lambda x, y: object())
        open = staticmethod(lambda pdf_path: FakeDocument())

    monkeypatch.setattr(
        page_offset_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, object(), object()),
    )

    with pytest.raises(OcrUnavailableError, match="render failed"):
        extract_pdf_texts_by_ocr("book.pdf", max_pages=2)


def test_page_offset_ocr_does_not_downgrade_cancellation(monkeypatch):
    class FakeDocument(object):
        def __len__(self):
            return 1

        def load_page(self, page_index):
            raise OperationCancelled("cancelled while rendering")

        def close(self):
            pass

    class FakeFitz(object):
        open = staticmethod(lambda pdf_path: FakeDocument())

    monkeypatch.setattr(
        page_offset_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, object(), object()),
    )

    with pytest.raises(OperationCancelled, match="cancelled while rendering"):
        extract_pdf_texts_by_ocr("book.pdf", max_pages=1)


def test_page_offset_ocr_checks_cancellation_before_candidate_validation():
    with pytest.raises(OcrCancelledError):
        infer_page_offset_by_ocr(
            "book.pdf",
            "",
            cancel_check=lambda: True,
        )


def test_extract_pdf_texts_respects_page_limit(monkeypatch, tmp_path):
    progress = []

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

    assert extract_pdf_texts(
        str(pdf_path),
        2,
        lambda current, total: progress.append((current, total)),
    ) == ["0", "1"]
    assert progress == [(1, 2), (2, 2)]


def test_extract_pdf_texts_can_be_cancelled(monkeypatch, tmp_path):
    class FakeReader(object):
        def __init__(self, handle, strict=False):
            self.pages = [object()]

    monkeypatch.setattr(page_offset_module, "PdfReader", FakeReader)
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"pdf")

    with pytest.raises(OcrCancelledError):
        extract_pdf_texts(str(pdf_path), cancel_callback=lambda: True)


def test_extract_pdf_texts_supports_master_positional_cancel_callback(
    monkeypatch, tmp_path
):
    class FakeReader(object):
        def __init__(self, handle, strict=False):
            self.pages = [object()]

    monkeypatch.setattr(page_offset_module, "PdfReader", FakeReader)
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"pdf")

    with pytest.raises(OcrCancelledError):
        extract_pdf_texts(str(pdf_path), None, lambda: True)


def test_extract_pdf_texts_supports_product_cancel_check(
    monkeypatch, tmp_path
):
    extracted = []

    class FakePage(object):
        def __init__(self, index):
            self.index = index

        def extract_text(self):
            extracted.append(self.index)
            return str(self.index)

    class FakeReader(object):
        def __init__(self, handle, strict=False):
            self.pages = [FakePage(index) for index in range(5)]

    monkeypatch.setattr(page_offset_module, "PdfReader", FakeReader)
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"pdf")

    with pytest.raises(OcrCancelledError):
        extract_pdf_texts(
            str(pdf_path),
            cancel_check=lambda: len(extracted) >= 2,
        )

    assert extracted == [0, 1]
