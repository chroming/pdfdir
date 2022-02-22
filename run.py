# -*- coding: utf-8 -*-

import sys
from six.moves import input

from src.pdfdirectory import add_directory


def get_input(message):
    return input(message)


def get_multiline_input(message):
    print(message)
    print("press Ctrl-D or Ctrl-Z ( windows ) to finish.")
    return sys.stdin.readlines()


if __name__ == '__main__':
    pdf_path = get_input("Please input pdf file path: ")
    offset = int(get_input("Please input offset number: "))
    dir_text = get_multiline_input("Please input directory string: ")
    add_directory(dir_text, offset, pdf_path)