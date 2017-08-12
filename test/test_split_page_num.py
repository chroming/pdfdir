# -*- coding : utf-8 -*-
from src.convert import split_page_num


def test_split_page_num():
    assert split_page_num("ABC1") == ("ABC", 1)
    assert split_page_num("ABC") == ("ABC", -1)
    assert split_page_num("12") == ("", 12)