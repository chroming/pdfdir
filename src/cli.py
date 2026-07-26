import argparse
from pathlib import Path

from src.pdfdirectory import add_directory


def build_parser():
    parser = argparse.ArgumentParser(description="Add bookmarks to a PDF.")
    parser.add_argument("pdf_path", help="Path to the PDF")
    parser.add_argument("toc_path", help="Path to the table-of-contents text file")
    parser.add_argument("--offset", type=int, default=0, help="Page number offset")
    for level in range(6):
        repeated = r"\.\d+" * level
        pattern = r"^\d+\.\s?" if level == 0 else rf"^\d+{repeated}\w?\s?"
        parser.add_argument(
            f"--l{level}",
            default=pattern,
            help=f"Regular expression for bookmark level {level}",
        )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    toc = Path(args.toc_path).read_text(encoding="utf-8")
    output_path = add_directory(
        toc,
        args.offset,
        args.pdf_path,
        args.l0,
        args.l1,
        args.l2,
        args.l3,
        args.l4,
        args.l5,
    )
    if output_path:
        print(output_path)
    return 0
