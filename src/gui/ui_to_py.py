import shutil
import subprocess
import sys
from pathlib import Path


def ui_py(ui_file, py_file):
    compiler = shutil.which("pyside6-uic")
    if compiler is None:
        raise RuntimeError(
            "pyside6-uic was not found. Install the project dependencies first."
        )
    subprocess.run(
        [compiler, str(ui_file), "-o", str(py_file)],
        check=True,
    )
    output_path = Path(py_file)
    if output_path.exists():
        generated = output_path.read_text(encoding="utf-8")
        output_path.write_text(generated.rstrip() + "\n", encoding="utf-8")


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    script_dir = Path(__file__).resolve().parent
    if not args:
        ui_file = script_dir / "main_ui.ui"
        py_file = script_dir / "main_ui.py"
    elif len(args) == 2:
        ui_file, py_file = map(Path, args)
    else:
        raise SystemExit("usage: ui_to_py.py [INPUT.ui OUTPUT.py]")
    ui_py(ui_file, py_file)


if __name__ == "__main__":
    main()
