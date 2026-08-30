"""Exercise an installed wheel without importing the source checkout."""

import os
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def main():
    root = Path(sys.argv[1]).resolve()
    cli = Path(sys.argv[2]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source_path = root / "source.pdf"
    toc_path = root / "toc.txt"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as handle:
        writer.write(handle)
    toc_path.write_text("1. Installed package 1\n", encoding="utf-8")

    os.chdir(root)
    result = subprocess.run(
        [str(cli), str(source_path), str(toc_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    output_path = root / "source_new.pdf"
    assert result.stdout.strip() == str(output_path)
    assert PdfReader(output_path).outline[0].title == "1. Installed package"

    original_hook = sys.excepthook
    from src.config import CONFIG
    from src.gui.main import Main

    assert Main
    assert CONFIG.VERSION
    assert sys.excepthook is original_hook


if __name__ == "__main__":
    main()
