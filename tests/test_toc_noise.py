# -*- coding: utf-8 -*-

from src.pdf.toc import _collect_paddleocr_texts, extract_toc_text_from_page_texts


def test_extract_toc_text_removes_generic_ocr_latin_noise():
    page_texts = [
        (
            "目录\n"
            "3.3 线性密码分析TISCUNRTeACnbwelawemwenonances 61\n"
            "3.3.3 SPN 的线性密码分析 66\n"
            "4.2 Hash 函数的安全性 93\n"
            "5.4.3 Miller-Rabin 算法 146\n"
            "习题 S 54\n"
            "12:2 FRAG BETES 22\n"
            "6.5.5 TESA IBA HAG RAR 208\n"
            "4.6 注释与参考文献cuNUaAUeaie 119\n"
            "INTRODUCTION 1\n"
            "DATA SECURITY 12\n"
        )
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "3.3 线性密码分析 61\n"
        "3.3.3 SPN 的线性密码分析 66\n"
        "4.2 Hash 函数的安全性 93\n"
        "5.4.3 Miller-Rabin 算法 146\n"
        "习题 54\n"
        "4.6 注释与参考文献 119\n"
        "DATA SECURITY 12"
    )


def test_collect_paddleocr_texts_supports_common_result_shapes():
    legacy_result = [
        [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("第1章 古典密码学 1", 0.99)],
            [[[0, 2], [1, 2], [1, 3], [0, 3]], ("1.1 引言 2", 0.98)],
        ]
    ]
    dict_result = [{"rec_texts": ["第2章 分组密码 36", "2.1 引言 36"]}]

    assert _collect_paddleocr_texts(legacy_result) == [
        "第1章 古典密码学 1",
        "1.1 引言 2",
    ]
    assert _collect_paddleocr_texts(dict_result) == [
        "第2章 分组密码 36",
        "2.1 引言 36",
    ]


def test_extract_toc_text_merges_paddleocr_wrapped_lines():
    page_texts = [
        (
            "目录\n"
            "作者简介\n"
            "第1章\n"
            "古典密码学\n"
            "1.1.1\n"
            "移位密码\n"
            "1.1.2\n"
            "代换密码\n"
            ".5\n"
            "1.1.3\n"
            "仿射密码·\n"
            "…6\n"
            "3.3.3 SPN的线性密码分析\n"
            "66\n"
            "习题\n"
            "…54\n"
        )
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "第1章 古典密码学\n"
        "1.1.1 移位密码\n"
        "1.1.2 代换密码 5\n"
        "1.1.3 仿射密码 6\n"
        "3.3.3 SPN的线性密码分析 66\n"
        "习题 54"
    )


def test_extract_toc_text_does_not_extend_block_with_title_only_body_page():
    page_texts = [
        (
            "目录\n"
            "第1章\n"
            "古典密码学\n"
            "1.1 引言\n"
            "1\n"
            "1.2 密码分析\n"
            "19\n"
            "1.3 注释与参考文献\n"
            "29\n"
        ),
        (
            "正文\n"
            "第1章\n"
            "古典密码学\n"
            "1.1 引言\n"
            "密码体制定义\n"
            "1.2 密码分析\n"
        ),
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "第1章 古典密码学\n"
        "1.1 引言 1\n"
        "1.2 密码分析 19\n"
        "1.3 注释与参考文献 29"
    )


def test_extract_toc_text_drops_obviously_decreasing_page_numbers():
    page_texts = [
        (
            "目录\n"
            "3.2 代换-置换网络 58\n"
            "3.3 线性密码分析 61\n"
            "3.3.3 SPN的线性密码分析 66\n"
            "3.4 差分密码分析 7\n"
            "3.5 数据加密标准 74\n"
            "习题 4\n"
        )
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "3.2 代换-置换网络 58\n"
        "3.3 线性密码分析 61\n"
        "3.3.3 SPN的线性密码分析 66\n"
        "3.4 差分密码分析\n"
        "3.5 数据加密标准 74\n"
        "习题"
    )


def test_extract_toc_text_drops_absurd_forward_page_jump():
    page_texts = [
        (
            "目录\n"
            "12.3 信任模型 356\n"
            "12.4 PKI 的未来 361\n"
            "14.2.1 利用 Ramp 方案的一种改进 6406\n"
        )
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "12.3 信任模型 356\n"
        "12.4 PKI 的未来 361\n"
        "14.2.1 利用 Ramp 方案的一种改进"
    )


def test_extract_toc_text_drops_single_digit_page_after_large_page():
    page_texts = [
        (
            "目录\n"
            "3.3 线性密码分析 61\n"
            "3.3.3 SPN的线性密码分析 66\n"
            "3.4 差分密码分析 7\n"
        )
    ]

    assert extract_toc_text_from_page_texts(page_texts) == (
        "3.3 线性密码分析 61\n"
        "3.3.3 SPN的线性密码分析 66\n"
        "3.4 差分密码分析"
    )
