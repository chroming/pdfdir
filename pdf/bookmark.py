# -*- coding: utf-8 -*-

"""
Add directory bookmarks to the pdf file.

Public:

- function: add_bookmark(path, index_dict)

"""

from .api import Pdf


def _add_bookmark(pdf, index_dict):
    m = max(index_dict.keys())
    for i in range(m):
        value = index_dict[i]
        pdf.add_bookmark(value.get('title', ''), value.get('pagenum', 0), value.get('parent'))


def add_bookmark(path, index_dict):
    """
    Add directory bookmarks to the pdf file.
    :param path: pdf file path.
    :param index_dict: bookmarks dict, like {0:{'title':'A', 'pagenum':1}, 1:{'title':'B', pagenum:2, parent: 0} ......}
    """
    pdf = Pdf(path)
    _add_bookmark(pdf, index_dict)
    return pdf.save_pdf()

