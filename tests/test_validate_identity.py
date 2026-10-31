"""The validator passes the standard and fails each named way (T012, FR-015)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import validate_identity as vi


def _write_tokens(root: Path, mutate: Callable[[dict[str, Any]], object]) -> None:
    path = root / "identity.tokens.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def test_the_standard_validates(root: Path) -> None:
    report = vi.validate(root)
    assert report.ok, [f.render() for f in report.findings]
    assert report.pairs
    assert all(r.passes for r in report.pairs)


def test_the_measured_pairs_of_research_r8(root: Path) -> None:
    assert round(vi.contrast("#e2e8f0", "#060a14"), 2) == 16.05
    assert round(vi.contrast("#3b82f6", "#ffffff"), 2) == 3.68
    assert round(vi.contrast("#2563eb", "#ffffff"), 2) == 5.17
    assert round(vi.contrast("#3b82f6", "#060a14"), 2) == 5.38
    assert round(vi.contrast("#64748b", "#060a14"), 2) == 4.16
    report = vi.validate(root)
    light_accent = next(
        r
        for r in report.pairs
        if r.pair.foreground == "color.role.accent" and r.pair.background == "color.role.ground" and r.theme == "light"
    )
    assert light_accent.foreground == "#2563eb" and light_accent.ratio == 5.17


def test_the_light_accent_at_3b82f6_fails_naming_pair_theme_ratio_and_threshold(standard_copy: Path) -> None:
    _write_tokens(
        standard_copy,
        lambda d: d["color"]["role"]["accent"]["$value"].__setitem__("light", "{color.primitive.blue-500}"),
    )
    report = vi.validate(standard_copy)
    assert not report.ok
    finding = report.findings[0]
    assert finding.check == "contrast"
    assert finding.where == "color.role.accent on color.role.ground"
    assert "light theme" in finding.message
    assert "3.68:1" in finding.message
    assert "4.5:1" in finding.message


def test_an_alias_of_a_missing_token_fails(standard_copy: Path) -> None:
    _write_tokens(
        standard_copy, lambda d: d["color"]["role"]["link"]["$value"].__setitem__("dark", "{color.primitive.blue-999}")
    )
    report = vi.validate(standard_copy)
    assert any(f.check == "alias" and f.where == "color.role.link" and "blue-999" in f.message for f in report.findings)


def test_a_template_with_a_literal_fails(standard_copy: Path, fixtures: Path) -> None:
    shutil.copy(fixtures / "standard" / "literal-template.svg", standard_copy / "templates" / "og.svg")
    report = vi.validate(standard_copy)
    assert any(
        f.check == "templates" and f.where.startswith("templates/og.svg:") and "#ff0000" in f.message
        for f in report.findings
    )


def test_a_roster_with_eight_family_links_fails(standard_copy: Path, fixtures: Path) -> None:
    shutil.copy(fixtures / "standard" / "eight-links.toml", standard_copy / "touchpoints.toml")
    report = vi.validate(standard_copy)
    assert any(f.check == "roster" and f.where == "family_link" and "seven" in f.message for f in report.findings)


def test_an_exception_that_is_a_lag_in_disguise_fails(standard_copy: Path, fixtures: Path) -> None:
    shutil.copy(fixtures / "standard" / "exception-yet.toml", standard_copy / "touchpoints.toml")
    report = vi.validate(standard_copy)
    assert any(f.check == "roster" and f.where.endswith(".reason") and "Lag" in f.message for f in report.findings)


def test_an_edited_master_fails(standard_copy: Path) -> None:
    target = standard_copy / "marks" / "tile.svg"
    target.write_text(target.read_text(encoding="utf-8").replace('rx="112.64"', 'rx="100"'), encoding="utf-8")
    report = vi.validate(standard_copy)
    assert any(f.check == "marks" and "tile.svg" in f.message for f in report.findings)


def test_cli_exit_codes(root: Path, standard_copy: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert vi.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "accent on ground" in out and "5.17" in out
    _write_tokens(
        standard_copy,
        lambda d: d["color"]["role"]["accent"]["$value"].__setitem__("light", "{color.primitive.blue-500}"),
    )
    assert vi.main(["--root", str(standard_copy), "--quiet"]) == 1
    assert "FAIL contrast" in capsys.readouterr().out
