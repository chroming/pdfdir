# -*- coding:utf-8 -*-

from src.pdf.page_offset import (
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
