"""mark.py writes exactly the masters, the committed masters match, and --check catches an edit (T014)."""

from __future__ import annotations

from pathlib import Path

import mark


def test_write_produces_exactly_the_variants(tmp_path: Path, root: Path) -> None:
    (tmp_path / "wordmark.svg").write_bytes((root / "marks" / "wordmark.svg").read_bytes())
    written = mark.write(tmp_path)
    assert sorted(p.name for p in written) == sorted(mark.MASTER_NAMES)
    assert sorted(mark.MASTER_NAMES) == sorted([
        "mark.svg",
        "mark-on-light.svg",
        "mark-on-dark.svg",
        "mark-small.svg",
        "tile.svg",
        "lockup.svg",
        "lockup-on-light.svg",
        "lockup-on-dark.svg",
    ])


def test_output_equals_the_committed_masters(root: Path) -> None:
    assert mark.check(root / "marks") == []
    for name, text in mark.masters().items():
        assert (root / "marks" / name).read_text(encoding="utf-8") == text


def test_check_fails_when_a_master_is_edited(standard_copy: Path) -> None:
    target = standard_copy / "marks" / "mark-on-dark.svg"
    target.write_text(target.read_text(encoding="utf-8").replace("#e2e8f0", "#e2e8f1"), encoding="utf-8")
    assert mark.check(standard_copy / "marks") == ["mark-on-dark.svg"]
    assert mark.main(["--check"]) == 0  # the repository's own masters still match


def test_geometry_is_the_recorded_mark() -> None:
    assert mark.MARK.grid == 48
    assert mark.MARK.ink == 40
    assert mark.PIECE_SIZE == 12
    assert mark.CLEAR_SPACE_FRACTION == 0.3
    assert mark.MIN_SIZE_PX == 16
    assert mark.TILE_RADIUS_FRACTION == 0.22
    assert mark.LOCKUP_MARK_HEIGHT == 80 and mark.LOCKUP_GAP_FRACTION == 0.3


def test_the_mark_is_one_colour_and_currentcolor() -> None:
    svg = mark.svg_mark("currentColor")
    assert svg.count("currentColor") == 2
    assert "#" not in svg
    assert "stroke" not in svg
    assert svg.endswith("\n")


def test_the_property_lockup_sets_the_name_in_the_label_face() -> None:
    svg = mark.svg_property_lockup(mark.INK_ON_DARK, "Developers", mark.read_wordmark())
    assert 'font-family="JetBrains Mono"' in svg
    assert 'font-weight="500"' in svg
    assert ">Developers</text>" in svg
    assert f'fill="{mark.DIVIDER_INK}"' in svg
    assert 'aria-label="idfkit Developers"' in svg


def test_the_property_lockup_leaves_room_for_descenders(root: Path) -> None:
    from glyphs import Font

    label = Font.load(root / "fonts" / "build" / "jetbrains-mono-500.ttf").run("Envelop")
    lockup = mark.property_lockup_parts(mark.INK_ON_DARK, "Envelop", mark.read_wordmark(), label)
    plain = mark.lockup_geometry(mark.read_wordmark())
    assert lockup.height > plain.baseline, "the p of Envelop reaches below the baseline"
    svg = mark.svg_property_lockup(mark.INK_ON_DARK, "Envelop", mark.read_wordmark(), label)
    assert f'viewBox="0 0 {lockup.width:.2f} {lockup.height:.2f}"' in svg


def test_the_word_space_in_a_property_name_is_narrowed(root: Path) -> None:
    from glyphs import Font

    font = Font.load(root / "fonts" / "build" / "jetbrains-mono-500.ttf")
    full = font.run("EnergyPlus docs")
    narrowed = font.run("EnergyPlus docs", space_em=mark.LABEL_SPACE_EM)
    cell = font.advance(font.glyph_id(" "))
    assert narrowed.advance == full.advance - (cell - mark.LABEL_SPACE_EM * font.units_per_em)
    assert mark.LABEL_SPACE_EM < 0.6
