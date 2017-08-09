# -*- coding: utf-8 -*-

"""
Add directory bookmarks to the pdf file.

Public:

- function: add_bookmark(path, index_dict)

"""

from .api import Pdf


def _add_bookmark(pdf, index_dict, parent=None):
    for title, dic in index_dict.items():
        paren = pdf.add_bookmark(title, dic['pagenum'], parent=parent)
        child = dic.get('child', None)
        if child:
            return _add_bookmark(child, paren)


def add_bookmark(path, index_dict):
    """
    Add directory bookmarks to the pdf file.
    :param path: pdf file path.
    :param index_dict: bookmarks dict, like {'title0': {'pagenum': 0, 'child': {'title01': {'pagenum': 1}...}}...}
    """
    pdf = Pdf(path)
    _add_bookmark(pdf, index_dict)
    return pdf.save_pdf()

