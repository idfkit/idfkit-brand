"""The mark: the one place its shapes are written.

The geometry is the "Part" mark designed on 2026-10-30 (research R5): on a 48-unit grid, a 32-unit
block with a 12-unit notch cut from its top-right corner, and the piece that fits the notch
displaced 8 units up and 8 units right of it. The body's outer corners are rounded 3 units, the
piece's 2 units, and the notch stays sharp. The ink spans 40 by 40 units, centred.

This module is the record of that geometry and the writer of every SVG master under `marks/`,
except `wordmark.svg`, which is "idfkit" in Inter ExtraBold at -0.035 em, shaped and outlined on
2026-10-30, and is read here, never generated (see `marks/README.md`).

    python mark.py --write      regenerate marks/ from this file
    python mark.py --check      exit 1 if any committed master differs from what this file writes

`build.py` imports the geometry and the lockup functions; nothing else in the standard draws the
mark, and no touchpoint redraws it (plan, Constraints).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

HERE = Path(__file__).resolve().parent
MARKS = HERE / "marks"
WORDMARK_FILE = MARKS / "wordmark.svg"

# 1. The inks a fixed-ink variant uses. These are the two body inks and the dark ground of
# identity.tokens.json (color.primitive.slate-200, slate-950 and navy-950); build.py checks they
# still agree with the token file, so the mark and the standard cannot drift apart.

INK_ON_DARK = "#e2e8f0"
INK_ON_LIGHT = "#0b1020"
TILE_GROUND = "#060a14"
DIVIDER_INK = "#64748b"

# 2. The geometry

MARK_GRID = 48
MARK_BODY = "M4 15a3 3 0 0 1 3-3h17v12h12v17a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3Z"
MARK_PIECE = "M34 4h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"
MARK_INK_MIN = 4
MARK_INK_MAX = 44
PIECE_SIZE = 12
BODY_RADIUS = 3
PIECE_RADIUS = 2

#: The 16-unit redraw with integer edges, for the 16 and 32 px rasters: a 9-unit body, a 3-unit
#: notch, piece and gap. At those sizes the 48-unit geometry lands between pixels and blurs.
SMALL_GRID = 16
SMALL_BODY = "M2 6a1 1 0 0 1 1-1h5v3h3v5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1Z"
SMALL_PIECE = "M11 2h3v3h-3Z"
SMALL_INK_MIN = 2
SMALL_INK_MAX = 14

#: The tile: the mark reversed out of the navy ground, 512 units, corners at 22 percent.
TILE_SIZE = 512
TILE_RADIUS_FRACTION = 0.22
#: The share of the tile's side the mark's ink spans; 0.56 keeps it inside the 80 percent safe zone
#: of a maskable icon.
TILE_INK_FRACTION = 0.56
SMALL_TILE_RADIUS = 3.5

#: The lockup: the mark's ink scaled to 80 units, on the wordmark's baseline, gap 0.3 of the height.
LOCKUP_MARK_HEIGHT = 80.0
LOCKUP_GAP_FRACTION = 0.3
#: The property lockup: a 1-unit divider in the muted ink, as tall as the x-height, then the name
#: in the label face at medium weight (research R7).
DIVIDER_WIDTH = 1.0
LABEL_FAMILY = "JetBrains Mono"
LABEL_WEIGHT = 500
#: The wordmark's x-height as a fraction of the lockup's mark height: Inter's x-height is 0.546 em
#: and the outlined wordmark sits at about 103 units per em when the mark is 80 tall.
X_HEIGHT_FRACTION = 0.70
#: JetBrains Mono's x-height as a fraction of its em (550 of 1000 units), which sets the label size.
LABEL_X_HEIGHT_FRACTION = 0.55

#: Clear space on every side is the piece's width, 0.3 of the ink height; minimum size 16 px;
#: below 24 px the tile stands in for the bare mark.
CLEAR_SPACE_FRACTION = PIECE_SIZE / (MARK_INK_MAX - MARK_INK_MIN)
MIN_SIZE_PX = 16
TILE_BELOW_PX = 24


@dataclass(frozen=True, slots=True)
class Mark:
    """The mark's paths and ink extents on its grid."""

    body: str = MARK_BODY
    piece: str = MARK_PIECE
    grid: int = MARK_GRID
    ink_min: int = MARK_INK_MIN
    ink_max: int = MARK_INK_MAX

    @property
    def ink(self) -> int:
        return self.ink_max - self.ink_min

    def paths(self, fill: str) -> str:
        return f'<path fill="{fill}" d="{self.body}"/><path fill="{fill}" d="{self.piece}"/>'


MARK = Mark()
SMALL_MARK = Mark(body=SMALL_BODY, piece=SMALL_PIECE, grid=SMALL_GRID, ink_min=SMALL_INK_MIN, ink_max=SMALL_INK_MAX)


@dataclass(frozen=True, slots=True)
class Wordmark:
    """The outlined wordmark's path data and metrics, read from `marks/wordmark.svg`."""

    path: str
    transform: str
    width: float
    height: float
    baseline: float


def read_wordmark(path: Path = WORDMARK_FILE) -> Wordmark:
    text = path.read_text(encoding="utf-8")
    view_box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', text)
    baseline = re.search(r'data-baseline="([\d.]+)"', text)
    transform = re.search(r'transform="([^"]+)"', text)
    data = re.search(r' d="([^"]+)"', text)
    if not (view_box and baseline and transform and data):
        raise SystemExit(f"{path} does not carry the expected viewBox, data-baseline, transform and path")
    return Wordmark(
        path=data.group(1),
        transform=transform.group(1),
        width=float(view_box.group(1)),
        height=float(view_box.group(2)),
        baseline=float(baseline.group(1)),
    )


# 3. SVG writers. Every writer returns a complete document ending in one newline, so that the
# committed masters are byte-reproducible.

SVG_NS = 'xmlns="http://www.w3.org/2000/svg"'


def svg_mark(fill: str, mark: Mark = MARK) -> str:
    return (
        f'<svg {SVG_NS} viewBox="0 0 {mark.grid} {mark.grid}" role="img" aria-label="idfkit">{mark.paths(fill)}</svg>\n'
    )


def svg_tile(
    size: int = TILE_SIZE, radius: float | None = None, ground: str = TILE_GROUND, ink: str = INK_ON_DARK
) -> str:
    """The mark reversed out of the navy tile, for icons and favicons; `radius` 0 gives full bleed."""
    r = size * TILE_RADIUS_FRACTION if radius is None else radius
    scale = size * TILE_INK_FRACTION / MARK.ink
    box = MARK.grid * scale
    offset = (size - box) / 2
    return (
        f'<svg {SVG_NS} viewBox="0 0 {size} {size}" role="img" aria-label="idfkit">'
        f'<rect width="{size}" height="{size}" rx="{r:g}" fill="{ground}"/>'
        f'<g transform="translate({offset:.2f} {offset:.2f}) scale({scale:.4f})">{MARK.paths(ink)}</g>'
        "</svg>\n"
    )


def svg_small_tile(ground: str = TILE_GROUND, ink: str = INK_ON_DARK) -> str:
    """The tile on the 16-unit grid, whole pixels at 16 and 32 px."""
    return (
        f'<svg {SVG_NS} viewBox="0 0 {SMALL_GRID} {SMALL_GRID}" role="img" aria-label="idfkit">'
        f'<rect width="{SMALL_GRID}" height="{SMALL_GRID}" rx="{SMALL_TILE_RADIUS:g}" fill="{ground}"/>'
        f"{SMALL_MARK.paths(ink)}</svg>\n"
    )


@dataclass(frozen=True, slots=True)
class LockupGeometry:
    """Where the parts of a lockup sit, in lockup units (the mark's ink is 80 tall)."""

    scale: float
    mark_offset: float
    word_x: float
    word_y: float
    width: float
    height: float
    baseline: float


def lockup_geometry(word: Wordmark) -> LockupGeometry:
    scale = LOCKUP_MARK_HEIGHT / MARK.ink
    gap = LOCKUP_GAP_FRACTION * LOCKUP_MARK_HEIGHT
    word_x = LOCKUP_MARK_HEIGHT + gap
    word_y = LOCKUP_MARK_HEIGHT - word.baseline
    return LockupGeometry(
        scale=scale,
        mark_offset=-MARK.ink_min * scale,
        word_x=word_x,
        word_y=word_y,
        width=word_x + word.width,
        height=max(LOCKUP_MARK_HEIGHT, word_y + word.height),
        baseline=LOCKUP_MARK_HEIGHT,
    )


def lockup_parts(fill: str, word: Wordmark) -> tuple[str, LockupGeometry]:
    """The mark and wordmark groups of a lockup, without the enclosing `<svg>`."""
    geometry = lockup_geometry(word)
    parts = (
        f'<g transform="translate({geometry.mark_offset:.2f} {geometry.mark_offset:.2f}) scale({geometry.scale:.4f})">{MARK.paths(fill)}</g>'
        f'<g transform="translate({geometry.word_x:.2f} {geometry.word_y:.2f})">'
        f'<path fill="{fill}" transform="{word.transform}" d="{word.path}"/></g>'
    )
    return parts, geometry


def svg_lockup(fill: str, word: Wordmark) -> str:
    """Mark and wordmark side by side, cropped to the ink."""
    parts, g = lockup_parts(fill, word)
    return f'<svg {SVG_NS} viewBox="0 0 {g.width:.2f} {g.height:.2f}" role="img" aria-label="idfkit">{parts}</svg>\n'


class LabelOutline(Protocol):
    """A line of text set as a path, as `tools/glyphs.py` produces; `mark.py` itself draws no text."""

    def width(self, size: float) -> float: ...

    def svg(self, x: float, baseline_y: float, size: float, fill: str) -> str: ...


@dataclass(frozen=True, slots=True)
class PropertyLockup:
    """The markup of a property lockup without its enclosing `<svg>`, and its extent."""

    markup: str
    width: float
    height: float


def property_lockup_parts(
    fill: str,
    name: str,
    word: Wordmark,
    label: LabelOutline | None = None,
    divider: str = DIVIDER_INK,
    label_fill: str | None = None,
) -> PropertyLockup:
    """The lockup, a divider, and the property name in the label face (FR-012, research R7).

    The x-height-tall divider sits on the baseline; the name is set at the size that gives the
    label face the wordmark's x-height. With `label`, the name is an outlined path from the
    standard's own font files, so a raster of it is the same on every host; without one, it is
    `<text>` in the label face, for a touchpoint that renders it with the vendored fonts.
    """
    parts, g = lockup_parts(fill, word)
    x_height = LOCKUP_MARK_HEIGHT * X_HEIGHT_FRACTION
    gap = LOCKUP_GAP_FRACTION * LOCKUP_MARK_HEIGHT
    divider_x = g.width + gap
    font_size = x_height / LABEL_X_HEIGHT_FRACTION
    label_x = divider_x + DIVIDER_WIDTH + gap
    text_fill = label_fill or fill
    if label is None:
        label_markup = (
            f'<text x="{label_x:.2f}" y="{g.baseline:.2f}" font-family="{LABEL_FAMILY}" font-weight="{LABEL_WEIGHT}" '
            f'font-size="{font_size:.2f}" fill="{text_fill}">{name}</text>'
        )
        label_width = len(name) * font_size * 0.6
    else:
        label_markup = label.svg(label_x, g.baseline, font_size, text_fill)
        label_width = label.width(font_size)
    markup = (
        f"{parts}"
        f'<rect x="{divider_x:.2f}" y="{g.baseline - x_height:.2f}" width="{DIVIDER_WIDTH:g}" height="{x_height:.2f}" fill="{divider}"/>'
        f"{label_markup}"
    )
    return PropertyLockup(markup=markup, width=label_x + label_width, height=g.height)


def svg_property_lockup(
    fill: str,
    name: str,
    word: Wordmark,
    label: LabelOutline | None = None,
    divider: str = DIVIDER_INK,
    label_fill: str | None = None,
) -> str:
    lockup = property_lockup_parts(fill, name, word, label, divider, label_fill)
    return (
        f'<svg {SVG_NS} viewBox="0 0 {lockup.width:.2f} {lockup.height:.2f}" role="img" aria-label="idfkit {name}">'
        f"{lockup.markup}</svg>\n"
    )


# 4. The masters


def masters(word: Wordmark | None = None) -> dict[str, str]:
    """Every file `--write` produces under `marks/`, by name (data-model, Mark variants)."""
    word = word or read_wordmark()
    return {
        "mark.svg": svg_mark("currentColor"),
        "mark-on-light.svg": svg_mark(INK_ON_LIGHT),
        "mark-on-dark.svg": svg_mark(INK_ON_DARK),
        "mark-small.svg": svg_mark("currentColor", SMALL_MARK),
        "tile.svg": svg_tile(),
        "lockup.svg": svg_lockup("currentColor", word),
        "lockup-on-light.svg": svg_lockup(INK_ON_LIGHT, word),
        "lockup-on-dark.svg": svg_lockup(INK_ON_DARK, word),
    }


MASTER_NAMES: tuple[str, ...] = (
    "mark.svg",
    "mark-on-light.svg",
    "mark-on-dark.svg",
    "mark-small.svg",
    "tile.svg",
    "lockup.svg",
    "lockup-on-light.svg",
    "lockup-on-dark.svg",
)


def write(directory: Path = MARKS) -> list[Path]:
    written: list[Path] = []
    for name, text in masters(read_wordmark(directory / "wordmark.svg")).items():
        target = directory / name
        target.write_text(text, encoding="utf-8")
        written.append(target)
    return written


def check(directory: Path = MARKS) -> list[str]:
    """Names of the masters that differ from this file's output, or are missing."""
    differing: list[str] = []
    for name, text in masters(read_wordmark(directory / "wordmark.svg")).items():
        target = directory / name
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            differing.append(name)
    return differing


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The mark: write or check the SVG masters under marks/.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", nargs="?", const=str(MARKS), metavar="DIR", help="write the masters (default marks/)")
    group.add_argument(
        "--check", action="store_true", help="exit 1 if a committed master differs from this file's output"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.check:
        differing = check()
        if differing:
            print(
                "marks/ differs from mark.py for: "
                + ", ".join(differing)
                + ". Run `python mark.py --write` and commit the result."
            )
            return 1
        print(f"marks/: {len(MASTER_NAMES)} masters match mark.py")
        return 0
    for path in write(Path(args.write)):
        print("wrote", path.relative_to(HERE) if path.is_relative_to(HERE) else path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
