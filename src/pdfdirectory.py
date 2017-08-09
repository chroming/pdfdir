# -*- coding: utf-8 -*-

from .convert import no_child_convert
from pdf.bookmark import add_bookmark


def add_directory(dir_str, offset, pdf_path):
    index_dict = no_child_convert(dir_str, offset=offset)
    add_bookmark(pdf_path, index_dict)

