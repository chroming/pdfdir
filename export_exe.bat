@echo off
call uv sync --locked --group build
call uv run python ./src/gui/ui_to_py.py
call uv run pyinstaller -F run_gui.py -i "pdf.ico" --add-data "pdf.ico;src" --add-data "src/language;src/language" -n "pdfdir" --noconfirm --clean --noconsole
