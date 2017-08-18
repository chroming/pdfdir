# -*- coding: utf-8 -*-

from .convert import convert_dir_text
from pdf.bookmark import add_bookmark


def add_directory(dir_text, offset, pdf_path):
    index_dict = convert_dir_text(dir_text, offset=offset)
    return add_bookmark(pdf_path, index_dict)

