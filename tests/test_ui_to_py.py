from pathlib import Path

import pytest

from src.gui import ui_to_py


def test_ui_compiler_uses_pyside_executable(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ui_to_py.shutil, "which", lambda _name: "/bin/pyside6-uic")

    def fake_run(command, check):
        calls.append((command, check))
        Path(command[-1]).write_text("generated\n\n", encoding="utf-8")

    monkeypatch.setattr(ui_to_py.subprocess, "run", fake_run)

    source = tmp_path / "input.ui"
    output = tmp_path / "output.py"
    ui_to_py.ui_py(source, output)

    assert calls == [(["/bin/pyside6-uic", str(source), "-o", str(output)], True)]
    assert output.read_text(encoding="utf-8") == "generated\n"


def test_ui_compiler_reports_missing_executable(monkeypatch):
    monkeypatch.setattr(ui_to_py.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="pyside6-uic"):
        ui_to_py.ui_py(Path("input.ui"), Path("output.py"))


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ([], ("main_ui.ui", "main_ui.py")),
        (["custom.ui", "custom.py"], ("custom.ui", "custom.py")),
    ],
)
def test_ui_compiler_main_resolves_arguments(monkeypatch, arguments, expected):
    calls = []
    monkeypatch.setattr(
        ui_to_py,
        "ui_py",
        lambda source, output: calls.append((Path(source).name, Path(output).name)),
    )

    ui_to_py.main(arguments)

    assert calls == [expected]


def test_ui_compiler_main_rejects_partial_arguments():
    with pytest.raises(SystemExit, match="usage"):
        ui_to_py.main(["only-input.ui"])
