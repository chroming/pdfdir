import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from src import cli
from src.cli import build_parser

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "run_cli.py"), *map(str, args)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_level_defaults_match_supported_numbering():
    args = build_parser().parse_args(["book.pdf", "toc.txt"])

    assert args.l0 == r"^\d+\.\s?"
    assert args.l1 == r"^\d+\.\d+\w?\s?"
    assert args.l5 == r"^\d+\.\d+\.\d+\.\d+\.\d+\.\d+\w?\s?"


def test_cli_rejects_invalid_regular_expression():
    with pytest.raises(
        cli.argparse.ArgumentTypeError,
        match="Invalid regular expression",
    ):
        cli.regex_pattern("[")


def test_cli_prints_output_without_returning_error_code(monkeypatch, tmp_path, capsys):
    toc_path = tmp_path / "toc.txt"
    toc_path.write_text("Chapter One 1", encoding="utf-8")
    calls = []

    def fake_add_directory(*args):
        calls.append(args)
        return "book_new.pdf"

    monkeypatch.setattr(cli, "add_directory", fake_add_directory)

    result = cli.main(["book.pdf", str(toc_path)])

    assert result == 0
    assert capsys.readouterr().out == "book_new.pdf\n"
    assert calls[0][:3] == ("Chapter One 1", 0, "book.pdf")


def test_cli_succeeds_when_no_output_is_created(monkeypatch, tmp_path, capsys):
    toc_path = tmp_path / "toc.txt"
    toc_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "add_directory", lambda *_args: None)

    assert cli.main(["book.pdf", str(toc_path)]) == 0
    assert capsys.readouterr().out == ""


def test_cli_help_succeeds():
    result = _run_cli("--help")

    assert result.returncode == 0
    assert "Add bookmarks to a PDF" in result.stdout


def test_cli_process_writes_nested_bookmarks(tmp_path):
    source_path = tmp_path / "source.pdf"
    toc_path = tmp_path / "toc.txt"
    _write_pdf(source_path)
    toc_path.write_text("1. Chapter 1\n1.1 Section 2\n", encoding="utf-8")

    result = _run_cli(source_path, toc_path)
    output_path = tmp_path / "source_new.pdf"

    assert result.returncode == 0
    assert result.stdout.strip() == str(output_path)
    assert output_path.exists()
    outline = PdfReader(output_path).outline
    assert outline[0].title == "1. Chapter"
    assert outline[1][0].title == "1.1 Section"


@pytest.mark.parametrize(
    "arguments",
    [
        ("missing.pdf", "missing.txt"),
        ("--l0", "[", "missing.pdf", "missing.txt"),
    ],
)
def test_cli_process_returns_nonzero_for_invalid_input(arguments):
    result = _run_cli(*arguments)

    assert result.returncode != 0


def test_cli_rejects_non_utf8_toc(tmp_path):
    source_path = tmp_path / "source.pdf"
    toc_path = tmp_path / "toc.txt"
    _write_pdf(source_path)
    toc_path.write_bytes(b"\xff\xfe")

    result = _run_cli(source_path, toc_path)

    assert result.returncode != 0
    assert not (tmp_path / "source_new.pdf").exists()
