# -*- coding: utf-8 -*-

"""Convert a directory text which from website to index dict"""

import re
import logging

logger = logging.getLogger(__name__)


def split_page_num(text):
    """split between title and page number"""
    page_num_patterns = [
        # Support negative numbers
        r"((?<!-)-?\d+)",
        # Support () around numbers
        r"\((\d+)\)",
        # Support [] around numbers
        r"\[(\d+)\]",
        # Support {} around numbers
        r"\{(\d+)\}",
        # Support <> around numbers
        r"\<(\d+)\>",
        # Support（）around numbers
        r"（(\d+)）",
        # Support【】around numbers
        r"【(\d+)】",
        # Support「」around numbers
        r"「(\d+)」",
        # Support《》around numbers
        r"《(\d+)》",
        # Final pattern, without numbers
        r"(\d*)",
    ]
    con, num = "", 1
    # con, num = re.search(r"(.*?)((?<!-)-?\d+$|\d*$)", text).groups()
    for pat in page_num_patterns:
        res = re.search("(.*?)%s$" % pat, text)
        if res:
            con, num = res.groups()
            break
    if con:
        con = con.rstrip(" .-")
    if num == "":
        num = 1
    return con, int(num)


def text_to_list(text):
    if isinstance(text, list):
        return text
    return text.splitlines()


def is_in(title, exp):
    try:
        return bool(re.match(exp, title)) if exp else False
    except re.error as e:
        logger.error("Check regex error! %s", e)
        return False


def clean_clipboard_control_chars(text: str) -> str:
    """
    Clean control characters that could cause clipboard operations to fail

    Core control characters handled:
    - 0x00 (NUL): String terminator in Windows, will truncate strings
    - 0x1A (SUB/Ctrl+Z): EOF marker in Windows, may truncate content

    Optional control characters:
    - 0x03 (ETX/Ctrl+C): Break signal, may interrupt copy operation
    - 0x04 (EOT/Ctrl+D): EOF in Unix, may need handling in cross-platform scenarios
    """
    # Core problematic characters that must be handled
    critical_chars = {
        "\x00",  # NUL - Will truncate string
        "\x1a",  # SUB/Ctrl+Z - May truncate in Windows
    }

    # Extended problematic characters (for stricter handling if needed)
    extended_chars = {
        "\x03",  # ETX/Ctrl+C
        "\x04",  # EOT/Ctrl+D
    }

    problematic_chars = critical_chars | extended_chars  # Strict version

    return "".join(char for char in text if char not in problematic_chars)


def check_level(
    title, level0, level1, level2, level3=None, level4=None, level5=None, other=0
):
    """check the level of this title"""
    ls = [level0, level1, level2, level3, level4, level5]
    for i in range(len(ls)):
        idx = len(ls) - 1 - i  # reserve match
        if is_in(title, ls[idx]):
            return idx
    # no level found
    return other


def generate_level_pattern_by_prefix_space(dir_list):
    """Generate regex pattern by prefix space in dir text"""
    level_patterns = [None, None, None, None, None, None]
    # All space count in dir text
    count_set = set()
    for d in dir_list:
        match = re.match(r"\s*", d)
        if match:
            count_set.add(len(match.group(0)))
    space_count_list = sorted(count_set)
    max_level = 5
    i = 0
    # Pop minimal count every time,
    # this count will used in level_i pattern
    while space_count_list:
        count = space_count_list.pop(0)
        level_patterns[i] = r"\s{" + str(count) + "}"
        i += 1
        # If len of space_count_list is more than max_level,
        # additional count all consider as max level
        if i > max_level:
            level_patterns[max_level] = r"\s{" + str(count) + ",}"
            break
    return level_patterns


def _convert_dir_text(
    dir_text,
    offset=0,
    level0=None,
    level1=None,
    level2=None,
    level3=None,
    level4=None,
    level5=None,
    other=0,
    level_by_space=False,
    fix_non_seq=False,
):
    l0, l1, pagenum, index_dict = 0, 0, -float("inf"), {}
    l2, l3, l4 = 0, 0, 0
    dir_list = text_to_list(dir_text)
    if level_by_space:
        level0, level1, level2, level3, level4, level5 = (
            generate_level_pattern_by_prefix_space(dir_list)
        )
    i = 0
    for di in dir_list:
        di = di.rstrip()
        title, num = split_page_num(di)
        if num > pagenum or not fix_non_seq:
            pagenum = num
        index_dict[i] = {"title": title, "real_num": pagenum + offset, "num": pagenum}
        level = check_level(
            title, level0, level1, level2, level3, level4, level5, other=other
        )
        if level == 5 and i != l4:
            index_dict[i]["parent"] = l4
        elif level == 4 and i != l3:
            index_dict[i]["parent"] = l3
            l4 = i
        elif level == 3 and i != l2:
            index_dict[i]["parent"] = l2
            l3 = i
        elif level == 2 and i != l1:
            index_dict[i]["parent"] = l1
            l2 = i
        elif level == 1 and i != l0:
            index_dict[i]["parent"] = l0
            l1 = i
        elif level == 0:
            l0 = i
        index_dict[i]["title"] = title.lstrip()
        i += 1
    return index_dict


def convert_dir_text(
    dir_text,
    offset=0,
    level0=None,
    level1=None,
    level2=None,
    level3=None,
    level4=None,
    level5=None,
    other=0,
    level_by_space=False,
    fix_non_seq=False,
):
    """
    convert directory text to dict.

    :param: dir_text: unicode, the directory text, usually copy from a bookstore like amazon.
    :param: offset: int, the offset of this book.
    :param: level0: unicode, the expression to find level0 title.
    :param: level1: unicode, the expression to find level1 title.
    :param: level2: unicode, the expression to find level2 title.
    :param: level3: unicode, the expression to find level3 title.
    :param: level4: unicode, the expression to find level4 title.
    :param: level5: unicode, the expression to find level5 title.
    :param: other: unicode, three level can't match title, then this is the level.
    :param: level_by_space: boolean, if True, auto generate level by space
    :return: the dict of directory, like {0:{'title':'A', 'pagenum':1}, 1:{'title':'B', pagenum:2, parent: 0} ......}

    """
    return _convert_dir_text(
        dir_text,
        offset,
        level0,
        level1,
        level2,
        level3,
        level4,
        level5,
        other=other,
        level_by_space=level_by_space,
        fix_non_seq=fix_non_seq,
    )
