from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = ".github/scripts/install-linux-qt-deps.sh"


def test_linux_workflows_use_shared_qt_runtime_setup():
    test_workflow = (PROJECT_ROOT / ".github/workflows/test.yml").read_text(
        encoding="utf-8"
    )
    release_workflow = (
        PROJECT_ROOT / ".github/workflows/release.yml"
    ).read_text(encoding="utf-8")

    assert test_workflow.count(INSTALL_SCRIPT) == 2
    assert INSTALL_SCRIPT in release_workflow


def test_linux_qt_runtime_setup_installs_required_libraries():
    install_script = (PROJECT_ROOT / INSTALL_SCRIPT).read_text(encoding="utf-8")

    for package in (
        "libdbus-1-3",
        "libegl1",
        "libgl1",
        "libxkbcommon-x11-0",
        "libxcb-cursor0",
        "libxcb-xinerama0",
    ):
        assert package in install_script


def test_frozen_smoke_uses_absolute_resources_with_external_spec_directory():
    test_workflow = (PROJECT_ROOT / ".github/workflows/test.yml").read_text(
        encoding="utf-8"
    )

    assert '--icon "${GITHUB_WORKSPACE}/pdf.ico"' in test_workflow
    assert '--add-data "${GITHUB_WORKSPACE}/pdf.ico:."' in test_workflow
    assert "dist/PDFdir --smoke-test" in test_workflow


def test_test_matrix_runs_desktop_e2e_as_an_explicit_suite():
    test_workflow = (PROJECT_ROOT / ".github/workflows/test.yml").read_text(
        encoding="utf-8"
    )

    assert "Run desktop E2E" in test_workflow
    assert "uv run pytest -q -m e2e --strict-markers" in test_workflow
    assert 'coverage run -m pytest -q -m "not e2e" --strict-markers' in test_workflow
