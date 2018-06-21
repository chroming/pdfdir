call python ./src/gui/ui_to_py.py
call python D:/pyinstaller-develop/pyinstaller.py -F run_gui.py -i "pdf.ico" -n "PDFdir.exe"  --noconsole
