call pyuic4 -i 0 ./gui/main.ui -o ./gui/main_ui.py
call pyinstaller -F run_gui.py -n "PDFdir.exe" --noconsole