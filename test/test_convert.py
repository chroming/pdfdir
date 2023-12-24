# -*- coding:utf-8 -*-

from src.convert import *
import pytest


@pytest.mark.parametrize("lbracket, rbracket", [("(", ")"),
                                                ("[", "]"),
                                                ("{", "}"),
                                                ("<", ">"),
                                                ("（", "）"),
                                                ("【", "】"),
                                                ("「", "」"),
                                                ("《", "》")])
def test_split_page_num(lbracket, rbracket):
    assert split_page_num("ABC%s1%s" % (lbracket, rbracket)) == ("ABC", 1)
    assert split_page_num("ABC %s1%s" % (lbracket, rbracket)) == ("ABC", 1)
    assert split_page_num("ABC") == ("ABC", 1)
    assert split_page_num("%s12%s" % (lbracket, rbracket)) == ("", 12)


def test_is_in():
    assert is_in('123', '1') == True
    assert is_in('456', '1') == False
    assert is_in('第1章', '第\d章') == True


def test_check_level():
    assert check_level('123', '0', '1', '2') == 1
    assert check_level('第2单元 编程基础', None, '第\d章', '第\d节') == 0
    assert check_level('第7章 正则', None, '第\d章', '第\d节') == 1
    assert check_level('第7节 零宽断言', None, '第\d章', '第\d节') == 2
    assert check_level('第7节 零宽断言', None, None, None) == 0


def test_convert_dir_text():
    assert convert_dir_text('第2单元 编程基础---... 23', 0) == {
        0: {'title': '第2单元 编程基础', 'num': 23, 'real_num': 23}}
    assert convert_dir_text(
        'a1\n第2单元 编程基础---... 23 \n第7章 正则 \n第7节 零宽断言\n第8章 正则21\n第3单元 编程实例---... 34', 1,
        level1='第\d章', level2='第\d节') == {0: {'num': 1, 'real_num': 2, 'title': 'a'},
                                              1: {'num': 23, 'real_num': 24, 'title': '第2单元 编程基础'},
                                              2: {'num': 23, 'parent': 1, 'real_num': 24, 'title': '第7章 正则'},
                                              3: {'num': 23, 'parent': 2, 'real_num': 24, 'title': '第7节 零宽断言'},
                                              4: {'num': 23, 'parent': 1, 'real_num': 24, 'title': '第8章 正则'},
                                              5: {'num': 34, 'real_num': 35, 'title': '第3单元 编程实例'}}
    assert convert_dir_text(
        'a1\n第2单元 编程基础---... 23 \n第7章 正则 \n第7节 零宽断言\nb25\n第8章 正则21\n第3单元 编程实例---... 34', 1,
        level0='第\d单元', level1='第\d章', level2='第\d节', other=2) == {0: {'num': 1, 'real_num': 2, 'title': 'a'},
                                                                          1: {'num': 23, 'real_num': 24,
                                                                              'title': '第2单元 编程基础'},
                                                                          2: {'num': 23, 'parent': 1, 'real_num': 24,
                                                                              'title': '第7章 正则'},
                                                                          3: {'num': 23, 'parent': 2, 'real_num': 24,
                                                                              'title': '第7节 零宽断言'},
                                                                          4: {'num': 25, 'parent': 2, 'real_num': 26,
                                                                              'title': 'b'},
                                                                          5: {'num': 25, 'parent': 1, 'real_num': 26,
                                                                              'title': '第8章 正则'},
                                                                          6: {'num': 34, 'real_num': 35,
                                                                              'title': '第3单元 编程实例'}}
