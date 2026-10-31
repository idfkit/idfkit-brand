"""Rasters in the standard library: decode PNG to pixels, pack and unpack ICO, compare by pixel.

Two builds of one tag are byte-identical for every SVG, CSS, JSON, JS and HTML file; rasters may
differ by build host (data-model, Derivation rule 2), so `build.py --compare` and assertion 3 of
`check_touchpoint.py` compare them by decoded pixels. Only what `rsvg-convert` writes is decoded:
8-bit, non-interlaced PNG in the greyscale, RGB, greyscale-alpha and RGBA colour types.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Sequence
from dataclasses import dataclass

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}


class RasterError(ValueError):
    """A PNG or ICO this module does not decode."""


@dataclass(frozen=True, slots=True)
class Raster:
    width: int
    height: int
    channels: int
    pixels: bytes

    def pixel(self, x: int, y: int) -> tuple[int, ...]:
        start = (y * self.width + x) * self.channels
        return tuple(self.pixels[start : start + self.channels])


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(data: bytes) -> Raster:
    """The pixels of an 8-bit, non-interlaced PNG, with its filters undone."""
    if not data.startswith(PNG_SIGNATURE):
        raise RasterError("not a PNG")
    offset = len(PNG_SIGNATURE)
    width = height = 0
    bit_depth = color_type = interlace = 0
    idat: list[bytes] = []
    while offset < len(data):
        length, kind = struct.unpack(">I4s", data[offset : offset + 8])
        body = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if bit_depth != 8 or color_type not in _CHANNELS or interlace != 0:
        raise RasterError(f"unsupported PNG: bit depth {bit_depth}, colour type {color_type}, interlace {interlace}")
    channels = _CHANNELS[color_type]
    stride = width * channels
    raw = zlib.decompress(b"".join(idat))
    pixels = bytearray(stride * height)
    previous = bytes(stride)
    for row in range(height):
        start = row * (stride + 1)
        filter_type = raw[start]
        line = bytearray(raw[start + 1 : start + 1 + stride])
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                up_left = previous[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, previous[i], up_left)) & 0xFF
        elif filter_type != 0:
            raise RasterError(f"unknown PNG filter {filter_type}")
        pixels[row * stride : (row + 1) * stride] = line
        previous = bytes(line)
    return Raster(width, height, channels, bytes(pixels))


def png_size(data: bytes) -> tuple[int, int]:
    if not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise RasterError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def pack_ico(frames: Sequence[bytes]) -> bytes:
    """An ICO container holding PNG-compressed frames, which every current browser reads."""
    header = struct.pack("<HHH", 0, 1, len(frames))
    entries = b""
    body = b""
    offset = 6 + 16 * len(frames)
    for frame in frames:
        width, height = png_size(frame)
        entries += struct.pack("<BBBBHHII", width % 256, height % 256, 0, 0, 1, 32, len(frame), offset + len(body))
        body += frame
    return header + entries + body


def unpack_ico(data: bytes) -> list[bytes]:
    _, kind, count = struct.unpack("<HHH", data[:6])
    if kind != 1:
        raise RasterError("not an ICO")
    frames: list[bytes] = []
    for i in range(count):
        size, offset = struct.unpack("<II", data[6 + 16 * i + 8 : 6 + 16 * i + 16])
        frames.append(data[offset : offset + size])
    return frames


@dataclass(frozen=True, slots=True)
class PixelDifference:
    x: int
    y: int
    left: tuple[int, ...]
    right: tuple[int, ...]

    def render(self) -> str:
        return f"pixel ({self.x}, {self.y}) is {self.left} and {self.right}"


def compare_rasters(a: Raster, b: Raster) -> PixelDifference | str | None:
    """None when identical; the first differing pixel; or a sentence when the shapes differ."""
    if (a.width, a.height, a.channels) != (b.width, b.height, b.channels):
        return f"{a.width}x{a.height}x{a.channels} against {b.width}x{b.height}x{b.channels}"
    if a.pixels == b.pixels:
        return None
    step = a.channels
    for i in range(0, len(a.pixels), step):
        if a.pixels[i : i + step] != b.pixels[i : i + step]:
            index = i // step
            return PixelDifference(
                index % a.width, index // a.width, tuple(a.pixels[i : i + step]), tuple(b.pixels[i : i + step])
            )
    return None


def compare_png(a: bytes, b: bytes) -> PixelDifference | str | None:
    return compare_rasters(decode_png(a), decode_png(b))


def compare_ico(a: bytes, b: bytes) -> PixelDifference | str | None:
    frames_a, frames_b = unpack_ico(a), unpack_ico(b)
    if len(frames_a) != len(frames_b):
        return f"{len(frames_a)} frames against {len(frames_b)}"
    for frame_a, frame_b in zip(frames_a, frames_b, strict=True):
        difference = compare_png(frame_a, frame_b)
        if difference is not None:
            return difference
    return None


__all__ = [
    "PixelDifference",
    "Raster",
    "RasterError",
    "compare_ico",
    "compare_png",
    "compare_rasters",
    "decode_png",
    "pack_ico",
    "png_size",
    "unpack_ico",
]
