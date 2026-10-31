"""build.py writes every file contracts/derivations.md lists, in the shape it states, reproducibly (T018)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
from models import load_roster

import build as build_module

needs_rsvg = pytest.mark.skipif(shutil.which("rsvg-convert") is None, reason="rsvg-convert is not on PATH")


@needs_rsvg
def test_css_derivation(dist: Path) -> None:
    css = dist / "css"
    for name in ("tokens.css", "fonts.css", "motion.css", "forced-colors.css", "family-links.html", "ownership.html"):
        assert (css / name).exists(), name
    tokens = (css / "tokens.css").read_text(encoding="utf-8")
    assert ":root {" in tokens
    assert '@media (prefers-color-scheme: dark) {\n  :root:not([data-theme="light"]) {' in tokens
    assert ':root[data-theme="dark"] {' in tokens
    assert "--idfkit-color-ground: var(--idfkit-color-primitive-white);" in tokens
    assert "--idfkit-color-accent: var(--idfkit-color-primitive-blue-600);" in tokens
    assert "--idfkit-color-accent: var(--idfkit-color-primitive-blue-500);" in tokens
    assert "--idfkit-space-2: 16px;" in tokens and "--idfkit-radius-md: 10px;" in tokens
    assert "--idfkit-motion-ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);" in tokens
    fonts = (css / "fonts.css").read_text(encoding="utf-8")
    assert fonts.count("@font-face") == 7 and "font-display: swap;" in fonts
    assert "--idfkit-font-text:" in fonts and "--idfkit-font-code:" in fonts
    assert sorted(p.name for p in (css / "fonts").glob("*.woff2")) == sorted([
        "inter-400.woff2",
        "inter-500.woff2",
        "inter-600.woff2",
        "inter-700.woff2",
        "inter-800.woff2",
        "jetbrains-mono-400.woff2",
        "jetbrains-mono-500.woff2",
    ])
    assert (css / "fonts" / "LICENSE-inter.txt").exists()
    motion = (css / "motion.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in motion and "--idfkit-motion-duration-base: 0ms;" in motion
    assert "forced-colors: active" in (css / "forced-colors.css").read_text(encoding="utf-8")
    links = (css / "family-links.html").read_text(encoding="utf-8")
    assert '<nav aria-label="idfkit"' in links and links.count("<a href=") == 7
    assert "An idfkit project. MIT License." in (css / "ownership.html").read_text(encoding="utf-8")


@needs_rsvg
def test_material_derivation(dist: Path) -> None:
    material = dist / "material"
    for name in (
        "material.css",
        "palette.yml",
        "social.yml",
        "logo.svg",
        "favicon.svg",
        "footer.html",
        "attribution.html",
        "fonts.css",
    ):
        assert (material / name).exists(), name
    css = (material / "material.css").read_text(encoding="utf-8")
    assert '[data-md-color-scheme="default"] {' in css and '[data-md-color-scheme="slate"] {' in css
    for prop in (
        "--md-primary-fg-color",
        "--md-accent-fg-color",
        "--md-default-bg-color",
        "--md-default-fg-color",
        "--md-code-bg-color",
    ):
        assert css.count(f"  {prop}:") == 2, prop
    assert "primary: custom" in (material / "palette.yml").read_text(encoding="utf-8")
    assert "cards_layout_options:" in (material / "social.yml").read_text(encoding="utf-8")
    assert "currentColor" in (material / "logo.svg").read_text(encoding="utf-8")
    assert "EnergyPlus" in (material / "attribution.html").read_text(encoding="utf-8")


@needs_rsvg
def test_envelop_derivation(dist: Path) -> None:
    envelop = dist / "envelop"
    primitives = (envelop / "primitives.css").read_text(encoding="utf-8")
    assert ":root {" in primitives and "[data-theme='dark'] {" in primitives
    values = re.findall(r"--p-brand-[a-z0-9-]+: (oklch\([^)]*\));", primitives)
    assert values and all(v.startswith("oklch(") for v in values)
    assert "--p-brand-accent: oklch(" in primitives
    assert build_module.hex_to_oklch("#ffffff").startswith("oklch(100% 0 ")
    assert build_module.hex_to_oklch("#f8fafc") == "oklch(98.4% 0.003 247.9)"
    fonts = (envelop / "fonts.css").read_text(encoding="utf-8")
    assert "--p-font-text:" in fonts and "--p-font-code:" in fonts
    assert (envelop / "brand.svg").exists() and (envelop / "roles.md").exists()
    links = json.loads((envelop / "family-links.json").read_text(encoding="utf-8"))
    assert len(links["links"]) == 7


@needs_rsvg
def test_stytch_derivation(dist: Path, root: Path) -> None:
    schema = json.loads((root / "providers" / "stytch-styles.json").read_text(encoding="utf-8"))["properties"]
    for name in ("styles.json", "styles.light.json"):
        styles = json.loads((dist / "stytch" / name).read_text(encoding="utf-8"))

        def keys(node: dict[str, object], prefix: str = "") -> set[str]:
            out: set[str] = set()
            for key, value in node.items():
                path = f"{prefix}.{key}" if prefix else key
                out |= keys(value, path) if isinstance(value, dict) else {path}
            return out

        assert keys(styles) <= keys(schema), name
        assert styles["buttons"]["primary"]["backgroundColor"] in ("#3b82f6", "#2563eb")
    coverage = (dist / "stytch" / "schema-coverage.md").read_text(encoding="utf-8")
    assert "## Not expressible" in coverage and "font.family.code" in coverage


@needs_rsvg
def test_hero_derivation(dist: Path) -> None:
    text = (dist / "hero" / "hero-palette.js").read_text(encoding="utf-8")
    assert text.startswith("//") and "export const heroPalette = {" in text and "export default heroPalette;" in text
    body = text.split("export const heroPalette = {", 1)[1].split("};", 1)[1]
    assert not re.search(r"#[0-9a-f]{6}", body)
    for role in ("warm", "cool", "structure", "ground"):
        assert f"{role}:" in text


@needs_rsvg
def test_readme_and_repo_preview_derivations(dist: Path, root: Path) -> None:
    for name in build_module.README_IMAGES:
        assert (dist / "readme" / name).exists(), name
    assert 'width="96" height="96"' in (dist / "readme" / "mark-on-dark.svg").read_text(encoding="utf-8")
    roster = load_roster(root / "touchpoints.toml")
    previews = sorted(p.name for p in (dist / "repo-preview").glob("*.png"))
    assert previews == sorted(f"{build_module.preview_name(t)}.png" for t in roster.readmes())
    from rasters import png_size

    for path in (dist / "repo-preview").glob("*.png"):
        assert png_size(path.read_bytes()) == (1280, 640)
        assert path.stat().st_size < 1_000_000


@needs_rsvg
def test_hosts_derivation(dist: Path, root: Path) -> None:
    from rasters import png_size, unpack_ico

    roster = load_roster(root / "touchpoints.toml")
    for touchpoint in roster.hosts():
        host = dist / "hosts" / (touchpoint.host_name or "")
        for name in (
            "favicon.svg",
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "og.png",
            "head.html",
            "manifest.webmanifest",
        ):
            assert (host / name).exists(), f"{touchpoint.id}: {name}"
        assert png_size((host / "og.png").read_bytes()) == (1200, 630)
        assert [png_size(f)[0] for f in unpack_ico((host / "favicon.ico").read_bytes())] == [16, 32, 48]
        head = (host / "head.html").read_text(encoding="utf-8")
        assert 'property="og:image"' in head and (touchpoint.host or "") in head and "identity-2026.1" in head
        manifest = json.loads((host / "manifest.webmanifest").read_text(encoding="utf-8"))
        assert manifest["name"].startswith("idfkit")


@needs_rsvg
def test_brand_page_names_the_tag_and_every_exception(dist: Path, root: Path) -> None:
    page = (dist / "brand-page" / "index.html").read_text(encoding="utf-8")
    assert "identity-2026.1" in page
    roster = load_roster(root / "touchpoints.toml")
    for touchpoint in roster.touchpoints:
        for exception in touchpoint.exceptions:
            assert exception.part in page
    assert "releases/download/identity-2026.1/mark-on-dark.svg" in page
    assert (dist / "brand-page" / "assets" / "incorrect-rotated.svg").exists()


@needs_rsvg
def test_review_sheet_shows_every_image(dist: Path) -> None:
    sheet = (dist / "review" / "index.html").read_text(encoding="utf-8")
    images = [
        p
        for p in dist.rglob("*")
        if p.is_file()
        and p.suffix in (".svg", ".png", ".ico")
        and "review" not in p.parts
        and "archives" not in p.parts
    ]
    for path in images:
        assert path.relative_to(dist).as_posix() in sheet, path
    assert "light" in sheet and "dark" in sheet


@needs_rsvg
def test_archives(dist: Path) -> None:
    archives = sorted(p.name for p in (dist / "archives").glob("*.tar.gz"))
    assert archives == sorted(f"{d}.tar.gz" for d in build_module.MECHANISM_DIRS)
    assert "review.tar.gz" not in archives


@needs_rsvg
def test_two_builds_are_identical(root: Path, tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    build_module.run(build_module.load_build(root, a, "identity-2026.1"))
    build_module.run(build_module.load_build(root, b, "identity-2026.1"))
    text_files = [
        p for p in a.rglob("*") if p.is_file() and p.suffix not in (".png", ".ico") and "review" not in p.parts
    ]
    for path in text_files:
        assert path.read_bytes() == (b / path.relative_to(a)).read_bytes(), path
    assert build_module.compare(a, b) == []
    (b / "css" / "tokens.css").write_bytes((b / "css" / "tokens.css").read_bytes() + b"x")
    assert any(d.path == "css/tokens.css" for d in build_module.compare(a, b))
