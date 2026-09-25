# -*- coding:utf-8 -*-

import pytest

import src.pdf.toc as toc_module

from src.pdf.cancellation import OperationCancelled
from src.pdf.page_offset import OcrUnavailableError
from src.pdf.toc import extract_toc_text_from_page_texts


def test_extract_toc_text_from_page_texts():
    page_texts = [
        "Cover",
        (
            "目录\n第1章 古典密码学 ........ 1\n第2章 分组密码 …… 42\n"
            "附录A 参考资料 420\n1.1\nISBN 978-7-121-27971-3\n"
            "ex (x) =(x+ K)mod 26"
        ),
        (
            "第3章 Hash函数 ........ 92\n第4章 公钥密码 ........ 126\n"
            "第5章 签名方案 ........ 222"
        ),
        "第1章 古典密码学\n正文",
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "第1章 古典密码学 1\n第2章 分组密码 42\n附录A 参考资料 420\n"
        "第3章 Hash函数 92\n第4章 公钥密码 126\n第5章 签名方案 222"
    )


def test_extract_toc_text_ignores_non_contiguous_body_matches():
    page_texts = [
        "目录\n第1章 A 1\n第2章 B 2\n第3章 C 3\n第4章 D 4\n第5章 E 5",
        "第6章 F 6\n第7章 G 7",
        "正文\n第1章 A 1\n公式 2",
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "第1章 A 1\n第2章 B 2\n第3章 C 3\n第4章 D 4\n第5章 E 5\n"
        "第6章 F 6\n第7章 G 7"
    )


def test_extract_toc_text_accepts_small_explicit_contents_page():
    page_texts = ["目录\n第一章 开始 1\n第二章 结束 2"]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "第一章 开始 1\n第二章 结束 2"
    )


def test_paddleocr_accepts_small_explicit_contents_page(monkeypatch):
    monkeypatch.setattr(
        toc_module,
        "_load_paddleocr_dependencies",
        lambda languages: (object(), object()),
    )
    monkeypatch.setattr(
        toc_module,
        "_render_pdf_pages",
        lambda pdf_path, max_pages, dpi: iter([(0, 1, object())]),
    )
    monkeypatch.setattr(
        toc_module,
        "_paddleocr_image_to_text",
        lambda ocr, np, image: "目录\n第一章 开始 1\n第二章 结束 2",
    )

    assert toc_module.extract_toc_text_by_paddleocr("book.pdf") == (
        "第一章 开始 1\n第二章 结束 2"
    )


def test_extract_toc_text_limits_text_layer_pages(monkeypatch):
    call = {}

    def fake_extract_pdf_texts(pdf_path, max_pages=None, cancel_callback=None):
        call.update(pdf_path=pdf_path, max_pages=max_pages)
        return []

    monkeypatch.setattr(toc_module, "extract_pdf_texts", fake_extract_pdf_texts)

    assert toc_module.extract_toc_text("book.pdf", max_pages=7, use_ocr=False) == ""
    assert call == {"pdf_path": "book.pdf", "max_pages": 7}


def test_tesseract_page_ocr_uses_timeout_and_skips_failed_page(monkeypatch):
    calls = []

    class FakePixmap(object):
        def tobytes(self, image_format):
            return b""

    class FakePage(object):
        def get_pixmap(self, matrix, alpha):
            return FakePixmap()

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

    class FakeTesseract(object):
        def image_to_string(self, image, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("timeout")
            return "目录\n第一章 开始 1\n第二章 结束 2"

    class FakeImage(object):
        open = staticmethod(lambda data: object())

    monkeypatch.setattr(
        toc_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, FakeTesseract(), FakeImage),
    )

    toc_text = toc_module.extract_toc_text_by_tesseract(
        "book.pdf", max_pages=2, timeout=7
    )

    assert len(calls) == 2
    assert all(call["timeout"] == 7 for call in calls)
    assert toc_text == "第一章 开始 1\n第二章 结束 2"


def test_tesseract_page_ocr_skips_a_page_when_rendering_fails(monkeypatch):
    calls = []

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
            return 2

        def load_page(self, page_index):
            return FakePage(page_index)

        def close(self):
            pass

    class FakeFitz(object):
        Matrix = staticmethod(lambda x, y: object())
        open = staticmethod(lambda pdf_path: FakeDocument())

    class FakeTesseract(object):
        def image_to_string(self, image, **kwargs):
            calls.append(kwargs)
            return "目录\n第一章 开始 1\n第二章 结束 2"

    class FakeImage(object):
        open = staticmethod(lambda data: object())

    monkeypatch.setattr(
        toc_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, FakeTesseract(), FakeImage),
    )

    toc_text = toc_module.extract_toc_text_by_tesseract(
        "book.pdf", max_pages=2, timeout=7
    )

    assert len(calls) == 1
    assert calls[0]["timeout"] == 7
    assert toc_text == "第一章 开始 1\n第二章 结束 2"


def test_tesseract_page_ocr_reports_when_all_pages_fail_to_render(monkeypatch):
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
        toc_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, object(), object()),
    )

    with pytest.raises(OcrUnavailableError, match="render failed"):
        toc_module.extract_toc_text_by_tesseract("book.pdf", max_pages=2)


def test_tesseract_page_ocr_does_not_downgrade_cancellation(monkeypatch):
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
        toc_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, object(), object()),
    )

    with pytest.raises(OperationCancelled, match="cancelled while rendering"):
        toc_module.extract_toc_text_by_tesseract("book.pdf", max_pages=1)


def test_paddleocr_closes_render_generator_after_early_stop(monkeypatch):
    closed = []
    consumed = []
    texts = iter(
        [
            "目录\n第一章 开始 1\n第二章 继续 2\n第三章 结束 3",
            "",
            "",
            "should not be consumed",
        ]
    )

    def rendered_pages(_pdf_path, _max_pages, _dpi):
        try:
            for page_index in range(4):
                consumed.append(page_index)
                yield page_index, 4, object()
        finally:
            closed.append(True)

    monkeypatch.setattr(
        toc_module,
        "_load_paddleocr_dependencies",
        lambda _languages: (object(), object()),
    )
    monkeypatch.setattr(toc_module, "_render_pdf_pages", rendered_pages)
    monkeypatch.setattr(
        toc_module,
        "_paddleocr_image_to_text",
        lambda _ocr, _np, _image: next(texts),
    )

    toc_module.extract_toc_text_by_paddleocr("book.pdf", max_pages=4)

    assert consumed == [0, 1, 2]
    assert closed == [True]


def test_extract_toc_text_by_ocr_passes_languages_to_tesseract(monkeypatch):
    calls = []

    def fake_tesseract(pdf_path, **kwargs):
        calls.append(kwargs["languages"])
        return "toc"

    monkeypatch.setattr(
        toc_module, "extract_toc_text_by_tesseract", fake_tesseract
    )

    assert (
        toc_module.extract_toc_text_by_ocr(
            "book.pdf", backend="tesseract", languages="en"
        )
        == "toc"
    )
    assert (
        toc_module.extract_toc_text_by_ocr(
            "book.pdf", backend="tesseract", languages="deu+eng"
        )
        == "toc"
    )
    assert calls == ["eng", "deu+eng"]


def test_extract_toc_text_by_ocr_passes_languages_to_tesseract_fallback(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        toc_module,
        "extract_toc_text_by_paddleocr",
        lambda *args, **kwargs: "",
    )

    def fake_tesseract(pdf_path, **kwargs):
        calls.append(kwargs["languages"])
        return "toc"

    monkeypatch.setattr(
        toc_module, "extract_toc_text_by_tesseract", fake_tesseract
    )

    assert toc_module.extract_toc_text_by_ocr("book.pdf", languages="ch") == "toc"
    assert calls == ["chi_sim+eng"]
