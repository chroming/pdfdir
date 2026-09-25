# -*- coding: utf-8 -*-

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
        return None
    m = max(index_dict.keys())
    parent_dict = {}  # {parent index:IndirectObject}
    max_page_num = len(pdf.writer.pages) - 1
    for i in range(m + 1):
        value = index_dict[i]
        inobject = pdf.add_bookmark(
            value.get("title", ""),
            min(value.get("real_num", 1) - 1, max_page_num),
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


def add_bookmark(path, index_dict, keep_exist_dir=False, page_label_plan=None):
    """
    Add directory bookmarks to the pdf file.
    :param path: pdf file path.
    :param index_dict: bookmarks dict, like {0:{'title':'A', 'pagenum':1}, 1:{'title':'B', pagenum:2, parent: 0} ......}
    """
    pdf = Pdf(
        path, keep_outline=keep_exist_dir, page_label_plan=page_label_plan
    )
    check_bookmarks(path, index_dict, keep_exist_dir)
    _add_bookmark(pdf, index_dict)
    return pdf.save_pdf()


def get_bookmarks(path):
    if not path:
        return []
    try:
        return Pdf(path).exist_bookmarks()
    except Exception as e:
        logging.warning("Read pdf %s failed! %s" % (path, e))
        return []


def check_bookmarks(path, index_dict, keep_exist_dir=False):
    if not index_dict:
        return
    from pypdf import PdfReader

    max_page_num = len(PdfReader(path).pages)
    for value in index_dict.values():
        page = value.get("real_num", 1)
        if not isinstance(page, int) or not 1 <= page <= max_page_num:
            raise ValueError(
                "Bookmark page '{}' must be between 1 and {}".format(page, max_page_num)
            )
