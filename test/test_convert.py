# -*- coding:utf-8 -*-

from src.convert import *


def test_split_page_num():
    assert split_page_num("ABC1") == ("ABC", 1)
    assert split_page_num("ABC") == ("ABC", -1)
    assert split_page_num("12") == ("", 12)


def test_is_in():
    assert is_in('123', '1') == True
    assert is_in('456', '1') == False
    assert is_in('第1章', '第\d章') == True


def test_check_level():
    assert check_level('123', '1', '2') == 1
    assert check_level('第2单元 编程基础', '第\d章', '第\d节') == 0
    assert check_level('第7章 正则', '第\d章', '第\d节') == 1
    assert check_level('第7节 零宽断言', '第\d章', '第\d节') == 2
    assert check_level('第7节 零宽断言', None, None) == 0


def test_convert_dir_text():
    assert convert_dir_text('第2单元 编程基础---... 23', 0) == {0: {'title': '第2单元 编程基础', 'pagenum': 22}}
    assert convert_dir_text('a1\n第2单元 编程基础---... 23 \n第7章 正则 \n第7节 零宽断言\n第8章 正则21\n第3单元 编程实例---... 34', 1, '第\d章', '第\d节') == {0: {'title': 'a', 'pagenum': 1}, 1: {'title': '第2单元 编程基础', 'pagenum': 23}, 2: {'title': '第7章 正则', 'pagenum': 23, 'parent': 1}, 3: {'title': '第7节 零宽断言', 'pagenum': 23, 'parent': 2}, 4: {'title': '第8章 正则', 'pagenum': 23, 'parent': 1}, 5: {'title': '第3单元 编程实例', 'pagenum': 34}}






