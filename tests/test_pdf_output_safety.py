import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Text

import src.pdf.pdf as pdf_module
from src.pdf.bookmark import add_bookmark, check_bookmarks
from src.pdf.cancellation import OperationCancelled
from src.pdf.pdf import Pdf
from src.pdf.pdf import OutputTargetChangedError


def _write_blank_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def test_copy_failure_does_not_fall_back_to_lossy_page_copy(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    pdf = Pdf(str(source_path))
    copy_attempts = []

    def fail_lossless_copy(_writer, _reader, **_kwargs):
        copy_attempts.append("lossless")
        raise OSError("lossless copy failed")

    def record_lossy_fallback(_writer, _reader):
        copy_attempts.append("lossy")

    monkeypatch.setattr(
        PdfWriter,
        "clone_document_from_reader",
        fail_lossless_copy,
    )
    monkeypatch.setattr(
        PdfWriter,
        "append_pages_from_reader",
        record_lossy_fallback,
    )

    with pytest.raises(OSError, match="lossless copy failed"):
        pdf.save_pdf()

    assert copy_attempts == ["lossless"]
    assert not output_path.exists()
    assert not list(tmp_path.glob(".source_new.*.tmp"))


def test_existing_output_is_never_replaced(tmp_path):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    previous_output = b"previous generated PDF"
    output_path.write_bytes(previous_output)

    with pytest.raises(OSError, match="already exists"):
        Pdf(str(source_path)).save_pdf()

    assert output_path.read_bytes() == previous_output
    assert not list(tmp_path.glob(".source_new.*.tmp"))


def test_concurrent_output_creation_is_not_overwritten(tmp_path, monkeypatch):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    pdf = Pdf(str(source_path))
    original_write = PdfWriter.write
    concurrent_output = b"created by another process"

    def write_then_create_output(writer, stream):
        result = original_write(writer, stream)
        output_path.write_bytes(concurrent_output)
        return result

    monkeypatch.setattr(PdfWriter, "write", write_then_create_output)

    with pytest.raises(OSError, match="changed during generation"):
        pdf.save_pdf()

    assert output_path.read_bytes() == concurrent_output
    assert not list(tmp_path.glob(".source_new.*.tmp"))


def test_output_created_at_atomic_commit_is_not_overwritten(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    concurrent_output = b"created at the final commit boundary"
    pdf = Pdf(str(source_path))
    original_link = pdf_module.os.link

    def create_target_before_link(source, destination):
        output_path.write_bytes(concurrent_output)
        return original_link(source, destination)

    monkeypatch.setattr(pdf_module.os, "link", create_target_before_link)

    with pytest.raises(OSError, match="changed during generation"):
        pdf.save_pdf()

    assert output_path.read_bytes() == concurrent_output
    assert not list(tmp_path.glob(".source_new.*.tmp"))


def test_generated_pdf_must_preserve_new_bookmark_structure(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as handle:
        writer.write(handle)
    pdf = Pdf(str(source_path))
    parent = pdf.add_bookmark("Parent", 0)
    pdf.add_bookmark("Child", 1, parent=parent)
    original_write = PdfWriter.write

    def write_flat_bookmarks(_writer, stream):
        invalid_writer = PdfWriter()
        invalid_writer.add_blank_page(width=72, height=72)
        invalid_writer.add_blank_page(width=72, height=72)
        invalid_writer.add_outline_item("Parent", 0)
        invalid_writer.add_outline_item("Child", 1)
        return original_write(invalid_writer, stream)

    monkeypatch.setattr(PdfWriter, "write", write_flat_bookmarks)

    with pytest.raises(OSError, match="bookmark structure"):
        pdf.save_pdf()

    assert not output_path.exists()
    assert not list(tmp_path.glob(".source_new.*.tmp"))


def test_generated_pdf_must_preserve_new_bookmark_page_targets(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as handle:
        writer.write(handle)

    pdf = Pdf(str(source_path))
    parent = pdf.add_bookmark("Parent", 0)
    pdf.add_bookmark("Child", 1, parent=parent)
    original_write = PdfWriter.write

    def write_wrong_page_target(_writer, stream):
        invalid_writer = PdfWriter()
        invalid_writer.add_blank_page(width=72, height=72)
        invalid_writer.add_blank_page(width=72, height=72)
        invalid_parent = invalid_writer.add_outline_item("Parent", 0)
        invalid_writer.add_outline_item(
            "Child",
            0,
            parent=invalid_parent,
        )
        return original_write(invalid_writer, stream)

    monkeypatch.setattr(PdfWriter, "write", write_wrong_page_target)

    with pytest.raises(OSError, match="page targets"):
        pdf.save_pdf()

    assert not output_path.exists()
    assert not list(tmp_path.glob(".source_new.*.tmp"))


def test_validation_accepts_existing_and_new_nested_bookmarks(tmp_path):
    source_path = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    existing_parent = writer.add_outline_item("Existing parent", 0)
    writer.add_outline_item(
        "Existing child",
        1,
        parent=existing_parent,
    )
    with source_path.open("wb") as handle:
        writer.write(handle)

    output_path = add_bookmark(
        str(source_path),
        {
            0: {"title": "New parent", "real_num": 1},
            1: {"title": "New child", "real_num": 2, "parent": 0},
        },
        keep_exist_dir=True,
    )

    output_reader = PdfReader(output_path)
    assert output_reader.outline[0].title == "Existing parent"
    assert output_reader.outline[1][0].title == "Existing child"
    assert output_reader.outline[2].title == "New parent"
    assert output_reader.outline[3][0].title == "New child"
    assert output_reader.get_destination_page_number(
        output_reader.outline[3][0]
    ) == 1


def test_successful_copy_preserves_source_annotations(tmp_path):
    source_path = tmp_path / "annotated.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_annotation(
        page_number=0,
        annotation=Text(
            rect=(10, 10, 30, 30),
            text="Important note",
        ),
    )
    with source_path.open("wb") as handle:
        writer.write(handle)

    output_path = add_bookmark(
        str(source_path),
        {0: {"title": "Chapter", "real_num": 1}},
    )

    output_reader = PdfReader(output_path)
    annotations = output_reader.pages[0]["/Annots"]
    assert len(annotations) == 1
    assert annotations[0].get_object()["/Contents"] == "Important note"


def test_successful_copy_preserves_embedded_files_and_metadata(tmp_path):
    source_path = tmp_path / "with-attachment.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_attachment("note.txt", b"source attachment payload")
    writer.add_metadata({"/Subject": "Document-level data must survive"})
    with source_path.open("wb") as handle:
        writer.write(handle)

    output_path = add_bookmark(
        str(source_path),
        {0: {"title": "Chapter", "real_num": 1}},
    )

    output_reader = PdfReader(output_path)
    assert list(output_reader.attachments) == ["note.txt"]
    assert output_reader.attachments["note.txt"] == [
        b"source attachment payload"
    ]
    assert (
        output_reader.metadata.subject
        == "Document-level data must survive"
    )
    assert output_reader.outline[0].title == "Chapter"


def test_candidate_validation_rejects_lost_embedded_files(
    tmp_path, monkeypatch
):
    source_path = tmp_path / "with-attachment.pdf"
    output_path = tmp_path / "with-attachment_new.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_attachment("note.txt", b"source attachment payload")
    with source_path.open("wb") as handle:
        writer.write(handle)
    pdf = Pdf(str(source_path))
    pdf.add_bookmark("Chapter", 0)
    original_write = PdfWriter.write

    def write_without_attachment(_writer, stream):
        invalid_writer = PdfWriter()
        invalid_writer.add_blank_page(width=72, height=72)
        invalid_writer.add_outline_item("Chapter", 0)
        return original_write(invalid_writer, stream)

    monkeypatch.setattr(PdfWriter, "write", write_without_attachment)

    with pytest.raises(OSError, match="embedded files"):
        pdf.save_pdf()

    assert not output_path.exists()
    assert not list(tmp_path.glob(".with-attachment_new.*.tmp"))


def test_bookmark_pages_must_be_positive(tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    with pytest.raises(ValueError, match="at least 1"):
        check_bookmarks(
            str(source_path),
            {0: {"title": "Invalid", "real_num": 0}},
        )


def test_public_writer_rejects_page_outside_source_pdf(tmp_path):
    source_path = tmp_path / "source.pdf"
    _write_blank_pdf(source_path)

    with pytest.raises(ValueError, match="exceeds"):
        add_bookmark(
            str(source_path),
            {0: {"title": "Invalid", "real_num": 999}},
        )


def test_cancel_before_atomic_commit_creates_no_output(tmp_path):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    pdf = Pdf(str(source_path))
    checks = []

    def cancel_after_write():
        checks.append(True)
        return len(checks) >= 2

    with pytest.raises(OperationCancelled):
        pdf.save_pdf(cancel_check=cancel_after_write)

    assert not output_path.exists()


def test_output_created_before_generation_is_not_replaced(tmp_path):
    source_path = tmp_path / "source.pdf"
    output_path = tmp_path / "source_new.pdf"
    _write_blank_pdf(source_path)
    expected_fingerprint = Pdf.output_fingerprint(output_path)
    output_path.write_bytes(b"created by another process")

    with pytest.raises(
        OutputTargetChangedError,
        match="already exists",
    ):
        Pdf(str(source_path)).save_pdf(
            expected_output_fingerprint=expected_fingerprint,
            enforce_output_fingerprint=True,
        )

    assert output_path.read_bytes() == b"created by another process"
