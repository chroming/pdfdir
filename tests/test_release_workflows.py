import json
import os
from pathlib import Path
import re
import subprocess
import sys

from packaging.version import Version
import pytest

from src.version import __version__


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"
RELEASE_WORKFLOW = WORKFLOW_ROOT / "release.yml"
CI_WORKFLOW = WORKFLOW_ROOT / "test.yml"
RELEASE_GUARD = (
    REPOSITORY_ROOT / ".github" / "scripts" / "guard_existing_release.py"
)
LEGACY_RELEASE_WORKFLOWS = (
    "linux-release.yml",
    "mac-py310-release.yml",
    "mac-release.yml",
    "mac-silicon-release.yml",
    "windows-release.yml",
)


def _release_workflow_text():
    return RELEASE_WORKFLOW.read_text(encoding="utf-8")


def _ci_workflow_text():
    return CI_WORKFLOW.read_text(encoding="utf-8")


def _mac_bundle_version_python():
    workflow = _release_workflow_text()
    match = re.search(
        r"""APP_VERSION="\$\(python -c '([^']+)'\)" """.strip(),
        workflow,
    )
    assert match, "macOS bundle-version normalizer is missing"
    return match.group(1)


def test_source_version_is_a_real_parseable_version():
    assert "${{" not in __version__
    assert Version(__version__) == Version("0.3.0b0")


def test_release_has_one_tag_only_workflow():
    assert RELEASE_WORKFLOW.is_file()
    for legacy_name in LEGACY_RELEASE_WORKFLOWS:
        assert not (WORKFLOW_ROOT / legacy_name).exists(), legacy_name

    workflow = _release_workflow_text()
    assert '      - "v*"' in workflow
    assert "release:\n" not in workflow
    assert "fetch-depth: 0" in workflow


def test_release_workflow_uses_supported_python_and_current_actions():
    workflow = _release_workflow_text()
    for contract in (
        'python-version: "3.12"',
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "astral-sh/setup-uv@v8",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "softprops/action-gh-release@v3",
    ):
        assert contract in workflow, contract

    assert workflow.count("softprops/action-gh-release@v3") == 1


def test_ci_workflow_uses_current_actions_and_semantic_frozen_smoke():
    workflow = _ci_workflow_text()
    for contract in (
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "astral-sh/setup-uv@v8",
        "dist/PDFdir --smoke-test",
    ):
        assert contract in workflow, contract
    assert "sleep 5" not in workflow


def test_release_builds_install_committed_dependencies():
    workflow = _release_workflow_text()
    assert "requirements_build_addon.txt" not in workflow
    assert workflow.count("requirements_dev.txt") == 3


def test_release_uses_the_exact_tag_as_the_application_version():
    workflow = _release_workflow_text()
    assert "RELEASE_VERSION: ${{ github.ref_name }}" in workflow
    assert 'Version(os.environ["RELEASE_VERSION"])' in workflow
    assert 'Path("src/version.py").write_text' in workflow
    assert "git describe" not in workflow


def test_release_builds_all_supported_platforms():
    workflow = _release_workflow_text()
    for contract in (
        "runs-on: ubuntu-22.04",
        "runs-on: windows-2025",
        "runner: macos-15-intel",
        "runner: macos-15",
        "pdfdir_mac_intel.zip",
        "pdfdir_mac_silicon.zip",
    ):
        assert contract in workflow, contract


def test_release_exercises_each_frozen_gui_to_pdf_path():
    workflow = _release_workflow_text()
    for command in (
        "./pdfdir --smoke-test",
        r".\pdfdir.exe --smoke-test",
        r".\pdfdir_folder\pdfdir_folder.exe --smoke-test",
        "./pdfdir.app/Contents/MacOS/pdfdir --smoke-test",
    ):
        assert command in workflow, command
    assert workflow.count("Smoke test frozen app") == 3


def test_macos_release_requires_signing_notarization_and_gatekeeper():
    workflow = _release_workflow_text()
    for contract in (
        "BUILD_CERTIFICATE_BASE64",
        "DEVELOPER_ID_APPLICATION",
        "--codesign-identity",
        "codesign --verify --deep --strict",
        "notarytool submit",
        "stapler staple",
        "stapler validate",
        "spctl --assess",
        "com.chroming.pdfdir",
    ):
        assert contract in workflow, contract


@pytest.mark.parametrize(
    ("tag", "expected"),
    (
        ("v0.3.0-beta40", "0.3.0"),
        ("v0.3.0.beta2", "0.3.0"),
        ("v2.7", "2.7.0"),
    ),
)
def test_macos_short_version_normalizer_returns_three_numeric_parts(
    tag, expected
):
    env = os.environ.copy()
    env["RELEASE_VERSION"] = tag

    result = subprocess.run(
        [sys.executable, "-c", _mac_bundle_version_python()],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.stdout.strip() == expected


def test_macos_short_version_normalizer_rejects_four_release_parts():
    env = os.environ.copy()
    env["RELEASE_VERSION"] = "v1.2.3.4"

    result = subprocess.run(
        [sys.executable, "-c", _mac_bundle_version_python()],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode != 0


def test_macos_bundle_fields_have_executable_numeric_guards():
    workflow = _release_workflow_text()
    assert r"^[0-9]+\.[0-9]+\.[0-9]+$" in workflow
    assert 'BUILD_VERSION="${GITHUB_RUN_NUMBER}"' in workflow
    assert r"^[0-9]+$" in workflow
    assert "CFBundleShortVersionString ${APP_VERSION}" in workflow
    assert "CFBundleVersion ${BUILD_VERSION}" in workflow
    assert '${VERSION#v}' not in workflow


def test_publish_job_is_the_only_release_writer_and_needs_every_build():
    workflow = _release_workflow_text()
    publish_start = workflow.index("\n  publish:")
    publish_workflow = workflow[publish_start:]

    assert "contents: read" in workflow[:publish_start]
    assert "contents: write" in publish_workflow
    for dependency in (
        "- build-linux",
        "- build-windows",
        "- build-macos",
    ):
        assert dependency in publish_workflow

    assert "softprops/action-gh-release@v3" not in workflow[:publish_start]
    assert publish_workflow.count("softprops/action-gh-release@v3") == 1
    assert "actions/download-artifact@v8" in publish_workflow
    assert "merge-multiple: true" in publish_workflow
    assert "SHA256SUMS" in publish_workflow
    assert "Refuse to mutate an existing tag release" in publish_workflow
    assert "gh api --paginate --slurp" in publish_workflow
    assert "releases?per_page=100" in publish_workflow
    assert "guard_existing_release.py" in publish_workflow
    assert "/releases/tags/" not in publish_workflow
    assert "gh release create" in publish_workflow
    assert "draft: true" in publish_workflow
    assert "overwrite_files: false" in publish_workflow
    assert 'gh release edit "$RELEASE_VERSION" --draft=false' in publish_workflow

    assert "group: release-${{ github.ref }}" in workflow
    assert "cancel-in-progress: false" in workflow


@pytest.mark.parametrize(
    ("pages", "expected_returncode"),
    (
        (
            [
                [
                    {
                        "id": 1,
                        "tag_name": "v0.3.0",
                        "draft": True,
                    }
                ]
            ],
            1,
        ),
        (
            [
                [],
                [
                    {
                        "id": 2,
                        "tag_name": "v0.3.0",
                        "draft": False,
                    }
                ],
            ],
            1,
        ),
        (
            [
                [
                    {
                        "id": 3,
                        "tag_name": "v0.3.0-old",
                        "draft": True,
                    }
                ],
                [],
            ],
            0,
        ),
    ),
)
def test_release_guard_rejects_draft_and_published_exact_tag_matches(
    tmp_path, pages, expected_returncode
):
    response = tmp_path / "release-pages.json"
    response.write_text(json.dumps(pages), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(RELEASE_GUARD),
            str(response),
            "v0.3.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == expected_returncode


def test_release_guard_fails_closed_on_unexpected_api_shape(tmp_path):
    response = tmp_path / "release-pages.json"
    response.write_text('{"message": "unexpected"}', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(RELEASE_GUARD),
            str(response),
            "v0.3.0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Could not verify" in result.stdout


def test_each_build_uploads_only_ci_artifacts_before_publish():
    workflow = _release_workflow_text()
    publish_start = workflow.index("\n  publish:")
    build_workflow = workflow[:publish_start]

    for artifact_name in (
        "release-linux",
        "release-windows",
        "release-macos-intel",
        "release-macos-silicon",
    ):
        assert artifact_name in build_workflow
    assert build_workflow.count("actions/upload-artifact@v7") == 3
    assert "softprops/action-gh-release" not in build_workflow
