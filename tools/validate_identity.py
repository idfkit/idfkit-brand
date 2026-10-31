"""The gate: is the standard well formed, and does every pair meet its threshold in both themes?

Runs on every pull request (`identity.yml`) and before every tag; it is the only thing permitted
to call the standard well formed (data-model, Standard, rule 1). What it checks, in order:

  1. `identity.tokens.json` parses under contracts/identity-standard.md section 2.
  2. Every role alias resolves to a primitive.
  3. Every Pair (an ink role on each ground its `on` lists) meets its `minContrast` in both themes,
     by WCAG 2.1 relative luminance (FR-015, SC-006).
  4. Every template under templates/ is free of colour and font literals.
  5. `touchpoints.toml` obeys the roster rules of contracts/touchpoint-check.md section 1.
  6. The committed masters under marks/ equal what mark.py writes, and mark.py's fixed inks are
     the token file's.

Exit 0 with a table of every pair and its ratio in both themes; exit 1 naming the first failure.
Standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models import THEMES, ColorValue, Pair, ShapeError, ThemeId, TokenFile, load_roster, load_tokens
from rasters import compare_png

HERE = Path(__file__).resolve().parent.parent

#: What a template may not carry (contract, templates row): a colour literal in any CSS or SVG
#: form, or a font family named outside a token placeholder.
COLOR_LITERAL = re.compile(
    r"(?<![\w{-])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b|\b(?:rgba?|hsla?|oklch|oklab)\("
)
FONT_LITERAL = re.compile(
    r"""(?:font-family\s*[:=]\s*["']?\s*(?!var\(|\{\{|inherit|initial|unset)[A-Za-z])|@font-face|fonts\.googleapis\.com|fonts\.gstatic\.com"""
)
TEMPLATE_SUFFIXES = (".svg", ".html", ".css", ".webmanifest", ".yml", ".json", ".js", ".md")


@dataclass(frozen=True, slots=True)
class Finding:
    """One failure, with where it was found."""

    check: str
    where: str
    message: str

    def render(self) -> str:
        return f"{self.check}: {self.where}: {self.message}"


@dataclass(frozen=True, slots=True)
class PairResult:
    pair: Pair
    theme: ThemeId
    foreground: str
    background: str
    ratio: float

    @property
    def passes(self) -> bool:
        return self.ratio >= self.pair.threshold


@dataclass(frozen=True, slots=True)
class Report:
    findings: tuple[Finding, ...]
    pairs: tuple[PairResult, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


# 1. Contrast, per WCAG 2.1


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


# 2. The checks


def check_tokens(root: Path) -> tuple[TokenFile | None, list[Finding]]:
    try:
        return load_tokens(root / "identity.tokens.json"), []
    except ShapeError as error:
        return None, [Finding("tokens", error.key, error.message)]


def check_aliases(tokens: TokenFile) -> list[Finding]:
    findings: list[Finding] = []
    for token in tokens.colors("role"):
        for theme in THEMES:
            try:
                tokens.resolve(token.name, theme)
            except ShapeError as error:
                findings.append(Finding("alias", token.name, f"{theme}: {error.key}: {error.message}"))
    return findings


def measure_pairs(tokens: TokenFile) -> list[PairResult]:
    results: list[PairResult] = []
    for pair in tokens.pairs():
        for theme in THEMES:
            try:
                fg = tokens.resolve(pair.foreground, theme)
                bg = tokens.resolve(pair.background, theme)
            except ShapeError:
                continue
            results.append(PairResult(pair, theme, fg, bg, round(contrast(fg, bg), 2)))
    return results


def check_pairs(results: Iterable[PairResult]) -> list[Finding]:
    return [
        Finding(
            "contrast",
            f"{r.pair.foreground} on {r.pair.background}",
            f"{r.theme} theme: {r.foreground} on {r.background} is {r.ratio:.2f}:1, below {r.pair.threshold:g}:1 (FR-015)",
        )
        for r in results
        if not r.passes
    ]


def check_templates(root: Path) -> list[Finding]:
    """A literal in a template is a validation failure: templates read tokens by name."""
    findings: list[Finding] = []
    templates = root / "templates"
    if not templates.is_dir():
        return [Finding("templates", str(templates), "missing")]
    for path in sorted(p for p in templates.rglob("*") if p.is_file() and p.suffix in TEMPLATE_SUFFIXES):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            color = COLOR_LITERAL.search(line)
            if color:
                findings.append(
                    Finding("templates", f"{path.relative_to(root)}:{number}", f"colour literal {color.group(0)!r}")
                )
                break
            font = FONT_LITERAL.search(line)
            if font:
                findings.append(
                    Finding("templates", f"{path.relative_to(root)}:{number}", f"font literal {font.group(0)!r}")
                )
                break
    return findings


def check_roster(root: Path) -> list[Finding]:
    try:
        load_roster(root / "touchpoints.toml")
    except ShapeError as error:
        return [Finding("roster", error.key, error.message)]
    return []


def _load_mark_module(root: Path):
    spec = importlib.util.spec_from_file_location("idfkit_mark", root / "mark.py")
    if spec is None or spec.loader is None:
        raise ShapeError("mark.py", "cannot be imported")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    spec.loader.exec_module(module)
    return module


def check_tile_raster(root: Path, mark: ModuleType) -> list[Finding]:
    """The committed raster is the tile master at its size, compared by decoded pixels."""
    png = root / "marks" / mark.TILE_RASTER
    where = f"marks/{mark.TILE_RASTER}"
    if not png.exists():
        return [Finding("marks", where, "missing; run `python mark.py --write`")]
    if shutil.which("rsvg-convert") is None:
        return [Finding("marks", where, "cannot be compared: rsvg-convert is not on PATH; install librsvg")]
    with tempfile.TemporaryDirectory() as scratch:
        expected = Path(scratch) / mark.TILE_RASTER
        mark.rasterize_tile(root / "marks" / "tile.svg", expected)
        difference = compare_png(png.read_bytes(), expected.read_bytes())
    if difference is None:
        return []
    rendered = difference if isinstance(difference, str) else difference.render()
    return [Finding("marks", where, f"differs from marks/tile.svg: {rendered}; run `python mark.py --write`")]


def check_marks(root: Path, tokens: TokenFile | None) -> list[Finding]:
    if not (root / "mark.py").exists():
        return [Finding("marks", "mark.py", "missing")]
    mark = _load_mark_module(root)
    findings: list[Finding] = []
    differing = mark.check(root / "marks")
    if differing:
        findings.append(
            Finding(
                "marks", "marks/", "differs from mark.py for " + ", ".join(differing) + "; run `python mark.py --write`"
            )
        )
    findings += check_tile_raster(root, mark)
    if tokens is not None:
        expected = {
            "INK_ON_DARK": "color.primitive.slate-200",
            "INK_ON_LIGHT": "color.primitive.slate-950",
            "TILE_GROUND": "color.primitive.navy-950",
            "DIVIDER_INK": "color.primitive.slate-500",
        }
        for constant, name in expected.items():
            try:
                value = tokens.get(name).value
            except ShapeError as error:
                findings.append(Finding("marks", name, error.message))
                continue
            if isinstance(value, ColorValue) and getattr(mark, constant) != value.dark:
                findings.append(
                    Finding(
                        "marks",
                        f"mark.py {constant}",
                        f"is {getattr(mark, constant)}, and {name} is {value.dark}; the mark's inks are the token file's",
                    )
                )
    return findings


def validate(root: Path) -> Report:
    tokens, findings = check_tokens(root)
    pairs: list[PairResult] = []
    if tokens is not None:
        findings += check_aliases(tokens)
        pairs = measure_pairs(tokens)
        findings += check_pairs(pairs)
    findings += check_templates(root)
    findings += check_roster(root)
    try:
        findings += check_marks(root, tokens)
    except ShapeError as error:
        findings.append(Finding("marks", error.key, error.message))
    return Report(tuple(findings), tuple(pairs))


# 3. Output


def render_table(pairs: Iterable[PairResult]) -> str:
    rows = [("Pair", "Threshold", "Light", "Dark")]
    by_pair: dict[tuple[str, str], dict[str, PairResult]] = {}
    for result in pairs:
        by_pair.setdefault((result.pair.foreground, result.pair.background), {})[result.theme] = result
    for (fg, bg), themes in by_pair.items():
        light, dark = themes.get("light"), themes.get("dark")
        first = light or dark
        threshold = first.pair.threshold if first else 0.0
        rows.append((
            f"{fg.removeprefix('color.role.')} on {bg.removeprefix('color.role.')}",
            f"{threshold:g}:1",
            f"{light.ratio:.2f} ({light.foreground} on {light.background})" if light else "",
            f"{dark.ratio:.2f} ({dark.foreground} on {dark.background})" if dark else "",
        ))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    lines = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the identity standard.")
    parser.add_argument("--root", type=Path, default=HERE, help="the standard's checkout (default: this repository)")
    parser.add_argument("--quiet", action="store_true", help="print failures only")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = validate(args.root.resolve())
    if not args.quiet:
        print(render_table(report.pairs))
        print()
    if report.findings:
        for finding in report.findings:
            print("FAIL " + finding.render())
        return 1
    print(
        f"identity: {len(report.pairs) // 2} pairs pass in both themes; tokens, templates, roster and marks are well formed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
