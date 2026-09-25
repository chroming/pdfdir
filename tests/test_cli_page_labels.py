"""CLI argument errors should be reported without a Python traceback."""

import subprocess
import sys
from pathlib import Path

from pypdf import PdfWriter


def test_body_start_beyond_pdf_is_argument_error(tmp_path):
    source = tmp_path / "book.pdf"
    toc = tmp_path / "contents.txt"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as output:
        writer.write(output)
    toc.write_text("Chapter 1", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, "run_cli.py", str(source), str(toc),
            "--page-labels", "roman-body", "--body-start-page", "2",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Body start page must be between 1 and 1" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "book_new.pdf").exists()
