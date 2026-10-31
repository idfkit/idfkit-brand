"""Set text as outlines, from the standard's own TrueType subsets, in the standard library.

The social images carry a property name and a repository sentence. Rendering them as `<text>`
would make every raster depend on which fonts the build host has installed, and on which font
backend its `rsvg-convert` uses. Instead the build reads the glyph outlines out of `fonts/build/`
(the same Latin subsets the touchpoints ship as woff2, kept as TTF for this reader) and writes
them as paths, so that a social image rasterizes the same way on every host and no touchpoint
ever sees a fallback face in a picture.

Supported: TrueType outlines (`glyf`), simple and composite glyphs, `cmap` formats 4 and 12,
horizontal advances. Not supported: kerning, which the label face does not have and the text face
can do without in a single line of 34 px type.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import cache
from pathlib import Path


class FontError(ValueError):
    """A font file this module does not read."""


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    on_curve: bool


@dataclass(frozen=True, slots=True)
class TextRun:
    """One line of text set as a path, in font units with y up; scale with `transform`."""

    path: str
    advance: float
    units_per_em: int
    descender: int = 0

    def width(self, size: float) -> float:
        return self.advance * size / self.units_per_em

    def descent(self, size: float) -> float:
        """How far below the baseline the face reaches at `size`, as a positive distance."""
        return abs(self.descender) * size / self.units_per_em

    def transform(self, x: float, baseline_y: float, size: float) -> str:
        s = size / self.units_per_em
        return f"translate({x:.2f} {baseline_y:.2f}) scale({s:.6f} {-s:.6f})"

    def svg(self, x: float, baseline_y: float, size: float, fill: str) -> str:
        return f'<g transform="{self.transform(x, baseline_y, size)}"><path fill="{fill}" d="{self.path}"/></g>'


class Font:
    """A TrueType font read for its outlines and advances."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.tables = self._directory()
        head = self._table("head")
        self.units_per_em: int = struct.unpack(">H", head[18:20])[0]
        self.index_to_loc_format: int = struct.unpack(">h", head[50:52])[0]
        maxp = self._table("maxp")
        self.glyph_count: int = struct.unpack(">H", maxp[4:6])[0]
        hhea = self._table("hhea")
        self.ascender: int = struct.unpack(">h", hhea[4:6])[0]
        self.descender: int = struct.unpack(">h", hhea[6:8])[0]
        self.metric_count: int = struct.unpack(">H", hhea[34:36])[0]
        self.hmtx = self._table("hmtx")
        self.loca = self._table("loca")
        self.glyf = self._table("glyf")
        os2 = self.tables.get("OS/2")
        self.x_height: int = (
            struct.unpack(">h", self._table("OS/2")[86:88])[0]
            if os2 and len(self._table("OS/2")) >= 88
            else int(self.units_per_em * 0.52)
        )
        self.cap_height: int = (
            struct.unpack(">h", self._table("OS/2")[88:90])[0]
            if os2 and len(self._table("OS/2")) >= 90
            else int(self.units_per_em * 0.7)
        )
        self.cmap = self._read_cmap()

    @classmethod
    @cache
    def load(cls, path: Path) -> Font:
        return cls(path.read_bytes())

    # 1. Tables

    def _directory(self) -> dict[str, tuple[int, int]]:
        count = struct.unpack(">H", self.data[4:6])[0]
        tables: dict[str, tuple[int, int]] = {}
        for i in range(count):
            tag, _, offset, length = struct.unpack(">4sIII", self.data[12 + 16 * i : 28 + 16 * i])
            tables[tag.decode("latin-1")] = (offset, length)
        if "glyf" not in tables:
            raise FontError("no glyf table: only TrueType outlines are read")
        return tables

    def _table(self, tag: str) -> bytes:
        if tag not in self.tables:
            raise FontError(f"no {tag} table")
        offset, length = self.tables[tag]
        return self.data[offset : offset + length]

    def _read_cmap(self) -> dict[int, int]:
        table = self._table("cmap")
        count = struct.unpack(">H", table[2:4])[0]
        chosen: dict[int, int] = {}
        for i in range(count):
            platform, encoding, offset = struct.unpack(">HHI", table[4 + 8 * i : 12 + 8 * i])
            fmt = struct.unpack(">H", table[offset : offset + 2])[0]
            if fmt == 12 and (platform, encoding) in ((3, 10), (0, 4), (0, 6)):
                return self._cmap12(table, offset)
            if fmt == 4 and (platform, encoding) in ((3, 1), (0, 3), (0, 4)) and not chosen:
                chosen = self._cmap4(table, offset)
        if not chosen:
            raise FontError("no usable cmap subtable")
        return chosen

    @staticmethod
    def _cmap4(table: bytes, offset: int) -> dict[int, int]:
        seg_count = struct.unpack(">H", table[offset + 6 : offset + 8])[0] // 2
        ends = struct.unpack(f">{seg_count}H", table[offset + 14 : offset + 14 + 2 * seg_count])
        base = offset + 16 + 2 * seg_count
        starts = struct.unpack(f">{seg_count}H", table[base : base + 2 * seg_count])
        base += 2 * seg_count
        deltas = struct.unpack(f">{seg_count}h", table[base : base + 2 * seg_count])
        base += 2 * seg_count
        range_offsets_at = base
        range_offsets = struct.unpack(f">{seg_count}H", table[base : base + 2 * seg_count])
        mapping: dict[int, int] = {}
        for i in range(seg_count):
            for code in range(starts[i], min(ends[i], 0xFFFE) + 1):
                if range_offsets[i] == 0:
                    glyph = (code + deltas[i]) & 0xFFFF
                else:
                    address = range_offsets_at + 2 * i + range_offsets[i] + 2 * (code - starts[i])
                    glyph = struct.unpack(">H", table[address : address + 2])[0]
                    if glyph:
                        glyph = (glyph + deltas[i]) & 0xFFFF
                if glyph:
                    mapping[code] = glyph
        return mapping

    @staticmethod
    def _cmap12(table: bytes, offset: int) -> dict[int, int]:
        group_count = struct.unpack(">I", table[offset + 12 : offset + 16])[0]
        mapping: dict[int, int] = {}
        for i in range(group_count):
            start, end, glyph = struct.unpack(">III", table[offset + 16 + 12 * i : offset + 28 + 12 * i])
            for code in range(start, end + 1):
                mapping[code] = glyph + (code - start)
        return mapping

    # 2. Metrics and outlines

    def glyph_id(self, char: str) -> int:
        return self.cmap.get(ord(char), 0)

    def advance(self, glyph: int) -> int:
        index = min(glyph, self.metric_count - 1)
        return struct.unpack(">H", self.hmtx[4 * index : 4 * index + 2])[0]

    def _glyph_bytes(self, glyph: int) -> bytes:
        if self.index_to_loc_format == 0:
            start, end = (2 * v for v in struct.unpack(">HH", self.loca[2 * glyph : 2 * glyph + 4]))
        else:
            start, end = struct.unpack(">II", self.loca[4 * glyph : 4 * glyph + 8])
        return self.glyf[start:end]

    def contours(self, glyph: int) -> list[list[Point]]:
        data = self._glyph_bytes(glyph)
        if not data:
            return []
        contour_count = struct.unpack(">h", data[:2])[0]
        if contour_count < 0:
            return self._composite(data)
        return self._simple(data, contour_count)

    @staticmethod
    def _simple(data: bytes, contour_count: int) -> list[list[Point]]:
        end_points = struct.unpack(f">{contour_count}H", data[10 : 10 + 2 * contour_count])
        point_count = end_points[-1] + 1 if contour_count else 0
        offset = 10 + 2 * contour_count
        instruction_length = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += 2 + instruction_length
        flags: list[int] = []
        while len(flags) < point_count:
            flag = data[offset]
            offset += 1
            flags.append(flag)
            if flag & 0x08:
                repeat = data[offset]
                offset += 1
                flags.extend([flag] * repeat)
        xs: list[int] = []
        value = 0
        for flag in flags:
            if flag & 0x02:
                delta = data[offset]
                offset += 1
                value += delta if flag & 0x10 else -delta
            elif not flag & 0x10:
                value += struct.unpack(">h", data[offset : offset + 2])[0]
                offset += 2
            xs.append(value)
        ys: list[int] = []
        value = 0
        for flag in flags:
            if flag & 0x04:
                delta = data[offset]
                offset += 1
                value += delta if flag & 0x20 else -delta
            elif not flag & 0x20:
                value += struct.unpack(">h", data[offset : offset + 2])[0]
                offset += 2
            ys.append(value)
        contours: list[list[Point]] = []
        start = 0
        for end in end_points:
            contours.append([Point(xs[i], ys[i], bool(flags[i] & 0x01)) for i in range(start, end + 1)])
            start = end + 1
        return contours

    def _composite(self, data: bytes) -> list[list[Point]]:
        offset = 10
        contours: list[list[Point]] = []
        while True:
            flags, glyph = struct.unpack(">HH", data[offset : offset + 4])
            offset += 4
            if flags & 0x0001:
                dx, dy = struct.unpack(">hh", data[offset : offset + 4])
                offset += 4
            else:
                dx, dy = struct.unpack(">bb", data[offset : offset + 2])
                offset += 2
            a, b, c, d = 1.0, 0.0, 0.0, 1.0
            if flags & 0x0008:
                a = d = _f2dot14(data, offset)
                offset += 2
            elif flags & 0x0040:
                a, d = _f2dot14(data, offset), _f2dot14(data, offset + 2)
                offset += 4
            elif flags & 0x0080:
                a, b, c, d = (_f2dot14(data, offset + 2 * i) for i in range(4))
                offset += 8
            if not flags & 0x0002:
                dx, dy = 0, 0  # point matching is not used by these fonts' composites
            for contour in self.contours(glyph):
                contours.append([Point(a * p.x + c * p.y + dx, b * p.x + d * p.y + dy, p.on_curve) for p in contour])
            if not flags & 0x0020:
                break
        return contours

    # 3. Text

    def run(self, text: str, tracking_em: float = 0.0) -> TextRun:
        """`text` on one line as a path in font units, with optional tracking in em."""
        parts: list[str] = []
        x = 0.0
        tracking = tracking_em * self.units_per_em
        for char in text:
            glyph = self.glyph_id(char)
            for contour in self.contours(glyph):
                parts.append(contour_path(contour, x))
            x += self.advance(glyph) + tracking
        return TextRun(
            path="".join(parts), advance=x - tracking, units_per_em=self.units_per_em, descender=self.descender
        )

    def measure(self, text: str) -> float:
        return sum(self.advance(self.glyph_id(c)) for c in text)


def _f2dot14(data: bytes, offset: int) -> float:
    return struct.unpack(">h", data[offset : offset + 2])[0] / 16384


def _fmt(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".") if value != int(value) else str(int(value))


def contour_path(points: list[Point], dx: float = 0.0) -> str:
    """One TrueType contour (quadratic, with implied on-curve midpoints) as SVG path data."""
    if not points:
        return ""
    pts = [Point(p.x + dx, p.y, p.on_curve) for p in points]
    first_on = next((i for i, p in enumerate(pts) if p.on_curve), None)
    if first_on is None:
        mid = Point((pts[0].x + pts[-1].x) / 2, (pts[0].y + pts[-1].y) / 2, True)
        pts = [mid, *pts]
        first_on = 0
    pts = pts[first_on:] + pts[:first_on]
    d = [f"M{_fmt(pts[0].x)} {_fmt(pts[0].y)}"]
    control: Point | None = None
    for p in [*pts[1:], pts[0]]:
        if p.on_curve:
            if control is None:
                d.append(f"L{_fmt(p.x)} {_fmt(p.y)}")
            else:
                d.append(f"Q{_fmt(control.x)} {_fmt(control.y)} {_fmt(p.x)} {_fmt(p.y)}")
                control = None
        else:
            if control is not None:
                mx, my = (control.x + p.x) / 2, (control.y + p.y) / 2
                d.append(f"Q{_fmt(control.x)} {_fmt(control.y)} {_fmt(mx)} {_fmt(my)}")
            control = p
    d.append("Z")
    return "".join(d)


def wrap(font: Font, text: str, size: float, max_width: float) -> list[str]:
    """Greedy line breaking on spaces by measured advance."""
    lines: list[str] = []
    current: list[str] = []
    for word in text.split():
        candidate = " ".join([*current, word])
        if current and font.measure(candidate) * size / font.units_per_em > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


__all__ = ["Font", "FontError", "Point", "TextRun", "contour_path", "wrap"]
