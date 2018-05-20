call pyuic4 -i 0 ./gui/main.ui -o ./gui/main_ui_4.py
call python ./tools/pyqt4topyqt5.py ./gui/main_ui_4.py -o ./gui/main_ui.py
call del .\gui\main_ui_4.py