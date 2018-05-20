from PyQt5.uic import compileUi


def ui_py(ui_file, py_file):
    with open(ui_file, 'r', encoding='utf-8') as u:
        with open(py_file, 'w', encoding='utf-8') as f:
            compileUi(u, f)


if __name__ == '__main__':
    ui_py('./gui/main.ui', './gui/main_ui.py')

