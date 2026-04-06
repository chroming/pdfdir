import subprocess
import sys


def ui_py(ui_file, py_file):
    print(f"Compiling {ui_file} to {py_file} using pyside6-uic...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "PySide6.scripts.pyside_tool", "uic", ui_file, "-o", py_file]
        )
        print("Success!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to compile UI: {e}")
        # Depending on how pyside6 is installed, `pyside6-uic` might be directly available
        try:
            subprocess.check_call(["pyside6-uic", ui_file, "-o", py_file])
            print("Success with direct pyside6-uic command!")
        except Exception as e2:
            print(f"Also failed with direct command: {e2}")


if __name__ == "__main__":
    ui_py("main_ui.ui", "main_ui.py")
