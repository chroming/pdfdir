# -*- coding: utf-8 -*-

"""Extract table-of-contents text from PDF pages."""

import logging
import os
import re
from io import BytesIO

from src.pdf.cancellation import OperationCancelled
from src.pdf.page_offset import (
    OcrCancelledError,
    OcrUnavailableError,
    _check_cancelled,
    _load_ocr_dependencies,
    _render_matrix,
    _tesseract_config,
    extract_pdf_texts,
    normalize_page_text,
)

logger = logging.getLogger(__name__)


_TOC_LINE_PATTERN = re.compile(r".{2,}\d+\s*$")
_DOT_LEADER_PATTERN = re.compile(r"[\s.\-·•…]{2,}(\d+)\s*$")
_TITLE_PAGE_PATTERN = re.compile(r"(?P<title>.+?)[\s.\-·•…]*(?P<num>\d+)\s*$")
_PAGE_NUMBER_FRAGMENT_PATTERN = re.compile(r"^[\s.\-·•…]*(\d+)\s*$")
_SECTION_NUMBER_ONLY_PATTERN = re.compile(r"^[#\d\s.:：]+$")
_NOISY_TITLE_PATTERN = re.compile(
    r"(isbn|版权|合同|登记号|邮编|出版社|印刷|发行|copyright|http|www|mod\b|=)"
    r"|([a-z]\))",
    re.IGNORECASE,
)


_LONG_LATIN_NOISE_PATTERN = re.compile(r"[A-Za-z]{18,}")


def _clean_toc_line(line):
    line = re.sub(r"\s+", " ", line.strip())
    line = _DOT_LEADER_PATTERN.sub(r" \1", line)
    if not re.match(r"^[§$]?\d+([.:：]\d+)+\s*$", line):
        line = re.sub(r"([^\d\s])(\d+)\s*$", r"\1 \2", line)
    return line.strip()


def _looks_like_toc_fragment(line):
    if not line:
        return False
    return bool(
        re.search(r"[\u4e00-\u9fffA-Za-z]", line)
        or re.match(r"^[§$]?\d+([.:：]\d+)*", line)
    )


def _starts_new_toc_entry(line):
    return bool(
        re.match(r"^(第\s*\d+\s*章|[§$]?\d+([.:：]\d+)*|习题|附录)", line)
    )


def _is_title_only_toc_line(line):
    cleaned = _clean_title_noise(_clean_toc_line(line))
    if not cleaned:
        return False
    if cleaned in ("目录", "目 录"):
        return False
    if cleaned.lower() == "contents":
        return False
    if _TOC_LINE_PATTERN.match(cleaned):
        return False
    if _SECTION_NUMBER_ONLY_PATTERN.match(cleaned):
        return False
    if _NOISY_TITLE_PATTERN.search(cleaned):
        return False
    if not re.match(r"^(第\s*\d+\s*章\s*\S+|[§$]?\d+([.:：]\d+)+\s*\S+)", cleaned):
        return False

    title_chars = re.findall(r"[\u4e00-\u9fffA-Za-z]", cleaned)
    return len(title_chars) >= 2


def _can_keep_toc_title_without_page(title):
    cleaned = _clean_title_noise(_clean_toc_line(title))
    if not cleaned:
        return False
    if cleaned in ("目录", "目 录"):
        return False
    if cleaned.lower() == "contents":
        return False
    if _SECTION_NUMBER_ONLY_PATTERN.match(cleaned):
        return False
    if _NOISY_TITLE_PATTERN.search(cleaned):
        return False
    if not re.match(r"^(第\s*\d+\s*章|[§$]?\d+([.:：]\d+)+|习题|附录)", cleaned):
        return False

    title_chars = re.findall(r"[\u4e00-\u9fffA-Za-z]", cleaned)
    return len(title_chars) >= 2


def _merge_wrapped_toc_lines(text, max_fragments=4):
    merged_lines = []
    pending = []

    def pending_text():
        return " ".join(pending).strip()

    def flush_title_only_pending():
        text = pending_text()
        if _is_title_only_toc_line(text):
            merged_lines.append(text)

    for raw_line in text.splitlines():
        line = _clean_toc_line(raw_line)
        if not line:
            continue

        page_match = _PAGE_NUMBER_FRAGMENT_PATTERN.match(line)
        if page_match and pending:
            merged_lines.append("{} {}".format(pending_text(), page_match.group(1)))
            pending = []
            continue

        if _is_toc_line(line):
            merged_lines.append(line)
            pending = []
            continue

        if not _looks_like_toc_fragment(line):
            continue

        if pending and _starts_new_toc_entry(line):
            flush_title_only_pending()
            pending = []
        pending.append(line)
        if len(pending) > max_fragments:
            pending = pending[-max_fragments:]

    flush_title_only_pending()
    return merged_lines


def _has_cjk(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _is_heading_number(token):
    return bool(re.match(r"^\d+([.:]\d+)*[.:]?$", token))


def _looks_like_regular_latin_word(token):
    normalized = re.sub(r"[^A-Za-z-]+", "", token)
    if not 4 <= len(normalized) <= 24:
        return False
    if _LONG_LATIN_NOISE_PATTERN.search(normalized):
        return False
    if not re.match(r"^[A-Za-z]+(?:-[A-Za-z]+)*$", normalized):
        return False

    letters = normalized.replace("-", "")
    uppercase_count = sum(1 for char in letters if char.isupper())
    lowercase_count = sum(1 for char in letters if char.islower())
    if uppercase_count == 0:
        return False
    if lowercase_count < 2:
        return False
    return uppercase_count <= 3


def _looks_like_latin_title(title):
    words = re.findall(r"[A-Za-z]+", title)
    if not words:
        return False
    if _LONG_LATIN_NOISE_PATTERN.search(title):
        return False

    lowercase_count = sum(1 for char in title if char.islower())
    if lowercase_count:
        return len(title) <= 80

    if len(words) == 1:
        return len(words[0]) >= 4
    if len(words) > 2:
        return False
    if max(len(word) for word in words) < 7:
        return False
    return True


def _should_keep_latin_token(token, previous_token="", next_token=""):
    normalized = re.sub(r"[^A-Za-z0-9-]+", "", token)
    if not normalized:
        return True
    if _is_heading_number(token):
        return True
    if not re.search(r"[A-Za-z]", normalized):
        return True

    letters = re.sub(r"[^A-Za-z]+", "", normalized)
    if letters.isupper() and len(letters) == 1:
        return bool(re.search(r"第\s*\d+\s*章", previous_token))
    if letters.isupper() and 2 <= len(letters) <= 12:
        return True

    adjacent_to_cjk = _has_cjk(previous_token) or _has_cjk(next_token)
    return adjacent_to_cjk and _looks_like_regular_latin_word(token)


def _clean_embedded_latin_noise(token):
    if not re.search(r"[\u4e00-\u9fff]", token):
        return token
    token = re.sub(r"^[0-9a-z]{3,}([\u4e00-\u9fff].*)$", r"\1", token)
    return re.sub(
        r"([\u4e00-\u9fff])([A-Za-z0-9'’<>{}\[\]_/|\\:;,.`~]{2,}.*)$",
        r"\1",
        token,
    )


def _clean_mixed_title_tokens(title):
    raw_tokens = title.split()
    tokens = []
    for index, token in enumerate(raw_tokens):
        token = _clean_embedded_latin_noise(token)
        if not token:
            continue
        if _has_cjk(token):
            tokens.append(token)
            continue
        previous_token = raw_tokens[index - 1] if index > 0 else ""
        next_token = raw_tokens[index + 1] if index + 1 < len(raw_tokens) else ""
        if _should_keep_latin_token(token, previous_token, next_token):
            tokens.append(token)
    return " ".join(tokens)


def _clean_title_noise(title):
    title = _clean_mixed_title_tokens(title)
    title = re.sub(r"[\s.\-·•…_]+$", "", title.strip())
    title = re.sub(r"\s+(?:和|站|ee|to|of)+$", "", title, flags=re.IGNORECASE)
    if re.search(r"[\u4e00-\u9fff]", title):
        match = list(re.finditer(r"[\u4e00-\u9fff]", title))
        if match:
            last_cjk_end = match[-1].end()
            suffix = title[last_cjk_end:]
            if len(re.findall(r"[A-Za-z]", suffix)) >= 4 and not _has_cjk(suffix):
                title = title[:last_cjk_end]
            if len(suffix) >= 5 and re.match(r"^[A-Za-z0-9\s.\-·•…_,;'\"`]+$", suffix):
                title = title[:last_cjk_end]
    return title.strip()


def _is_toc_line(line):
    cleaned = _clean_toc_line(line)
    if len(cleaned) < 3:
        return False
    if not _TOC_LINE_PATTERN.match(cleaned):
        return False

    match = _TITLE_PAGE_PATTERN.match(cleaned)
    if not match:
        return False

    title = match.group("title").strip()
    title = _clean_title_noise(title)
    if _SECTION_NUMBER_ONLY_PATTERN.match(title):
        return False
    if _NOISY_TITLE_PATTERN.search(title):
        return False

    title_chars = re.findall(r"[\u4e00-\u9fffA-Za-z]", title)
    if len(title_chars) < 2:
        return False
    if not _has_cjk(title) and not _looks_like_latin_title(title):
        return False

    return True


def _looks_like_toc_page(text):
    normalized = normalize_page_text(text)
    lines = [_clean_toc_line(line) for line in text.splitlines()]
    toc_line_count = sum(1 for line in lines if _is_toc_line(line))
    return "目录" in normalized or "contents" in normalized or toc_line_count >= 3


def _extract_toc_entries_from_text(text):
    page_entries = []
    if not text:
        return page_entries

    seen = set()
    for line in text.splitlines():
        cleaned = _clean_toc_line(line)
        if _is_toc_line(cleaned):
            match = _TITLE_PAGE_PATTERN.match(cleaned)
            title = _clean_title_noise(match.group("title"))
            page_line = "{} {}".format(title, match.group("num"))
            if page_line not in seen:
                page_entries.append((page_line, True))
                seen.add(page_line)

    for line in _merge_wrapped_toc_lines(text):
        cleaned = _clean_toc_line(line)
        if _is_toc_line(cleaned):
            match = _TITLE_PAGE_PATTERN.match(cleaned)
            title = _clean_title_noise(match.group("title"))
            page_line = "{} {}".format(title, match.group("num"))
            if page_line not in seen:
                page_entries.append((page_line, True))
                seen.add(page_line)
            continue

        if _is_title_only_toc_line(cleaned):
            page_line = _clean_title_noise(cleaned)
            if page_line not in seen:
                page_entries.append((page_line, False))
                seen.add(page_line)
    return _normalize_toc_entry_page_order(page_entries)


def _split_toc_entry_page(line):
    match = _TITLE_PAGE_PATTERN.match(_clean_toc_line(line))
    if not match:
        return line, None
    return _clean_title_noise(match.group("title")), int(match.group("num"))


def _normalize_toc_entry_page_order(
    page_entries,
    max_backward_gap=5,
    max_forward_jump=500,
):
    normalized_entries = []
    last_page_num = None
    for index, (line, has_page) in enumerate(page_entries):
        if not has_page:
            normalized_entries.append((line, has_page))
            continue

        title, page_num = _split_toc_entry_page(line)
        future_page_nums = [
            _split_toc_entry_page(future_line)[1]
            for future_line, future_has_page in page_entries[index + 1 :]
            if future_has_page
        ]
        future_recovers = (
            last_page_num is not None
            and any(
                num is not None and num + max_backward_gap >= last_page_num
                for num in future_page_nums
            )
        )
        suspicious_page = (
            last_page_num is not None
            and page_num is not None
            and page_num + max_backward_gap < last_page_num
            and (
                future_recovers
                or (page_num < 10 <= last_page_num)
                or (
                    _clean_title_noise(title).startswith("习题")
                    and page_num < 10 <= last_page_num
                )
            )
        )
        suspicious_page = suspicious_page or (
            last_page_num is not None
            and page_num is not None
            and page_num > last_page_num + max_forward_jump
        )

        if suspicious_page:
            if _can_keep_toc_title_without_page(title):
                normalized_entries.append((title, False))
            continue

        normalized_entries.append((line, has_page))
        if page_num is not None:
            last_page_num = page_num
    return normalized_entries


def extract_toc_text_from_page_texts(page_texts):
    page_toc_entries = []
    for text in page_texts:
        page_toc_entries.append(_extract_toc_entries_from_text(text))

    selected_lines = _select_toc_page_block(page_toc_entries)
    if not selected_lines:
        for text, page_entries in zip(page_texts, page_toc_entries):
            if (
                _looks_like_toc_page(text)
                and _toc_entry_count(page_entries, require_page=True) >= 2
            ):
                selected_lines = [line for line, _ in page_entries]
                break
    return "\n".join(selected_lines)


def _toc_entry_count(page_entries, require_page=False):
    if require_page:
        return sum(1 for _, has_page in page_entries if has_page)
    return len(page_entries)


def _is_strong_toc_page(page_entries, strong_threshold):
    page_count = _toc_entry_count(page_entries, require_page=True)
    return page_count >= strong_threshold or (
        page_count >= 2 and _toc_entry_count(page_entries) >= strong_threshold
    )


def _select_toc_page_block(page_toc_entries, strong_threshold=3, tail_threshold=2):
    best_start = None
    best_end = None
    best_score = 0
    i = 0
    while i < len(page_toc_entries):
        if not _is_strong_toc_page(page_toc_entries[i], strong_threshold):
            i += 1
            continue

        start = i
        end = i + 1
        score = _toc_entry_count(page_toc_entries[i], require_page=True)
        saw_weak_tail = False
        while end < len(page_toc_entries):
            line_count = _toc_entry_count(page_toc_entries[end], require_page=True)
            if line_count >= strong_threshold:
                score += line_count
                saw_weak_tail = False
                end += 1
                continue
            if line_count >= tail_threshold and not saw_weak_tail:
                score += line_count
                saw_weak_tail = True
                end += 1
                continue
            break

        if score > best_score:
            best_start = start
            best_end = end
            best_score = score
        i = end

    if best_start is None:
        return []

    selected = []
    for page_entries in page_toc_entries[best_start:best_end]:
        selected.extend(line for line, _ in page_entries)
    return selected


def _load_render_dependencies():
    try:
        import fitz
        from PIL import Image
    except ImportError as e:
        raise OcrUnavailableError(
            "OCR requires PyMuPDF and Pillow to render PDF pages"
        ) from e
    return fitz, Image


def _load_paddleocr_dependencies(languages="ch"):
    cache_root = os.path.join(
        os.environ.get(
            "XDG_CACHE_HOME", os.path.expanduser(os.path.join("~", ".cache"))
        ),
        "pdfdir",
    )
    os.environ.setdefault("PADDLE_HOME", os.path.join(cache_root, "paddle"))
    os.environ.setdefault(
        "PADDLE_PDX_CACHE_HOME", os.path.join(cache_root, "paddlex")
    )
    os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")

    try:
        import numpy as np
        from paddleocr import PaddleOCR
    except ImportError as e:
        raise OcrUnavailableError(
            "PaddleOCR backend requires paddleocr and paddlepaddle"
        ) from e

    lang = _paddleocr_lang(languages)
    try:
        try:
            ocr = PaddleOCR(
                lang=lang,
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                text_det_limit_side_len=1280,
            )
        except (TypeError, ValueError):
            try:
                ocr = PaddleOCR(lang=lang, use_textline_orientation=False)
            except (TypeError, ValueError):
                ocr = PaddleOCR(lang=lang)
    except Exception as e:
        raise OcrUnavailableError(
            "Initialize PaddleOCR failed: {}".format(e)
        ) from e
    return np, ocr


def _paddleocr_lang(languages):
    normalized = (languages or "").lower()
    if "chi" in normalized or "ch" in normalized or "zh" in normalized:
        return "ch"
    if "eng" in normalized or "en" in normalized:
        return "en"
    return "ch"


def _tesseract_languages(languages):
    normalized = (languages or "").strip().lower()
    language_map = {
        "ch": "chi_sim+eng",
        "zh": "chi_sim+eng",
        "zh-cn": "chi_sim+eng",
        "en": "eng",
    }
    return language_map.get(normalized, languages or "chi_sim+eng")


def _collect_paddleocr_texts(result):
    texts = []

    def collect(item):
        if item is None:
            return
        if isinstance(item, dict):
            for key in ("rec_texts", "texts"):
                value = item.get(key)
                if isinstance(value, list):
                    texts.extend(str(text) for text in value if text)
                    return
            if "res" in item:
                collect(item["res"])
                return
            text = item.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
            return
        if isinstance(item, tuple) and item and isinstance(item[0], str):
            texts.append(item[0])
            return
        if isinstance(item, list):
            if (
                len(item) >= 2
                and isinstance(item[1], (tuple, list))
                and item[1]
                and isinstance(item[1][0], str)
            ):
                texts.append(item[1][0])
                return
            for child in item:
                collect(child)

    collect(result)
    return texts


def _render_pdf_pages(pdf_path, max_pages, dpi):
    fitz, Image = _load_render_dependencies()

    document = fitz.open(pdf_path)
    try:
        page_count = min(len(document), max_pages)
        for page_index in range(page_count):
            page = document.load_page(page_index)
            matrix = _render_matrix(fitz, page, dpi)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
            yield page_index, page_count, image
    finally:
        document.close()


def _paddleocr_image_to_text(ocr, np, image):
    image_array = np.array(image)
    if hasattr(ocr, "predict"):
        result = ocr.predict(image_array)
        return "\n".join(_collect_paddleocr_texts(result))

    try:
        result = ocr.ocr(image_array, cls=True)
    except TypeError:
        result = ocr.ocr(image_array)
    return "\n".join(_collect_paddleocr_texts(result))


def extract_toc_text_by_paddleocr(
    pdf_path,
    max_pages=30,
    dpi=130,
    languages="ch",
    progress_callback=None,
    cancel_callback=None,
    cancel_check=None,
):
    _check_cancelled(cancel_callback, cancel_check)
    np, ocr = _load_paddleocr_dependencies(languages)
    page_texts = []
    seen_toc_page = False
    weak_pages_after_toc = 0

    try:
        rendered_pages = _render_pdf_pages(pdf_path, max_pages, dpi)
        try:
            for page_index, page_count, image in rendered_pages:
                _check_cancelled(cancel_callback, cancel_check)
                text = _paddleocr_image_to_text(ocr, np, image)
                page_texts.append(text)
                page_entries = _extract_toc_entries_from_text(text)
                if progress_callback:
                    progress_callback(page_index + 1, page_count)

                if _toc_entry_count(page_entries, require_page=True) >= 3:
                    seen_toc_page = True
                    weak_pages_after_toc = 0
                elif seen_toc_page:
                    weak_pages_after_toc += 1
                    if weak_pages_after_toc >= 2:
                        break
        finally:
            close_pages = getattr(rendered_pages, "close", None)
            if close_pages:
                close_pages()
    except Exception as e:
        if isinstance(
            e,
            (OcrUnavailableError, OcrCancelledError, OperationCancelled),
        ):
            raise
        raise OcrUnavailableError("PaddleOCR page text failed: {}".format(e)) from e

    return extract_toc_text_from_page_texts(page_texts)


def extract_toc_text_by_tesseract(
    pdf_path,
    max_pages=30,
    dpi=240,
    languages="chi_sim+eng",
    progress_callback=None,
    cancel_callback=None,
    timeout=30,
    cancel_check=None,
):
    _check_cancelled(cancel_callback, cancel_check)
    fitz, pytesseract, Image = _load_ocr_dependencies()
    config = "{} --psm 4 -c preserve_interword_spaces=1".format(_tesseract_config())
    page_texts = []

    document = fitz.open(pdf_path)
    try:
        page_count = min(len(document), max_pages)
        first_page_error = None
        successful_pages = 0
        for page_index in range(page_count):
            try:
                _check_cancelled(cancel_callback, cancel_check)
                page = document.load_page(page_index)
                matrix = _render_matrix(fitz, page, dpi)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.open(BytesIO(pixmap.tobytes("png")))
                text = pytesseract.image_to_string(
                    image, lang=languages, config=config, timeout=timeout
                )
            except OperationCancelled:
                raise
            except Exception as e:
                logger.warning(
                    "Render or OCR page %d failed: %s",
                    page_index + 1,
                    e,
                )
                if first_page_error is None:
                    first_page_error = e
                text = ""
            else:
                successful_pages += 1
            page_texts.append(text or "")
            if progress_callback:
                progress_callback(page_index + 1, page_count)
    finally:
        document.close()

    if not successful_pages and first_page_error is not None:
        raise OcrUnavailableError(
            "OCR page text failed: {}".format(first_page_error)
        ) from first_page_error
    return extract_toc_text_from_page_texts(page_texts)


def extract_toc_text_by_ocr(
    pdf_path,
    max_pages=30,
    dpi=130,
    languages="ch",
    progress_callback=None,
    backend="paddle",
    fallback_to_tesseract=True,
    cancel_callback=None,
    timeout=30,
    cancel_check=None,
):
    _check_cancelled(cancel_callback, cancel_check)
    if backend == "tesseract":
        return extract_toc_text_by_tesseract(
            pdf_path,
            max_pages=max_pages,
            dpi=240 if dpi == 220 else dpi,
            languages=_tesseract_languages(languages),
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
            timeout=timeout,
            cancel_check=cancel_check,
        )
    if backend != "paddle":
        raise ValueError("Unknown OCR backend: {}".format(backend))

    try:
        toc_text = extract_toc_text_by_paddleocr(
            pdf_path,
            max_pages=max_pages,
            dpi=dpi,
            languages=languages,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
            cancel_check=cancel_check,
        )
        if toc_text or not fallback_to_tesseract:
            return toc_text
    except OcrUnavailableError:
        if not fallback_to_tesseract:
            raise

    return extract_toc_text_by_tesseract(
        pdf_path,
        max_pages=max_pages,
        languages=_tesseract_languages(languages),
        progress_callback=progress_callback,
        cancel_callback=cancel_callback,
        timeout=timeout,
        cancel_check=cancel_check,
    )


def extract_toc_text(
    pdf_path,
    max_pages=30,
    use_ocr=True,
    ocr_backend="paddle",
    progress_callback=None,
    cancel_callback=None,
    ocr_timeout=30,
    cancel_check=None,
):
    _check_cancelled(cancel_callback, cancel_check)
    extract_kwargs = {
        "max_pages": max_pages,
        "cancel_callback": cancel_callback,
    }
    if cancel_check is not None:
        extract_kwargs["cancel_check"] = cancel_check
    page_texts = extract_pdf_texts(pdf_path, **extract_kwargs)
    toc_text = extract_toc_text_from_page_texts(page_texts)
    if toc_text or not use_ocr:
        return toc_text

    return extract_toc_text_by_ocr(
        pdf_path,
        max_pages=max_pages,
        backend=ocr_backend,
        progress_callback=progress_callback,
        cancel_callback=cancel_callback,
        timeout=ocr_timeout,
        cancel_check=cancel_check,
    )
