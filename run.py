# -*- coding: utf-8 -*-

import sys

from src.pdfdirectory import add_directory


version = 3 if sys.version_info[0] == 3 else 2


def get_input(message):
    if version == 3:
        return input(message)
    else:
        return raw_input(message).decode(sys.stdin.encoding)


if __name__ == '__main__':
    pdf_path = get_input("Please input pdf file path: ")
    offset = int(get_input("Please input offset number: "))
    dir_text = get_input("Please input directory string: ")
    add_directory(dir_text, offset, pdf_path)