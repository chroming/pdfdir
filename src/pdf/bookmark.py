# -*- coding: utf-8 -*-

"""
Add directory bookmarks to the pdf file.

Public:

- function: add_bookmark(path, index_dict)

"""
import logging

from .api import Pdf

logger = logging.getLogger(__name__)


def _add_bookmark(pdf, index_dict):
    if not index_dict:
        return None
    m = max(index_dict.keys())
    parent_dict = {}  # {parent index:IndirectObject}
    max_page_num = len(pdf.writer.pages) - 1
    for i in range(m+1):
        value = index_dict[i]
        inobject = pdf.add_bookmark(value.get('title', ''),
                                    min(value.get('real_num', 1) - 1, max_page_num),
                                    parent_dict.get(value.get('parent')))
        parent_dict[i] = inobject


def add_bookmark(path, index_dict):
    """
    Add directory bookmarks to the pdf file.
    :param path: pdf file path.
    :param index_dict: bookmarks dict, like {0:{'title':'A', 'pagenum':1}, 1:{'title':'B', pagenum:2, parent: 0} ......}
    """
    pdf = Pdf(path)
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


def check_bookmarks(path, index_dict):
    pdf = Pdf(path)
    max_page_num = len(pdf.writer.pages)
    max_set_page_num = max([v.get('real_num', 1) for v in index_dict.values()])
    if max_set_page_num > max_page_num:
        raise ValueError("Max page number '{}' exceeds the pdf real page number '{}'!".format(max_set_page_num, max_page_num))
