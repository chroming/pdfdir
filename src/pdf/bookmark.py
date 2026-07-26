"""
Add directory bookmarks to the pdf file.

Public:

- function: add_bookmark(path, index_dict)

"""

import logging

from .pdf import Pdf

logger = logging.getLogger(__name__)


def _add_bookmark(pdf, index_dict):
    if not index_dict:
        return
    m = max(index_dict.keys())
    parent_dict = {}  # {parent index:IndirectObject}
    max_page_num = len(pdf.writer.pages) - 1
    for i in range(m + 1):
        value = index_dict[i]
        inobject = pdf.add_bookmark(
            value.get("title", ""),
            min(max(value.get("real_num", 1) - 1, 0), max_page_num),
            parent_dict.get(value.get("parent")),
        )
        parent_dict[i] = inobject


def _validate_bookmarks(pdf, index_dict):
    if not index_dict:
        return

    expected_indexes = set(range(len(index_dict)))
    if set(index_dict) != expected_indexes:
        raise ValueError("Bookmark indexes must be consecutive and start at 0!")

    for index, value in index_dict.items():
        parent = value.get("parent")
        if parent is not None and (
            not isinstance(parent, int)
            or isinstance(parent, bool)
            or parent not in index_dict
            or parent >= index
        ):
            raise ValueError(f"Invalid parent index '{parent}' for bookmark '{index}'!")

    page_numbers = [value.get("real_num", 1) for value in index_dict.values()]
    if any(
        not isinstance(page_number, int) or isinstance(page_number, bool)
        for page_number in page_numbers
    ):
        raise ValueError("Page numbers must be integers!")
    min_page_num = min(page_numbers)
    max_page_num = max(page_numbers)
    pdf_page_count = len(pdf.writer.pages)

    if min_page_num < 1:
        raise ValueError(f"Page number '{min_page_num}' must be at least 1!")
    if max_page_num > pdf_page_count:
        raise ValueError(
            f"Max page number '{max_page_num}' exceeds "
            f"the pdf real page number '{pdf_page_count}'!"
        )


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
            bm["parent"] = new_key_map.get(parent, parent)
        merged.append(bm)
    return merged


def add_bookmark(path, index_dict, keep_exist_dir=False):
    """
    Add directory bookmarks to the pdf file.
    :param path: pdf file path.
    :param index_dict: bookmarks dict, like {0:{'title':'A', 'pagenum':1}, 1:{'title':'B', pagenum:2, parent: 0} ......}
    """
    pdf = Pdf(path, keep_outline=keep_exist_dir)
    _validate_bookmarks(pdf, index_dict)
    _add_bookmark(pdf, index_dict)
    return pdf.save_pdf()


def get_bookmarks(path):
    if not path:
        return []
    try:
        return Pdf(path).exist_bookmarks()
    except Exception as e:  # noqa: BLE001 - invalid third-party PDFs are expected
        logger.warning("Read pdf %s failed! %s", path, e)
        return []


def check_bookmarks(path, index_dict, keep_exist_dir=False):
    if not index_dict:
        return
    pdf = Pdf(path, keep_outline=keep_exist_dir)
    _validate_bookmarks(pdf, index_dict)
