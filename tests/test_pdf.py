import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError
from pypdf.generic import RectangleObject

from src.pdf.bookmark import (
    add_bookmark,
    check_bookmarks,
    get_bookmarks,
    merge_bookmarks,
)
from src.pdf.pdf import Pdf


class _FakeIndirectReference:
    def __init__(self, idnum):
        self.idnum = idnum


class _FakePage:
    def __init__(self, idnum, page_number):
        self.indirect_reference = _FakeIndirectReference(idnum)
        self.page_number = page_number


def _write_pdf(
    path,
    *,
    page_count=2,
    metadata=None,
    existing_outline=False,
    annotation=False,
    password=None,
):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    if metadata:
        writer.add_metadata(metadata)
    if existing_outline:
        parent = writer.add_outline_item("Existing", 0)
        writer.add_outline_item("Existing child", min(1, page_count - 1), parent=parent)
    if annotation:
        writer.add_uri(
            page_number=0,
            uri="https://example.com",
            rect=RectangleObject([0, 0, 10, 10]),
        )
    if password:
        writer.encrypt(password)
    with path.open("wb") as handle:
        writer.write(handle)


def _outline_titles(outline):
    titles = []
    for item in outline:
        if isinstance(item, list):
            titles.extend(_outline_titles(item))
        else:
            titles.append(item.title)
    return titles


def test_get_pages_num_supports_indirect_reference(monkeypatch):
    monkeypatch.setattr("src.pdf.pdf.PageObject", _FakePage)

    pages_num = Pdf._get_pages_num([_FakePage(7, 3)])

    assert pages_num == {7: 3}


def test_add_bookmark_preserves_pages_metadata_annotations_and_unicode(tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_pdf(
        source_path,
        metadata={"/Title": "Original title", "/Author": "PDFDir"},
        annotation=True,
    )

    output_path = add_bookmark(
        str(source_path),
        {
            0: {"title": "第一章 📖", "real_num": 1},
            1: {"title": "Section " + "x" * 200, "real_num": 2, "parent": 0},
        },
    )
    output_reader = PdfReader(output_path)

    assert len(output_reader.pages) == 2
    assert _outline_titles(output_reader.outline) == [
        "第一章 📖",
        "Section " + "x" * 200,
    ]
    assert output_reader.metadata.title == "Original title"
    assert output_reader.metadata.author == "PDFDir"
    assert len(output_reader.pages[0].get("/Annots", [])) == 1


@pytest.mark.parametrize(
    ("keep_existing", "expected_titles"),
    [
        (False, ["New"]),
        (True, ["Existing", "Existing child", "New"]),
    ],
)
def test_add_bookmark_controls_existing_outline(
    tmp_path, keep_existing, expected_titles
):
    source_path = tmp_path / f"source-{keep_existing}.pdf"
    _write_pdf(source_path, existing_outline=True)

    output_path = add_bookmark(
        str(source_path),
        {0: {"title": "New", "real_num": 1}},
        keep_exist_dir=keep_existing,
    )

    assert _outline_titles(PdfReader(output_path).outline) == expected_titles


@pytest.mark.parametrize("page_number", [0, -1, 3])
def test_bookmark_page_number_must_be_inside_pdf(tmp_path, page_number):
    source_path = tmp_path / "source.pdf"
    _write_pdf(source_path)
    bookmarks = {0: {"title": "Invalid", "real_num": page_number}}

    with pytest.raises(ValueError, match="page number|Page number|Max page number"):
        check_bookmarks(str(source_path), bookmarks)
    with pytest.raises(ValueError, match="page number|Page number|Max page number"):
        add_bookmark(str(source_path), bookmarks)


@pytest.mark.parametrize("page_number", [None, "1", 1.5, True])
def test_bookmark_page_number_must_be_an_integer(tmp_path, page_number):
    source_path = tmp_path / "source.pdf"
    _write_pdf(source_path)

    with pytest.raises(ValueError, match="must be integers"):
        add_bookmark(
            str(source_path),
            {0: {"title": "Invalid", "real_num": page_number}},
        )


@pytest.mark.parametrize(
    ("bookmarks", "message"),
    [
        ({1: {"title": "Wrong start", "real_num": 1}}, "consecutive"),
        (
            {
                0: {"title": "Parent", "real_num": 1},
                1: {"title": "Child", "real_num": 1, "parent": 2},
            },
            "Invalid parent",
        ),
        (
            {
                0: {"title": "Parent", "real_num": 1, "parent": 0},
            },
            "Invalid parent",
        ),
    ],
)
def test_bookmark_tree_indexes_must_be_valid(tmp_path, bookmarks, message):
    source_path = tmp_path / "source.pdf"
    _write_pdf(source_path)

    with pytest.raises(ValueError, match=message):
        add_bookmark(str(source_path), bookmarks)


def test_empty_bookmark_list_still_produces_valid_copy(tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_pdf(source_path)

    output_path = add_bookmark(str(source_path), {})
    output_reader = PdfReader(output_path)

    assert len(output_reader.pages) == 2
    assert output_reader.outline == []


def test_empty_bookmark_validation_does_not_open_pdf():
    assert check_bookmarks("missing.pdf", {}) is None


def test_save_pdf_rejects_existing_output_before_writing(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    _write_pdf(source_path)
    pdf = Pdf(str(source_path))
    output_path = tmp_path / "source_new.pdf"
    output_path.write_bytes(b"previous output")

    def fail_write(_handle):
        raise RuntimeError("disk full")

    monkeypatch.setattr(pdf.writer, "write", fail_write)

    with pytest.raises(OSError, match="already exists"):
        pdf.save_pdf()

    assert output_path.read_bytes() == b"previous output"
    assert list(tmp_path.glob(".source_new.pdf.*.tmp")) == []


def test_encrypted_pdf_requires_a_password(tmp_path):
    source_path = tmp_path / "encrypted.pdf"
    _write_pdf(source_path, password="secret")

    with pytest.raises(FileNotDecryptedError):
        add_bookmark(
            str(source_path),
            {0: {"title": "Chapter", "real_num": 1}},
        )


def test_get_bookmarks_handles_missing_and_invalid_files(tmp_path):
    invalid_path = tmp_path / "invalid.pdf"
    invalid_path.write_bytes(b"not a pdf")

    assert get_bookmarks("") == []
    assert get_bookmarks(str(invalid_path)) == []


def test_get_bookmarks_returns_nested_outline_as_indented_text(tmp_path):
    source_path = tmp_path / "outline.pdf"
    _write_pdf(source_path, existing_outline=True)

    assert get_bookmarks(str(source_path)) == [
        "Existing  1",
        " Existing child  2",
    ]


def test_pdf_copy_does_not_silently_drop_document_data_on_clone_failure():
    class FakeWriter:
        def clone_document_from_reader(self, reader):
            raise RuntimeError("Cannot clone complete document")

    with pytest.raises(RuntimeError, match="Cannot clone complete document"):
        Pdf.copy_reader_to_writer(object(), FakeWriter())


def test_merge_bookmarks_remaps_new_parent_indexes():
    existing = [{"title": "Existing", "pagenum": 1}]
    new = [
        {"title": "New parent", "pagenum": 2},
        {"title": "New child", "pagenum": 3, "parent": 0},
    ]

    assert merge_bookmarks(existing, new) == [
        {"title": "Existing", "pagenum": 1},
        {"title": "New parent", "pagenum": 2},
        {"title": "New child", "pagenum": 3, "parent": 1},
    ]
