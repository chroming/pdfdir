# -*- coding: utf-8 -*-

import os

from src.pdfdirectory import add_directory


if __name__ == '__main__':
    pdf_path = raw_input("Please input pdf file path: ").decode('utf-8')
    if not os.path.isfile(pdf_path):
        raise TypeError, "pdf path if not file !"
    offset = int(raw_input("Please input offset number: "))
    dir_text = raw_input("Please input directory string: ").decode('utf-8')
    add_directory(dir_text, offset, pdf_path)