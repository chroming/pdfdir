# -*- coding:utf-8 -*-

import pytest

from src.convert import *


@pytest.mark.parametrize(
    "lbracket, rbracket",
    [
        ("(", ")"),
        ("[", "]"),
        ("{", "}"),
        ("<", ">"),
        ("（", "）"),
        ("【", "】"),
        ("「", "」"),
        ("《", "》"),
    ],
)
def test_split_page_num(lbracket, rbracket):
    assert split_page_num("ABC%s1%s" % (lbracket, rbracket)) == ("ABC", 1)
    assert split_page_num("ABC %s1%s" % (lbracket, rbracket)) == ("ABC", 1)
    assert split_page_num("ABC") == ("ABC", None)
    assert split_page_num("%s12%s" % (lbracket, rbracket)) == ("", 12)


def test_is_in():
    assert is_in("123", "1") == True
    assert is_in("456", "1") == False
    assert is_in("第1章", r"第\d章") == True


def test_check_level():
    assert check_level("123", "0", "1", "2") == 1
    assert check_level("第2单元 编程基础", None, r"第\d章", r"第\d节") == 0
    assert check_level("第7章 正则", None, r"第\d章", r"第\d节") == 1
    assert check_level("第7节 零宽断言", None, r"第\d章", r"第\d节") == 2
    assert check_level("第7节 零宽断言", None, None, None) == 0


def test_convert_dir_text():
    assert convert_dir_text("第2单元 编程基础---... 23", 0) == {
        0: {"title": "第2单元 编程基础", "num": 23, "real_num": 23}
    }
    assert convert_dir_text(
        "a1\n第2单元 编程基础---... 23 \n第7章 正则 \n第7节 零宽断言\n第8章 正则21\n第3单元 编程实例---... 34",
        1,
        level1=r"第\d章",
        level2=r"第\d节",
        fix_non_seq=True,
    ) == {
        0: {"num": 1, "real_num": 2, "title": "a"},
        1: {"num": 23, "real_num": 24, "title": "第2单元 编程基础"},
        2: {"num": 23, "parent": 1, "real_num": 24, "title": "第7章 正则"},
        3: {"num": 23, "parent": 2, "real_num": 24, "title": "第7节 零宽断言"},
        4: {"num": 23, "parent": 1, "real_num": 24, "title": "第8章 正则"},
        5: {"num": 34, "real_num": 35, "title": "第3单元 编程实例"},
    }
    assert convert_dir_text(
        "a1\n第2单元 编程基础---... 23 \n第7章 正则 \n第7节 零宽断言\nb25\n第8章 正则21\n第3单元 编程实例---... 34",
        1,
        level0=r"第\d单元",
        level1=r"第\d章",
        level2=r"第\d节",
        other=2,
        fix_non_seq=True,
    ) == {
        0: {"num": 1, "real_num": 2, "title": "a"},
        1: {"num": 23, "real_num": 24, "title": "第2单元 编程基础"},
        2: {"num": 23, "parent": 1, "real_num": 24, "title": "第7章 正则"},
        3: {"num": 23, "parent": 2, "real_num": 24, "title": "第7节 零宽断言"},
        4: {"num": 25, "parent": 2, "real_num": 26, "title": "b"},
        5: {"num": 25, "parent": 1, "real_num": 26, "title": "第8章 正则"},
        6: {"num": 34, "real_num": 35, "title": "第3单元 编程实例"},
    }


def test_clean_clipboard_control_chars():
    assert clean_clipboard_control_chars("abc\x00def") == "abcdef"
    assert clean_clipboard_control_chars("abc\x1adef") == "abcdef"
    assert clean_clipboard_control_chars("abc\x03def") == "abcdef"
    assert clean_clipboard_control_chars("normal text") == "normal text"


def test_generate_level_pattern_by_prefix_space():
    dir_list = ["Title 1", "  Subtitle 1", "    Sub-subtitle 1", "Title 2"]
    patterns = generate_level_pattern_by_prefix_space(dir_list)
    assert patterns[0] == r"\s{0}"
    assert patterns[1] == r"\s{2}"
    assert patterns[2] == r"\s{4}"


def test_convert_dir_text_by_space():
    text = "Title 1 1\n  Subtitle 1 2\n    Sub-subtitle 1 3\nTitle 2 4"
    result = convert_dir_text(text, level_by_space=True)
    assert result[0]["title"] == "Title 1"
    assert result[1]["title"] == "Subtitle 1"
    assert result[1]["parent"] == 0
    assert result[2]["title"] == "Sub-subtitle 1"
    assert result[2]["parent"] == 1
    assert result[3]["title"] == "Title 2"
    assert "parent" not in result[3]


def test_convert_dir_text_fix_non_seq():
    # Test without fix_non_seq (default behavior: pagenum increases or stays same)
    text = "Page 10 10\nPage 5 5\nPage 12 12"
    result = convert_dir_text(text, fix_non_seq=False)
    assert result[0]["num"] == 10
    assert result[1]["num"] == 5  # Should be forced to max(previous, current) -> 10
    assert result[2]["num"] == 12

    # Test with fix_non_seq=True (allow non-sequential page numbers)
    # Note: The logic in _convert_dir_text says: if num > pagenum or not fix_non_seq: pagenum = num
    # Wait, let's check the logic in convert.py:
    # if num > pagenum or not fix_non_seq:
    #     pagenum = num
    #
    # Case 1: fix_non_seq = False (default). "not fix_non_seq" is True.
    # Condition is (num > pagenum) OR True. Always True.
    # pagenum is always updated to current num.
    # So "Page 5" becomes 5.
    
    # Case 2: fix_non_seq = True. "not fix_non_seq" is False.
    # Condition is (num > pagenum) OR False.
    # pagenum is updated ONLY if num > pagenum.
    # So if we have 10, then 5. 5 is NOT > 10. pagenum stays 10.
    # So "Page 5" gets num=10.
    
    # So "fix_non_seq" actually means "fix non-sequential numbers by forcing them to be at least the previous number".
    # So if I have 10, 5, 12.
    # fix_non_seq=True -> 10, 10, 12.
    # fix_non_seq=False -> 10, 5, 12.
    
    result_fix = convert_dir_text(text, fix_non_seq=True)
    assert result_fix[0]["num"] == 10
    assert result_fix[1]["num"] == 10
    assert result_fix[2]["num"] == 12
    
    result_no_fix = convert_dir_text(text, fix_non_seq=False)
    assert result_no_fix[0]["num"] == 10
    assert result_no_fix[1]["num"] == 5
    assert result_no_fix[2]["num"] == 12
