call python ./src/gui/ui_to_py.py
call pyinstaller -F run_gui.py -i "pdf.ico" -n "PDFdir.exe"  --noconsole
