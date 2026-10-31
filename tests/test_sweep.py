"""The sweep reads every declaration from where it lives and fails only an unexplained host (T031, FR-006)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import sweep_touchpoints as sw


@pytest.fixture
def workspace(tmp_path: Path, root: Path) -> Path:
    """A fixture workspace: a tagged standard and five touchpoints in five states."""
    standard = tmp_path / "idfkit-brand"
    standard.mkdir()
    shutil.copy(root / "touchpoints.toml", standard / "touchpoints.toml")
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    for command in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "add", "touchpoints.toml"],
        ["git", "commit", "-q", "-m", "roster"],
        ["git", "tag", "identity-2026.1"],
        ["git", "tag", "identity-2026.2"],
        ["git", "tag", "identity-2025.9"],
    ):
        subprocess.run(command, cwd=standard, check=True, env=env)
    # current
    developers = tmp_path / "idfkit-developers"
    developers.mkdir()
    (developers / "pyproject.toml").write_text('[tool.idfkit.identity]\nlevel = "identity-2026.2"\n', encoding="utf-8")
    # behind with a deliberate lag
    mcp = tmp_path / "idfkit-mcp"
    mcp.mkdir()
    (mcp / "pyproject.toml").write_text(
        '[tool.idfkit.identity]\nlevel = "identity-2026.1"\nlag = { kind = "deliberate", reason = "waits for the next docs release" }\n',
        encoding="utf-8",
    )
    # behind with none
    shoebox = tmp_path / "idfkit-shoebox"
    shoebox.mkdir()
    (shoebox / "package.json").write_text(json.dumps({"idfkit": {"identity": "identity-2026.1"}}), encoding="utf-8")
    # a README behind
    idfkit = tmp_path / "idfkit"
    idfkit.mkdir()
    (idfkit / "README.md").write_text(
        '<img src="https://raw.githubusercontent.com/idfkit/idfkit-brand/identity-2026.1/marks/tile.svg">\n',
        encoding="utf-8",
    )
    # the application, under its folder alias, with a not-yet lag
    envelop = tmp_path / "envelop"
    envelop.mkdir()
    (envelop / "package.json").write_text(
        json.dumps({
            "idfkit": {
                "identity": "identity-2026.1",
                "identityLag": {"kind": "not-yet", "issue": "https://github.com/idfkit/idfkit-app/issues/1"},
            }
        }),
        encoding="utf-8",
    )
    return tmp_path


def test_latest_tag_orders_by_year_then_number(workspace: Path) -> None:
    assert sw.latest_tag(workspace / "idfkit-brand") == "identity-2026.2"


def test_sweep_reports_every_state(workspace: Path) -> None:
    from models import load_roster

    roster = load_roster(workspace / "idfkit-brand" / "touchpoints.toml")
    report = sw.sweep(roster, workspace, "identity-2026.2")
    by_id = {t.id: t for t in report.touchpoints}
    assert by_id["developers"].status == "current"
    assert by_id["mcp"].status == "lagging" and by_id["mcp"].lag is not None and by_id["mcp"].lag.kind == "deliberate"
    assert by_id["shoebox"].status == "unexplained"
    assert by_id["readme-idfkit"].status == "behind"
    assert by_id["app"].status == "lagging" and by_id["app"].lag is not None and by_id["app"].lag.issue
    assert by_id["docs"].status == "unreachable"
    assert [t.id for t in report.unexplained] == ["shoebox"]
    assert "docs" in [t.id for t in report.unreachable]


def test_cli_writes_the_report_and_fails_only_for_the_unexplained_host(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = sw.main(["--workspace", str(workspace), "--standard", str(workspace / "idfkit-brand")])
    assert code == sw.EXIT_UNEXPLAINED
    out = capsys.readouterr().out
    assert "latest tag: identity-2026.2" in out
    assert any(line.startswith("shoebox") and "unexplained" in line for line in out.splitlines())
    assert any(line.startswith("docs") and "unreachable" in line for line in out.splitlines())
    report = json.loads((workspace / "sweep-report.json").read_text(encoding="utf-8"))
    assert report["identity_latest"] == "identity-2026.2"
    assert report["unexplained"] == ["shoebox"]
    (workspace / "idfkit-shoebox" / "package.json").write_text(
        json.dumps({
            "idfkit": {
                "identity": "identity-2026.1",
                "identityLag": {"kind": "deliberate", "reason": "the drafting sheet waits for its next release"},
            }
        }),
        encoding="utf-8",
    )
    assert sw.main(["--workspace", str(workspace), "--standard", str(workspace / "idfkit-brand")]) == 0


def test_an_untagged_standard_reports_everything_current(workspace: Path, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(
        ["git", "tag", "-d", "identity-2026.1", "identity-2026.2", "identity-2025.9"],
        cwd=workspace / "idfkit-brand",
        check=True,
        capture_output=True,
    )
    assert sw.latest_tag(workspace / "idfkit-brand") is None
    assert sw.main(["--workspace", str(workspace), "--standard", str(workspace / "idfkit-brand")]) == 0
    assert "latest tag: unreleased" in capsys.readouterr().out
