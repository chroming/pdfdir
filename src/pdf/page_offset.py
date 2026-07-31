# -*- coding: utf-8 -*-

"""Infer the page offset between printed page numbers and PDF pages."""

import logging
import math
import os
import re
import sys
from io import BytesIO

from pypdf import PdfReader

from src.convert import COMPILED_PAGE_NUM_PATTERNS, text_to_list

logger = logging.getLogger(__name__)


class OcrUnavailableError(RuntimeError):
    """Raised when OCR fallback cannot run in the current environment."""


class OcrCancelledError(RuntimeError):
    """Raised when an OCR operation is cancelled."""


def _check_cancelled(cancel_callback):
    if cancel_callback and cancel_callback():
        raise OcrCancelledError("OCR operation cancelled")


def normalize_page_text(text):
    """Normalize text so titles can match despite whitespace differences."""
    if not text:
        return ""
    return re.sub(r"\s+", "", text).lower()


def split_explicit_page_num(text):
    """Return (title, page_num) only when a line explicitly ends with a page number."""
    for pat in COMPILED_PAGE_NUM_PATTERNS[:-1]:
        res = pat.search(text)
        if not res:
            continue
        title, num = res.groups()
        title = title.rstrip(" .-")
        if title and num:
            return title, int(num)
    return None, None


def iter_toc_candidates(dir_text, max_entries=20, min_title_len=2):
    """Yield (title, printed_page_num) candidates parsed from directory text."""
    for line in text_to_list(dir_text):
        title, num = split_explicit_page_num(line.rstrip())
        if title is None:
            continue
        title = title.strip()
        normalized_title = normalize_page_text(title)
        if len(normalized_title) < min_title_len:
            continue
        yield title, num
        max_entries -= 1
        if max_entries <= 0:
            break


def _title_grams(title, gram_size):
    return {
        title[i : i + gram_size]
        for i in range(len(title) - gram_size + 1)
    }


def _has_non_ascii(text):
    return any(ord(char) > 127 for char in text)


def page_contains_title(title, page_text, fuzzy=True):
    """Return True when extracted page text appears to contain the title."""
    normalized_title = normalize_page_text(title)
    normalized_page = normalize_page_text(page_text)
    if not normalized_title or not normalized_page:
        return False
    if normalized_title in normalized_page:
        return True
    if not fuzzy or len(normalized_title) < 4 or not _has_non_ascii(normalized_title):
        return False

    gram_size = 3 if len(normalized_title) >= 8 else 2
    grams = _title_grams(normalized_title, gram_size)
    if not grams:
        return False
    matched = sum(1 for gram in grams if gram in normalized_page)
    return matched / float(len(grams)) >= 0.6


def _looks_like_contents_page(page_text, matched_count):
    normalized_page = normalize_page_text(page_text)
    if matched_count >= 3:
        return True
    return matched_count >= 2 and (
        "contents" in normalized_page or "目录" in normalized_page
    )


def _infer_page_offset_from_candidates(candidates, page_texts, log_insufficient=True):
    offset_matches = {}

    for page_index, page_text in enumerate(page_texts):
        page_matches = []
        for candidate_index, (title, printed_num) in enumerate(candidates):
            if page_contains_title(title, page_text):
                page_matches.append((candidate_index, printed_num))

        if _looks_like_contents_page(page_text, len(page_matches)):
            continue

        for candidate_index, printed_num in page_matches:
            offset = page_index + 1 - printed_num
            match = offset_matches.setdefault(
                offset, {"pages": set(), "candidates": set()}
            )
            match["pages"].add(page_index)
            match["candidates"].add(candidate_index)

    if not offset_matches:
        return None

    def score(item):
        _, match = item
        return (len(match["candidates"]), len(match["pages"]))

    ranked_offsets = sorted(offset_matches.items(), key=score, reverse=True)
    best_offset, best_match = ranked_offsets[0]
    if len(ranked_offsets) > 1 and score(ranked_offsets[1]) == score(ranked_offsets[0]):
        logger.warning("Infer page offset is ambiguous")
        return None
    if len(best_match["candidates"]) >= 2 and len(best_match["pages"]) >= 2:
        return best_offset

    if log_insufficient:
        logger.warning("Infer page offset does not have enough matching titles")

    return None


def infer_page_offset_from_texts(dir_text, page_texts, max_entries=20):
    """Infer offset using repeated title matches across extracted PDF pages.

    Each matching page creates a candidate offset:
        offset = real_pdf_page_number - printed_page_number

    The correct offset should be shared by multiple table-of-contents entries.
    False matches on the contents page usually produce inconsistent offsets.
    """
    candidates = list(iter_toc_candidates(dir_text, max_entries=max_entries))
    if len(candidates) < 2:
        return None

    return _infer_page_offset_from_candidates(candidates, page_texts)


def extract_pdf_texts(pdf_path, max_pages=None, cancel_callback=None):
    """Extract page texts from a PDF text layer."""
    page_texts = []
    with open(pdf_path, "rb") as handle:
        reader = PdfReader(handle, strict=False)
        for page_index, page in enumerate(reader.pages):
            if max_pages is not None and page_index >= max_pages:
                break
            _check_cancelled(cancel_callback)
            try:
                page_texts.append(page.extract_text() or "")
            except Exception as e:
                logger.warning("Extract page text failed: %s", e)
                page_texts.append("")
    return page_texts


def _load_ocr_dependencies():
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise OcrUnavailableError(
            "OCR fallback requires PyMuPDF, Pillow, pytesseract, and Tesseract OCR"
        ) from e
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.name == "nt" and os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    return fitz, pytesseract, Image


def _tesseract_config():
    tessdata_dir = os.path.join(sys.prefix, "tessdata")
    if os.path.isdir(tessdata_dir):
        return '--tessdata-dir "{}"'.format(tessdata_dir)
    return ""


def _render_matrix(fitz, page, dpi, max_pixels=16_000_000):
    scale = dpi / 72.0
    rect = getattr(page, "rect", None)
    if rect is not None:
        pixel_count = (
            max(float(rect.width), 1) * max(float(rect.height), 1) * scale**2
        )
        if pixel_count > max_pixels:
            scale *= math.sqrt(max_pixels / pixel_count)
    return fitz.Matrix(scale, scale)


def infer_page_offset_by_ocr(
    pdf_path,
    dir_text,
    max_entries=20,
    max_pages=120,
    dpi=160,
    languages="chi_sim+eng",
    progress_callback=None,
    cancel_callback=None,
    timeout=30,
):
    """Infer page offset by OCR, stopping as soon as enough evidence exists."""
    candidates = list(iter_toc_candidates(dir_text, max_entries=max_entries))
    if len(candidates) < 2:
        return None

    fitz, pytesseract, Image = _load_ocr_dependencies()
    page_texts = []
    tesseract_config = _tesseract_config()

    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        raise OcrUnavailableError("Open PDF for OCR failed: {}".format(e)) from e

    try:
        page_count = min(len(document), max_pages)
        first_ocr_error = None
        successful_pages = 0
        for page_index in range(page_count):
            _check_cancelled(cancel_callback)
            page = document.load_page(page_index)
            matrix = _render_matrix(fitz, page, dpi)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            try:
                text = pytesseract.image_to_string(
                    image, lang=languages, config=tesseract_config, timeout=timeout
                )
            except Exception as e:
                logger.warning("OCR page %d failed: %s", page_index + 1, e)
                if first_ocr_error is None:
                    first_ocr_error = e
                text = ""
            else:
                successful_pages += 1
            page_texts.append(text or "")
            if progress_callback:
                progress_callback(page_index + 1, page_count)

            offset = _infer_page_offset_from_candidates(
                candidates, page_texts, log_insufficient=False
            )
            if offset is not None:
                return offset
    finally:
        document.close()

    if not successful_pages and first_ocr_error is not None:
        raise OcrUnavailableError(
            "OCR page text failed: {}".format(first_ocr_error)
        ) from first_ocr_error
    return _infer_page_offset_from_candidates(candidates, page_texts)


def infer_page_offset(
    pdf_path,
    dir_text,
    max_entries=20,
    use_ocr=False,
    ocr_max_pages=120,
    ocr_languages="chi_sim+eng",
    progress_callback=None,
    cancel_callback=None,
    ocr_timeout=30,
):
    """Infer page offset from a PDF and directory text."""
    page_texts = extract_pdf_texts(pdf_path, cancel_callback=cancel_callback)
    offset = infer_page_offset_from_texts(
        dir_text, page_texts, max_entries=max_entries
    )
    if offset is not None or not use_ocr:
        return offset

    return infer_page_offset_by_ocr(
        pdf_path,
        dir_text,
        max_entries=max_entries,
        max_pages=ocr_max_pages,
        languages=ocr_languages,
        progress_callback=progress_callback,
        cancel_callback=cancel_callback,
        timeout=ocr_timeout,
    )
