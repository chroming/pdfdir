# -*- coding: utf-8 -*-

"""
The add bookmark api for a pdf file.

public:

- class: Pdf(path)

"""
import logging
import os

from pypdf import PdfWriter, PdfReader, PageObject
from pypdf.generic import Destination

logger = logging.getLogger(__name__)



class Pdf(object):
    """
    Add bookmarks to a pdf file.

    Usage:

    >>> from src.pdf import Pdf

    read a exist pdf file:
    >>> p = Pdf('D:\\1.pdf')

    add a bookmark:
    >>> b0 = p.add_bookmark('First bookmark', 1)

    add a child bookmark to b0:
    >>> p.add_bookmark('Child bookmark', 2, parent=b0)

    save pdf:
    >>> p.save_pdf()

    the new pdf file will save to save directory with '1_new.pdf'

    """
    def __init__(self, path):
        self.path = path
        self.reader = PdfReader(open(path, "rb"), strict=False)
        self.pages_num = self._get_pages_num(self.reader.pages)
        self._writer = None

    @property
    def _new_path(self):
        name, ext = os.path.splitext(self.path)
        return name + '_new' + ext

    @property
    def writer(self):
        if not self._writer:
            writer = PdfWriter()
            # `clone_from=reader (clone_document_from_reader)` is slow when pdf is complex
            # `append_pages_from_reader` is fast but will lose annotations in pdf
            # writer.append(self.reader, import_outline=False)
            self.copy_reader_to_writer(self.reader, writer)
            # Temporarily remove exist outline,
            # to prevent `'DictionaryObject' object has no attribute 'insert_child'` error
            # when adding bookmarks to some pdf which already have outline
            writer._root_object.pop("/Outlines", None)
            self._writer = writer
        return self._writer

    @staticmethod
    def copy_reader_to_writer(reader, writer):
        # Use fallback function to make sure copy pdf always successes.
        try:
            # `clone_from=reader (clone_document_from_reader)` is slow when pdf is complex
            # `append_pages_from_reader` is fast but will lose annotations in pdf
            writer.append(reader, import_outline=False)
        except Exception as e:
            logger.warning("Copy pdf failed, {}, try to exclude /Annots and /B".format(e))
            try:
                writer.append(reader, import_outline=False, excluded_fields=["/Annots", "/B"])
            except Exception as e:
                logger.warning("Copy pdf failed again, {}, try to use append_pages_from_reader".format(e))
                writer.append_pages_from_reader(reader)

    @staticmethod
    def _get_pages_num(pages):
        pages_num = {}
        for page in pages:
            try:
                if isinstance(page, PageObject):
                    pages_num[page.indirect_ref.idnum] = page.page_number
                else:
                    logger.error("Unknown page type {} for {}".format(type(page), page.page_number))
            except Exception as e:
                logger.error(e)
        return pages_num

    def _outlines_to_bookmarks(self, outlines, current_level=0):
        index_list = []
        for o in outlines:
            if isinstance(o, Destination):
                try:
                    idnum = o.page if isinstance(o.page, int) else o.page.idnum
                    title = " " * current_level + o.title.strip()
                    page_num = self.pages_num[idnum] + 1
                    index_list.append("{title}  {page_num}".format(title=title, page_num=page_num))
                except Exception as e:
                    logger.error(e)
            elif isinstance(o, list):
                index_list += self._outlines_to_bookmarks(o, current_level + 1)
            else:
                logger.error("Unknown outline type: {} in {}".format(type(o), o))
                continue
        return index_list

    def exist_bookmarks(self):
        return self._outlines_to_bookmarks(self.reader.outline)

    def add_bookmark(self, title, pagenum, parent=None):
        """
        add a bookmark to pdf file with title and page num.
        if it's a child bookmark, add a parent argument.

        :Args

        title: str, the bookmark title.
        pagenum: int, the page num this bookmark refer to.
        parent: IndirectObject(the addBookmark() return object), the parent of this bookmark, the default is None.

        """
        return self.writer.add_outline_item(title, pagenum, parent=parent)

    def save_pdf(self):
        """save the writer to a pdf file with name 'name_new.pdf' """
        if os.path.exists(self._new_path):
            os.remove(self._new_path)
        with open(self._new_path, 'wb') as out:
            self.writer.write(out)
        return self._new_path
