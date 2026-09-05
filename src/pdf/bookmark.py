# -*- coding: utf-8 -*-

"""
Add directory bookmarks to the pdf file.

Public:

- function: add_bookmark(path, index_dict)

"""

import logging

from src.pdf.cancellation import raise_if_cancelled

from .pdf import Pdf

logger = logging.getLogger(__name__)


class BookmarkPageError(ValueError):
    """A bookmark targets a page outside the source PDF."""

    def __init__(self, reason, page_number, page_count=None):
        self.reason = reason
        self.page_number = page_number
        self.page_count = page_count
        if reason == "below_minimum":
            message = "Bookmark page number '{}' must be at least 1!".format(
                page_number
            )
        else:
            message = (
                "Max page number '{}' exceeds the pdf real page number '{}'!"
            ).format(page_number, page_count)
        super(BookmarkPageError, self).__init__(message)


def _add_bookmark(pdf, index_dict, cancel_check=None):
    _validate_bookmark_structure(index_dict)
    if not index_dict:
        return None
    m = max(index_dict.keys())
    parent_dict = {}  # {parent index:IndirectObject}
    max_page_num = len(pdf.writer.pages) - 1
    for i in range(m + 1):
        raise_if_cancelled(cancel_check)
        value = index_dict[i]
        real_page_num = value.get("real_num", 1)
        if real_page_num < 1:
            raise BookmarkPageError(
                "below_minimum",
                real_page_num,
            )
        if real_page_num > max_page_num + 1:
            raise BookmarkPageError(
                "above_maximum",
                real_page_num,
                max_page_num + 1,
            )
        inobject = pdf.add_bookmark(
            value.get("title", ""),
            real_page_num - 1,
            parent_dict.get(value.get("parent")),
        )
        parent_dict[i] = inobject


def merge_bookmarks(existing_bookmarks, new_bookmarks):
    """
    Merge existing bookmarks with new bookmarks.
    :param existing_bookmarks: List of existing bookmarks.
    :param new_bookmarks: List of new bookmarks (index_dict.values()).
    :return: Merged bookmarks list
    """
    merged = existing_bookmarks.copy()
    offset = len(existing_bookmarks)
    new_key_map = {}
    for i, new in enumerate(new_bookmarks):
        new_key_map[i] = offset + i
    for i, new in enumerate(new_bookmarks):
        bm = {"title": new["title"], "pagenum": new["pagenum"]}
        parent = new.get("parent")
        if parent is not None:
            if parent in new_key_map:
                bm["parent"] = new_key_map[parent]
            else:
                bm["parent"] = parent
        merged.append(bm)
    return merged


def add_bookmark(
    path,
    index_dict,
    keep_exist_dir=False,
    cancel_check=None,
    expected_output_fingerprint=None,
    enforce_output_fingerprint=False,
    output_path=None,
):
    """
    Add directory bookmarks to the pdf file.
    :param path: pdf file path.
    :param index_dict: bookmarks dict, like {0:{'title':'A', 'pagenum':1}, 1:{'title':'B', pagenum:2, parent: 0} ......}
    """
    pdf = Pdf(
        path,
        keep_outline=keep_exist_dir,
        output_path=output_path,
    )
    _add_bookmark(pdf, index_dict, cancel_check=cancel_check)
    return pdf.save_pdf(
        cancel_check=cancel_check,
        expected_output_fingerprint=expected_output_fingerprint,
        enforce_output_fingerprint=enforce_output_fingerprint,
    )


def get_bookmarks(path):
    if not path:
        return []
    try:
        return get_bookmarks_strict(path)
    except Exception as e:
        logging.warning("Read pdf %s failed! %s" % (path, e))
        return []


def get_bookmarks_strict(path):
    """Return existing bookmarks while preserving PDF read failures."""
    if not path:
        return []
    return Pdf(path).exist_bookmarks()


def _validate_bookmark_structure(index_dict):
    if set(index_dict) != set(range(len(index_dict))):
        raise ValueError("Bookmark indexes must be consecutive and start at 0!")
    for index, value in index_dict.items():
        parent = value.get("parent")
        if parent is not None and (
            not isinstance(parent, int) or isinstance(parent, bool)
            or parent not in index_dict or parent >= index
        ):
            raise ValueError(f"Invalid parent index '{parent}' for bookmark '{index}'!")
        page = value.get("real_num", 1)
        if not isinstance(page, int) or isinstance(page, bool):
            raise ValueError("Page numbers must be integers!")


def check_bookmarks(path, index_dict, keep_exist_dir=False):
    _validate_bookmark_structure(index_dict)
    if not index_dict:
        return
    pdf = Pdf(path, keep_outline=keep_exist_dir)
    # Validation must stay read-only and cheap; building the writer copies the
    # entire document and belongs in the background write worker.
    max_page_num = len(pdf.reader.pages)
    page_numbers = [v.get("real_num", 1) for v in index_dict.values()]
    min_set_page_num = min(page_numbers)
    if min_set_page_num < 1:
        raise BookmarkPageError(
            "below_minimum",
            min_set_page_num,
        )
    max_set_page_num = max(page_numbers)
    if max_set_page_num > max_page_num:
        raise BookmarkPageError(
            "above_maximum",
            max_set_page_num,
            max_page_num,
        )
