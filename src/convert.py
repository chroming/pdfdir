# -*- coding: utf-8 -*-

"""Convert a directory which from website to index dict"""

import re
from collections import OrderedDict


def split_page_num(text):
    """split between title and page num"""
    text = text.strip()
    args = re.split('(\d*$)', text)
    if len(args) > 1:
        return args[0], int(args[1])
    return args[0], -1


def text_to_list(text):
    return text.splitlines()


def no_child_convert(dir_text, offset=0):
    """
    convert a directory with out child directory

    :param: dir_text: unicode, the directory text, usually copy from a bookstore like amazon.
    :param: offset: int, the offset of this book.
    :return: the dict of directory, like {'title0': {'pagenum': 0, 'child': {'title01': {'pagenum': 1}...}}...}
    """
    index_dict = OrderedDict()
    pagenum = 0
    dir_list = text_to_list(dir_text)
    for di in dir_list:
        title, num = split_page_num(di)
        if num != -1 and num > pagenum:
            pagenum = num
        index_dict[title] = {'pagenum': pagenum+offset-1}
    return index_dict

