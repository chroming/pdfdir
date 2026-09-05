# -*- coding: utf-8 -*-

"""
The add bookmark class for a pdf file.

public:

- class: Pdf(path)

"""

import hashlib
import logging
import os
import tempfile

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import Destination, Fit

from src.pdf.cancellation import raise_if_cancelled

logger = logging.getLogger(__name__)


class OutputTargetChangedError(OSError):
    """The output path changed after PDF generation started."""


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

    def __init__(self, path, keep_outline=False, output_path=None):
        self.path = path
        self.reader = PdfReader(open(path, "rb"), strict=False)
        self.pages_num = self._get_pages_num(self.reader.pages)
        self._writer = None
        self._added_bookmarks = []
        self._added_bookmark_indices = {}
        self.keep_outline = keep_outline
        self.output_path = output_path

    @property
    def _new_path(self):
        if self.output_path:
            return self.output_path
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
            self._writer = writer
        return self._writer

    @staticmethod
    def copy_reader_to_writer(reader, writer, keep_outline=False):
        # Clone the complete document catalog. Page-only/append copying can
        # silently discard document-level data such as embedded files, forms,
        # named destinations, and other entries under /Root.
        writer.clone_document_from_reader(reader)
        return writer

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
                    title = " " * current_level + o.title.strip()
                    page_num = self.reader.get_destination_page_number(o) + 1
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
        parent_index = None
        if parent is not None:
            parent_index = self._added_bookmark_indices.get(id(parent))
            if parent_index is None:
                raise ValueError("Bookmark parent was not added by this PDF")
        bookmark = self.writer.add_outline_item(
            title, pagenum, parent=parent, fit=Fit.xyz()
        )
        bookmark_index = len(self._added_bookmarks)
        self._added_bookmarks.append(
            {
                "title": str(title),
                "page_number": pagenum,
                "parent": parent_index,
            }
        )
        self._added_bookmark_indices[id(bookmark)] = bookmark_index
        return bookmark

    @staticmethod
    def _outline_specs(reader):
        specs = []

        def walk(entries, parent_index=None):
            last_destination_index = None
            for entry in entries:
                if isinstance(entry, list):
                    if last_destination_index is None:
                        raise IOError(
                            "Generated PDF has an invalid bookmark structure"
                        )
                    walk(entry, last_destination_index)
                elif isinstance(entry, Destination):
                    destination_index = len(specs)
                    specs.append(
                        (
                            str(entry.title),
                            reader.get_destination_page_number(entry),
                            parent_index,
                        )
                    )
                    last_destination_index = destination_index
                else:
                    raise IOError(
                        "Generated PDF has an unsupported bookmark entry"
                    )

        walk(reader.outline)
        return specs

    def _ordered_added_bookmarks(self):
        children = {None: []}
        for index, bookmark in enumerate(self._added_bookmarks):
            parent_index = bookmark["parent"]
            children.setdefault(parent_index, []).append(index)
            children.setdefault(index, [])

        ordered = []

        def append_subtree(index, parent_index=None):
            bookmark = self._added_bookmarks[index]
            ordered_index = len(ordered)
            ordered.append(
                (
                    bookmark["title"],
                    bookmark["page_number"],
                    parent_index,
                )
            )
            for child_index in children[index]:
                append_subtree(child_index, ordered_index)

        for root_index in children[None]:
            append_subtree(root_index)
        if len(ordered) != len(self._added_bookmarks):
            raise IOError("Requested bookmarks have an invalid structure")
        return ordered

    def _expected_bookmark_specs(self):
        expected = self._outline_specs(self.reader) if self.keep_outline else []
        added_offset = len(expected)
        for title, page_number, parent_index in self._ordered_added_bookmarks():
            expected.append(
                (
                    title,
                    page_number,
                    (
                        parent_index + added_offset
                        if parent_index is not None
                        else None
                    ),
                )
            )
        return expected

    def _validate_candidate(self, candidate):
        if len(candidate.pages) != len(self.reader.pages):
            raise IOError("Generated PDF page count does not match source")

        if self._attachment_specs(candidate) != self._attachment_specs(
            self.reader
        ):
            raise IOError(
                "Generated PDF embedded files do not match source"
            )

        expected_specs = self._expected_bookmark_specs()
        candidate_specs = self._outline_specs(candidate)
        expected_structure = [
            (title, parent_index)
            for title, _page_number, parent_index in expected_specs
        ]
        candidate_structure = [
            (title, parent_index)
            for title, _page_number, parent_index in candidate_specs
        ]
        if candidate_structure != expected_structure:
            raise IOError(
                "Generated PDF bookmark structure does not match requested bookmarks"
            )
        expected_page_targets = [
            page_number
            for _title, page_number, _parent_index in expected_specs
        ]
        candidate_page_targets = [
            page_number
            for _title, page_number, _parent_index in candidate_specs
        ]
        if candidate_page_targets != expected_page_targets:
            raise IOError(
                "Generated PDF bookmark page targets do not match requested bookmarks"
            )

    @staticmethod
    def _attachment_specs(reader):
        """Return stable names, sizes, and hashes for every embedded file."""
        specs = []
        for name in reader.attachments:
            payloads = reader.attachments[name]
            if isinstance(payloads, (bytes, bytearray, memoryview)):
                payloads = [payloads]
            fingerprints = sorted(
                (
                    len(payload),
                    hashlib.sha256(bytes(payload)).digest(),
                )
                for payload in payloads
            )
            specs.append((str(name), tuple(fingerprints)))
        return tuple(sorted(specs))

    @staticmethod
    def output_fingerprint(path):
        try:
            with open(path, "rb") as target:
                before = os.fstat(target.fileno())
                digest = hashlib.sha256()
                while True:
                    chunk = target.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                after = os.fstat(target.fileno())
            current = os.stat(path)
        except FileNotFoundError:
            return None

        stat_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
        )
        before_state = tuple(getattr(before, field) for field in stat_fields)
        after_state = tuple(getattr(after, field) for field in stat_fields)
        current_state = tuple(getattr(current, field) for field in stat_fields)
        if before_state != after_state or after_state != current_state:
            raise OutputTargetChangedError(
                "Output target changed during generation; refusing to replace it"
            )
        return after_state + (digest.digest(),)

    # Backward-compatible private alias for callers/tests that used the helper
    # during the initial safety hardening.
    _output_fingerprint = output_fingerprint

    def save_pdf(
        self,
        cancel_check=None,
        expected_output_fingerprint=None,
        enforce_output_fingerprint=False,
    ):
        """save the writer to a pdf file with name 'name_new.pdf'"""
        raise_if_cancelled(cancel_check)
        output_path = os.path.abspath(self._new_path)
        output_dir = os.path.dirname(output_path)
        output_name = os.path.basename(output_path)
        output_fingerprint = self.output_fingerprint(output_path)
        if output_fingerprint is not None:
            raise OutputTargetChangedError(
                "Output target already exists; refusing to replace it"
            )
        if enforce_output_fingerprint and expected_output_fingerprint is not None:
            raise OutputTargetChangedError(
                "Replacing an existing output target is not supported"
            )
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=".{}.".format(output_name),
            suffix=".tmp",
            dir=output_dir,
        )
        try:
            with os.fdopen(file_descriptor, "wb") as out:
                self.writer.write(out)
                out.flush()
                os.fsync(out.fileno())

            with open(temporary_path, "rb") as candidate_file:
                candidate = PdfReader(candidate_file, strict=False)
                self._validate_candidate(candidate)

            raise_if_cancelled(cancel_check)
            try:
                # Hard-linking is an atomic create-if-absent operation on the
                # same filesystem. Unlike os.replace(), it cannot overwrite a
                # file created in the gap after our final check.
                os.link(temporary_path, output_path)
            except FileExistsError as exc:
                raise OutputTargetChangedError(
                    "Output target changed during generation; refusing to replace it"
                ) from exc
            os.remove(temporary_path)
        except Exception:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise
        return self._new_path
