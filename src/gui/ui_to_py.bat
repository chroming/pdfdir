@echo off
set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%ui_to_py.py" "%SCRIPT_DIR%main_ui.ui" "%SCRIPT_DIR%main_ui.py"
