import os
import subprocess
import sys
from pathlib import Path

from src import config
from src.version import __version__


def test_config_version_matches_release_version():
    assert config.CONFIG.VERSION == __version__


def test_resource_path_uses_pyinstaller_bundle_directory(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/pdfdir-bundle", raising=False)

    assert config.resource_path("pdf.ico") == os.path.join(
        "/tmp/pdfdir-bundle", "pdf.ico"
    )


def test_config_ignores_unrelated_config_ini_in_launch_directory(tmp_path):
    (tmp_path / "config.ini").write_text(
        "[UNRELATED]\nvalue = true\n",
        encoding="utf-8",
    )
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project_root)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.config import CONFIG; print(CONFIG.DEFAULT_FOLDER)",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() != str(tmp_path)
