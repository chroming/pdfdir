from src import cli
from src.cli import build_parser


def test_cli_level_defaults_match_supported_numbering():
    args = build_parser().parse_args(["book.pdf", "toc.txt"])

    assert args.l0 == r"^\d+\.\s?"
    assert args.l1 == r"^\d+\.\d+\w?\s?"
    assert args.l5 == r"^\d+\.\d+\.\d+\.\d+\.\d+\.\d+\w?\s?"


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
