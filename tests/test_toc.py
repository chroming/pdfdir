# -*- coding:utf-8 -*-

import src.pdf.toc as toc_module

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


def test_extract_toc_text_limits_text_layer_pages(monkeypatch):
    call = {}

    def fake_extract_pdf_texts(pdf_path, max_pages=None, cancel_callback=None):
        call.update(pdf_path=pdf_path, max_pages=max_pages)
        return []

    monkeypatch.setattr(toc_module, "extract_pdf_texts", fake_extract_pdf_texts)

    assert toc_module.extract_toc_text("book.pdf", max_pages=7, use_ocr=False) == ""
    assert call == {"pdf_path": "book.pdf", "max_pages": 7}


def test_tesseract_page_ocr_uses_timeout(monkeypatch):
    calls = []

    class FakePixmap(object):
        def tobytes(self, image_format):
            return b""

    class FakePage(object):
        def get_pixmap(self, matrix, alpha):
            return FakePixmap()

    class FakeDocument(object):
        def __len__(self):
            return 1

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
            return ""

    class FakeImage(object):
        open = staticmethod(lambda data: object())

    monkeypatch.setattr(
        toc_module,
        "_load_ocr_dependencies",
        lambda: (FakeFitz, FakeTesseract(), FakeImage),
    )

    toc_module.extract_toc_text_by_tesseract("book.pdf", max_pages=1, timeout=7)

    assert calls[0]["timeout"] == 7
