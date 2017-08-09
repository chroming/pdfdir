# -*- coding: utf-8 -*-

from .convert import no_child_convert
from pdf.bookmark import add_bookmark


def add_directory(dir_text, offset, pdf_path):
    index_dict = no_child_convert(dir_text, offset=offset)
    return add_bookmark(pdf_path, index_dict)

