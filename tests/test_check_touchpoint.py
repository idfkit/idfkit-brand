"""The five assertions of check_touchpoint.py, on fixture trees (T028, FR-005, FR-007)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import check_touchpoint as ct
import pytest
from models import Roster, load_roster

LEVEL = "identity-2026.1"


def _material_touchpoint(tmp_path: Path, dist: Path) -> Path:
    root = tmp_path / "idfkit-developers"
    (root / "docs" / "stylesheets").mkdir(parents=True)
    (root / "docs" / "overrides" / "partials").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "x"\n\n[tool.idfkit.identity]\nlevel = "identity-2026.1"\n', encoding="utf-8"
    )
    (root / "mkdocs.yml").write_text(
        "site_name: idfkit\ntheme:\n  name: material\n  palette:\n    primary: custom\nextra_css:\n  - identity/hosts/developers.idfkit.com/lockup.css\n",
        encoding="utf-8",
    )
    (root / "docs" / "stylesheets" / "extra.css").write_text(".md-grid { max-width: 70rem; }\n", encoding="utf-8")
    (root / "docs" / "overrides" / "partials" / "copyright.html").write_text(
        "<div>{% include 'identity/material/footer.html' %}</div>\n", encoding="utf-8"
    )
    shutil.copytree(dist / "material", root / "docs" / "identity" / "material")
    shutil.copytree(
        dist / "hosts" / "developers.idfkit.com", root / "docs" / "identity" / "hosts" / "developers.idfkit.com"
    )
    return root


def _css_touchpoint(tmp_path: Path, dist: Path) -> Path:
    root = tmp_path / "idfkit-shoebox"
    (root / "src").mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps({"name": "idfkit-shoebox", "idfkit": {"identity": LEVEL}}, indent=2), encoding="utf-8"
    )
    (root / "index.html").write_text(
        '<!doctype html><html><head><link rel="stylesheet" href="identity/css/tokens.css"><link rel="stylesheet" href="identity/hosts/shoebox.idfkit.com/lockup.css"></head><body></body></html>\n',
        encoding="utf-8",
    )
    (root / "src" / "sheet.css").write_text(":root { --sheet: var(--idfkit-color-surface); }\n", encoding="utf-8")
    shutil.copytree(dist / "css", root / "identity" / "css")
    shutil.copytree(dist / "hosts" / "shoebox.idfkit.com", root / "identity" / "hosts" / "shoebox.idfkit.com")
    return root


@pytest.fixture
def roster(root: Path):
    return load_roster(root / "touchpoints.toml")


def test_a_conforming_material_touchpoint_passes(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _material_touchpoint(tmp_path, dist)
    findings = ct.check(
        roster, "idfkit/idfkit-developers", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert findings == [], [f.render() for f in findings]


def test_a_hand_edited_vendored_file_fails_naming_file_and_offset(
    tmp_path: Path, dist: Path, roster: Roster, root: Path
) -> None:
    touchpoint = _material_touchpoint(tmp_path, dist)
    target = touchpoint / "docs" / "identity" / "material" / "material.css"
    text = target.read_text(encoding="utf-8")
    offset = text.index("#2563eb")
    target.write_text(text.replace("#2563eb", "#2563ec", 1), encoding="utf-8")
    findings = ct.check(
        roster, "idfkit/idfkit-developers", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert len(findings) == 1
    assert findings[0].assertion == 3
    assert findings[0].file == "docs/identity/material/material.css"
    assert f"byte offset {offset + 6}" in findings[0].message


def test_a_hand_edited_raster_fails_by_pixel(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _material_touchpoint(tmp_path, dist)
    target = touchpoint / "docs" / "identity" / "hosts" / "developers.idfkit.com" / "icon-192.png"
    shutil.copy(dist / "hosts" / "developers.idfkit.com" / "apple-touch-icon.png", target)
    findings = ct.check(
        roster, "idfkit/idfkit-developers", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert [f.file for f in findings] == ["docs/identity/hosts/developers.idfkit.com/icon-192.png"]
    assert "against" in findings[0].message or "pixel" in findings[0].message
    assert (
        ct.check(roster, "idfkit/idfkit-developers", touchpoint, LEVEL, dist, root, "skip", "host", require_tag=False)
        == []
    )


def test_a_rewritten_head_prefix_still_passes(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _material_touchpoint(tmp_path, dist)
    head = touchpoint / "docs" / "identity" / "hosts" / "developers.idfkit.com" / "head.html"
    head.write_text(
        head
        .read_text(encoding="utf-8")
        .replace('href="/', 'href="/identity/hosts/developers.idfkit.com/')
        .replace("developers.idfkit.com/og.png", "developers.idfkit.com/identity/hosts/developers.idfkit.com/og.png"),
        encoding="utf-8",
    )
    findings = ct.check(
        roster, "idfkit/idfkit-developers", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert findings == [], [f.render() for f in findings]


def test_a_wrong_declaration_fails(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _material_touchpoint(tmp_path, dist)
    (touchpoint / "pyproject.toml").write_text('[tool.idfkit.identity]\nlevel = "identity-2026.2"\n', encoding="utf-8")
    findings = ct.check(
        roster, "idfkit/idfkit-developers", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert (
        findings[0].assertion == 2 and "identity-2026.2" in findings[0].message and findings[0].file == "pyproject.toml"
    )


def test_a_stray_literal_fails_naming_file_line_and_value(
    tmp_path: Path, dist: Path, roster: Roster, root: Path
) -> None:
    touchpoint = _css_touchpoint(tmp_path, dist)
    (touchpoint / "src" / "sheet.css").write_text(
        ":root { --sheet: var(--idfkit-color-surface); }\n.plate { color: #ff0000; }\n", encoding="utf-8"
    )
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert len(findings) == 1
    assert (findings[0].assertion, findings[0].file, findings[0].place) == (4, "src/sheet.css", "2")
    assert "#ff0000" in findings[0].message


def test_a_pasted_head_fragment_is_not_a_stray_literal(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _css_touchpoint(tmp_path, dist)
    head = (dist / "hosts" / "shoebox.idfkit.com" / "head.html").read_text(encoding="utf-8")
    assert "theme-color" in head and "#" in head
    page = touchpoint / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("<head>", "<head>\n" + head, 1), encoding="utf-8")
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert findings == []
    (touchpoint / "index.html").write_text(
        page.read_text(encoding="utf-8").replace('content="#060a14"', 'content="#060a15"', 1), encoding="utf-8"
    )
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert [f.assertion for f in findings] == [4] and "#060a15" in findings[0].message


def test_a_marked_literal_with_a_matching_exception_passes(tmp_path: Path, dist: Path, root: Path) -> None:
    touchpoint = _css_touchpoint(tmp_path, dist)
    (touchpoint / "src" / "sheet.css").write_text(
        ".plate { color: #ff0000; /* identity-exception: color.role.accent */ }\n", encoding="utf-8"
    )
    standard = tmp_path / "standard"
    standard.mkdir()
    text = (root / "touchpoints.toml").read_text(encoding="utf-8")
    marker = 'notes = "The css derivation and hosts/shoebox.idfkit.com/'
    assert marker in text
    text = text.replace(
        marker,
        '[[touchpoint.exception]]\npart = "color.role.accent"\nreason = "The plate\'s stamp is a photograph of a red pen; the page keeps it."\nsince = "identity-2026.1"\n\n'
        + marker,
    )
    # TOML: the exception table must come after the touchpoint's own keys, so move notes above it.
    text = text.replace(
        '[[touchpoint.exception]]\npart = "color.role.accent"',
        '[[touchpoint.exception]]\npart = "color.role.accent"',
        1,
    )
    (standard / "touchpoints.toml").write_text(text, encoding="utf-8")
    roster = load_roster(standard / "touchpoints.toml")
    shoebox = roster.by_id("shoebox")
    assert shoebox is not None and any(e.part == "color.role.accent" for e in shoebox.exceptions)
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, standard, "compare", "host", require_tag=False
    )
    assert findings == [], [f.render() for f in findings]
    (touchpoint / "src" / "sheet.css").write_text(
        ".plate { color: #ff0000; /* identity-exception: color.role.focus */ }\n", encoding="utf-8"
    )
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, standard, "compare", "host", require_tag=False
    )
    assert len(findings) == 1 and "records no such exception" in findings[0].message


def test_a_host_that_does_not_load_its_lockup_fails(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _css_touchpoint(tmp_path, dist)
    page = touchpoint / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("lockup.css", "other.css"), encoding="utf-8")
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert [(f.assertion, f.file) for f in findings] == [(6, "index.html")]


def test_a_hand_drawn_mark_fails_naming_file_and_line(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _css_touchpoint(tmp_path, dist)
    page = touchpoint / "index.html"
    drawn = page.read_text(encoding="utf-8").replace(
        "<body>", '<body>\n<svg viewBox="0 0 48 48"><path d="M4 15a3 3 0 0 1 3-3h17v12h12v17"/></svg>'
    )
    page.write_text(drawn, encoding="utf-8")
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert [(f.assertion, f.file, f.place) for f in findings] == [(6, "index.html", "2")]


def test_a_font_host_and_a_js_colour_fail(tmp_path: Path, dist: Path, roster: Roster, root: Path) -> None:
    touchpoint = _css_touchpoint(tmp_path, dist)
    (touchpoint / "index.html").write_text(
        '<link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet">\n', encoding="utf-8"
    )
    findings = ct.check(
        roster, "idfkit/idfkit-shoebox", touchpoint, LEVEL, dist, root, "compare", "host", require_tag=False
    )
    assert any(f.file == "index.html" and "fonts.googleapis.com" in f.message for f in findings)
    assert ct.scan_line("    warmHot:   new THREE.Color(0xff2a6d),", ".js") == "0xff2a6d"
    assert ct.scan_line("  font-family: var(--idfkit-font-text);", ".css") is None
    assert ct.scan_line("  font-family: 'JetBrains Mono', monospace;", ".css") is not None


def test_a_conforming_library_readme_passes(tmp_path: Path, fixtures: Path, roster: Roster, root: Path) -> None:
    touchpoint = tmp_path / "idfkit"
    touchpoint.mkdir()
    shutil.copy(fixtures / "touchpoints" / "library-readme.md", touchpoint / "README.md")
    findings = ct.check(roster, "idfkit/idfkit", touchpoint, LEVEL, None, root, "compare", "readme", require_tag=False)
    assert findings == [], [f.render() for f in findings]


def test_a_release_asset_address_fails_because_a_browser_will_not_display_it(
    tmp_path: Path, fixtures: Path, roster: Roster, root: Path
) -> None:
    (tmp_path / "README.md").write_text(
        (fixtures / "touchpoints" / "library-readme.md")
        .read_text(encoding="utf-8")
        .replace(
            "https://raw.githubusercontent.com/idfkit/idfkit-brand/identity-2026.1/marks/",
            "https://github.com/idfkit/idfkit-brand/releases/download/identity-2026.1/",
        ),
        encoding="utf-8",
    )
    findings = ct.check(roster, "idfkit/idfkit", tmp_path, LEVEL, None, root, "compare", "readme", require_tag=False)
    assert findings and all(f.assertion in (2, 5) for f in findings)


def test_every_address_a_readme_may_use_exists_in_marks(root: Path) -> None:
    for name in ("mark-on-dark.svg", "mark-on-light.svg", "tile.svg", "lockup-on-dark.svg", "lockup-on-light.svg"):
        assert (root / "marks" / name).is_file(), name


def test_a_readme_missing_its_heading_fails(tmp_path: Path, fixtures: Path, roster: Roster, root: Path) -> None:
    touchpoint = tmp_path / "idfkit"
    touchpoint.mkdir()
    text = (fixtures / "touchpoints" / "library-readme.md").read_text(encoding="utf-8").replace("# idfkit\n\n", "")
    (touchpoint / "README.md").write_text(text, encoding="utf-8")
    findings = ct.check(roster, "idfkit/idfkit", touchpoint, LEVEL, None, root, "compare", "readme", require_tag=False)
    assert any(f.assertion == 5 and "heading" in f.message for f in findings)


def test_a_library_readme_without_its_parity_statement_fails(
    tmp_path: Path, fixtures: Path, roster: Roster, root: Path
) -> None:
    touchpoint = tmp_path / "idfkit"
    touchpoint.mkdir()
    text = (fixtures / "touchpoints" / "library-readme.md").read_text(encoding="utf-8")
    text = text[: text.index("## Parity")]
    (touchpoint / "README.md").write_text(text, encoding="utf-8")
    findings = ct.check(roster, "idfkit/idfkit", touchpoint, LEVEL, None, root, "compare", "readme", require_tag=False)
    assert len(findings) == 1 and "parity" in findings[0].message and "FR-033" in findings[0].message


def test_a_readme_at_another_tag_fails_on_its_declaration(
    tmp_path: Path, fixtures: Path, roster: Roster, root: Path
) -> None:
    touchpoint = tmp_path / "idfkit"
    touchpoint.mkdir()
    text = (
        (fixtures / "touchpoints" / "library-readme.md")
        .read_text(encoding="utf-8")
        .replace("identity-2026.1/marks/mark-on-dark", "identity-2026.2/marks/mark-on-dark")
    )
    (touchpoint / "README.md").write_text(text, encoding="utf-8")
    findings = ct.check(roster, "idfkit/idfkit", touchpoint, LEVEL, None, root, "compare", "readme", require_tag=False)
    assert findings[0].assertion == 2 and "different tags" in findings[0].message


def test_an_unlisted_repository_fails_membership(tmp_path: Path, roster: Roster, root: Path) -> None:
    findings = ct.check(roster, "idfkit/idfkit-engine", tmp_path, LEVEL, None, root, "compare", None, require_tag=False)
    assert findings[0].assertion == 1 and "idfkit-engine" in findings[0].message


def test_cli(tmp_path: Path, dist: Path, root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    touchpoint = _material_touchpoint(tmp_path, dist)
    assert (
        ct.main([
            "--repository",
            "idfkit/idfkit-developers",
            "--level",
            LEVEL,
            "--root",
            str(touchpoint),
            "--dist",
            str(dist),
            "--standard",
            str(root),
            "--kind",
            "host",
            "--allow-untagged",
        ])
        == 0
    )
    assert "conforms to identity-2026.1" in capsys.readouterr().out
    assert (
        ct.main([
            "--repository",
            "idfkit/idfkit-developers",
            "--level",
            "main",
            "--root",
            str(touchpoint),
            "--standard",
            str(root),
        ])
        == ct.EXIT_UNREADABLE
    )
    assert (
        ct.main([
            "--repository",
            "idfkit/idfkit-developers",
            "--level",
            LEVEL,
            "--root",
            str(touchpoint),
            "--dist",
            str(tmp_path / "missing"),
            "--standard",
            str(root),
        ])
        == ct.EXIT_UNREADABLE
    )
    (touchpoint / "docs" / "stylesheets" / "extra.css").write_text("a { color: rgb(0, 0, 0); }\n", encoding="utf-8")
    assert (
        ct.main([
            "--repository",
            "idfkit/idfkit-developers",
            "--level",
            LEVEL,
            "--root",
            str(touchpoint),
            "--dist",
            str(dist),
            "--standard",
            str(root),
            "--kind",
            "host",
            "--allow-untagged",
        ])
        == ct.EXIT_FINDINGS
    )
    out = capsys.readouterr().out
    assert "FAIL assertion 4: docs/stylesheets/extra.css:1:" in out and "rgb(" in out
