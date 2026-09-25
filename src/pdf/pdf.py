# -*- coding: utf-8 -*-

"""
The add bookmark class for a pdf file.

public:

- class: Pdf(path)

"""

import logging
import os
import secrets
import stat

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import Destination, Fit

from .page_labels import PageLabelPlan, apply_page_labels

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

    def __init__(self, path, keep_outline=False, page_label_plan=None):
        self.path = path
        self._source_stat = os.stat(path)
        self.reader = PdfReader(path, strict=False)
        self.pages_num = self._get_pages_num(self.reader.pages)
        self._writer = None
        self.keep_outline = keep_outline
        self.page_label_plan = page_label_plan or PageLabelPlan()

    @property
    def _new_path(self):
        name, ext = os.path.splitext(self.path)
        return name + "_new" + ext

    @property
    def writer(self):
        if not self._writer:
            writer = PdfWriter()
            # `clone_from=reader (clone_document_from_reader)` is slow when pdf is complex
            # `append_pages_from_reader` is fast but will lose annotations in pdf
            # writer.append(self.reader, import_outline=False)
            writer = self.copy_reader_to_writer(
                self.reader, writer, keep_outline=self.keep_outline
            )
            # Temporarily remove exist outline,
            # to prevent `'DictionaryObject' object has no attribute 'insert_child'` error
            # when adding bookmarks to some pdf which already have outline
            if not self.keep_outline:
                writer._root_object.pop("/Outlines", None)
            apply_page_labels(self.reader, writer, self.page_label_plan)
            self._writer = writer
        return self._writer

    @staticmethod
    def copy_reader_to_writer(reader, writer, keep_outline=False):
        # Use fallback function to make sure copy pdf always successes.
        try:
            # `clone_from=reader (clone_document_from_reader)` is slow when pdf is complex
            # `append_pages_from_reader` is fast but will lose annotations in pdf
            new_writer = writer
            new_writer.append(reader, import_outline=keep_outline)
        except Exception as e:
            logger.warning(
                "Copy pdf failed, {}, try to exclude /Annots and /B".format(e)
            )
            try:
                new_writer = type(writer)()
                new_writer.append(
                    reader,
                    import_outline=keep_outline,
                    excluded_fields=["/Annots", "/B"],
                )
            except Exception as e:
                logger.warning(
                    "Copy pdf failed again, {}, try to use append_pages_from_reader".format(
                        e
                    )
                )
                new_writer = type(writer)()
                new_writer.append_pages_from_reader(reader)
        if reader.metadata is not None:
            new_writer.add_metadata(reader.metadata)
        return new_writer

    @staticmethod
    def _get_page_ref(page):
        return getattr(page, "indirect_reference", None) or getattr(
            page, "indirect_ref", None
        )

    @classmethod
    def _get_pages_num(cls, pages):
        pages_num = {}
        for page in pages:
            try:
                if isinstance(page, PageObject):
                    page_ref = cls._get_page_ref(page)
                    if page_ref is None:
                        logger.error(
                            "Unknown page reference for page %s", page.page_number
                        )
                        continue
                    pages_num[page_ref.idnum] = page.page_number
                else:
                    logger.error(
                        "Unknown page type {} for {}".format(
                            type(page), page.page_number
                        )
                    )
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
                    index_list.append(
                        "{title}  {page_num}".format(title=title, page_num=page_num)
                    )
                except Exception as e:
                    logger.error(e)
            elif isinstance(o, list):
                index_list += self._outlines_to_bookmarks(o, current_level + 1)
            else:
                logger.error("Unknown outline type: {} in {}".format(type(o), o))
                continue
        return index_list

    def _extract_bookmarks(self, outlines, parent=None, result=None):
        if result is None:
            result = []

        last_destination = None

        for item in outlines:
            if isinstance(item, list):
                self._extract_bookmarks(
                    item, parent=last_destination, result=result
                )
            elif isinstance(item, Destination):
                page_number = self.reader.get_destination_page_number(item)
                node = {
                    "title": item.title,
                    "page_number": page_number,
                    "parent": parent,
                }
                result.append(node)
                last_destination = item
            else:
                continue
        return result

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
        # Set fit=Fit.xyz() to inherit zoom
        return self.writer.add_outline_item(
            title, pagenum, parent=parent, fit=Fit.xyz()
        )

    def save_pdf(self):
        """save the writer to a pdf file with name 'name_new.pdf'"""
        writer = self.writer
        temp_path = os.path.join(
            os.path.dirname(self._new_path) or ".",
            ".pdfdir-{}.pdf".format(secrets.token_hex(16)),
        )
        fd = os.open(
            temp_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o666,
        )
        try:
            with os.fdopen(fd, "wb") as out:
                writer.write(out)
            output = PdfReader(temp_path)
            if len(output.pages) != len(self.reader.pages):
                raise ValueError("Exported PDF has a different page count")
            if self.page_label_plan.mode == "preserve":
                if self.reader.trailer["/Root"].get("/PageLabels") is not None:
                    if output.page_labels != self.reader.page_labels:
                        raise ValueError("Exported PDF lost its existing page labels")
            elif output.page_labels[self.page_label_plan.body_start_page - 1] != "1":
                raise ValueError("Exported PDF has incorrect body page labels")
            current_stat = os.stat(self.path)
            if (
                current_stat.st_ino,
                current_stat.st_size,
                current_stat.st_mtime_ns,
            ) != (
                self._source_stat.st_ino,
                self._source_stat.st_size,
                self._source_stat.st_mtime_ns,
            ):
                raise ValueError("Source PDF changed during export; please retry")
            if os.name != "nt" and os.path.exists(self._new_path):
                # New exports already have the user's umask; replacements keep
                # the previous output's mode instead of the temporary mode.
                os.chmod(
                    temp_path,
                    stat.S_IMODE(os.stat(self._new_path).st_mode),
                )
            os.replace(temp_path, self._new_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        return self._new_path
