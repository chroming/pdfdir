# -*- coding: utf-8 -*-

from src.convert import convert_dir_text
from src.pdf.bookmark import add_bookmark


def add_directory(dir_text, offset, pdf_path, level0=None, level1=None, level2=None, other=0):
    index_dict = convert_dir_text(dir_text, offset, level0, level1, level2, other)
    return add_bookmark(pdf_path, index_dict)