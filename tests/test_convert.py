import pytest

from src.convert import (
    check_level,
    clean_clipboard_control_chars,
    convert_dir_text,
    generate_level_pattern_by_prefix_space,
    is_in,
    split_page_num,
)


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
    assert split_page_num(f"ABC{lbracket}1{rbracket}") == ("ABC", 1)
    assert split_page_num(f"ABC {lbracket}1{rbracket}") == ("ABC", 1)
    assert split_page_num("ABC") == ("ABC", None)
    assert split_page_num(f"{lbracket}12{rbracket}") == ("", 12)


def test_is_in():
    assert is_in("123", "1") is True
    assert is_in("456", "1") is False
    assert is_in("第1章", r"第\d章") is True


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


def test_missing_page_number_inherits_previous_page():
    result = convert_dir_text("Preface\nChapter One 10\nSection One\nChapter Two 20")

    assert [item["num"] for item in result.values()] == [1, 10, 10, 20]


def test_clean_clipboard_control_chars():
    assert clean_clipboard_control_chars("a\x00b\x1ac\x03d\x04e") == "abcde"


def test_generate_level_pattern_by_prefix_space():
    patterns = generate_level_pattern_by_prefix_space(
        ["Title", "  Section", "    Subsection"]
    )

    assert patterns[:3] == [r"\s{0}", r"\s{2}", r"\s{4}"]
