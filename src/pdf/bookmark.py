# -*- coding: utf-8 -*-

"""
Add directory bookmarks to the pdf file.

Public:

- function: add_bookmark(path, index_dict)

"""

from .api import Pdf


def _add_bookmark(pdf, index_dict):
    if not index_dict:
        return None
    m = max(index_dict.keys())
    parent_dict = {}  # {parent index:IndirectObject}
    max_page_num = pdf.writer.getNumPages() - 1
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

