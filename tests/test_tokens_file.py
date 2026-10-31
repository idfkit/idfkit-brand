"""The token file has the restricted shape of contracts/identity-standard.md section 2 (T010)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from models import ALIAS_PATTERN, HEX_PATTERN, THEMES, TOKEN_GROUPS, ColorValue, ShapeError, load_tokens


@pytest.fixture(scope="module")
def document(root: Path) -> dict[str, object]:
    return json.loads((root / "identity.tokens.json").read_text(encoding="utf-8"))


def test_only_the_six_groups(document: dict[str, object]) -> None:
    groups = [key for key in document if not key.startswith("$")]
    assert groups == list(TOKEN_GROUPS)


def test_every_token_loads_and_carries_a_usage(root: Path) -> None:
    tokens = load_tokens(root / "identity.tokens.json")
    assert len(tokens.tokens) > 40
    for token in tokens:
        assert token.description.strip(), token.name


def test_roles_are_aliases_and_primitives_are_hex(root: Path) -> None:
    tokens = load_tokens(root / "identity.tokens.json")
    roles = tokens.colors("role")
    primitives = tokens.colors("primitive")
    assert roles and primitives
    for token in roles:
        assert isinstance(token.value, ColorValue)
        for theme in THEMES:
            assert ALIAS_PATTERN.match(token.value.for_theme(theme)), token.name
            assert tokens.resolve(token.name, theme).startswith("#")
    for token in primitives:
        assert isinstance(token.value, ColorValue)
        for theme in THEMES:
            assert HEX_PATTERN.match(token.value.for_theme(theme)), token.name


def test_every_ink_role_carries_a_threshold_and_its_grounds(root: Path) -> None:
    tokens = load_tokens(root / "identity.tokens.json")
    inks = [
        t
        for t in tokens.colors("role")
        if t.name.split(".")[-1].startswith(("ink", "accent", "link", "focus")) or ".status." in t.name
    ]
    assert inks
    for token in inks:
        assert token.min_contrast in (4.5, 3), token.name
        assert token.on, token.name
        for ground in token.on:
            assert f"color.role.{ground}" in tokens.tokens, f"{token.name} sits on an unknown ground {ground}"


def test_the_light_accent_is_the_darker_step(root: Path) -> None:
    tokens = load_tokens(root / "identity.tokens.json")
    assert tokens.resolve("color.role.accent", "light") == "#2563eb"
    assert tokens.resolve("color.role.accent", "dark") == "#3b82f6"
    assert tokens.get("color.role.ink-label").min_contrast == 3


def test_both_theme_keys_on_every_primitive(document: dict[str, object]) -> None:
    color = document["color"]
    assert isinstance(color, dict)
    for name, raw in color["primitive"].items():
        if name.startswith("$"):
            continue
        assert set(raw["$value"]) == set(THEMES), name


def test_the_file_names_no_touchpoint_or_path(root: Path) -> None:
    text = (root / "identity.tokens.json").read_text(encoding="utf-8")
    for forbidden in (
        "idfkit.com",
        "developers.",
        "docs.idfkit",
        "app.idfkit",
        "auth.idfkit",
        "mcp.idfkit",
        "shoebox",
        "mkdocs",
        "stytch",
        "envelop",
        ".css",
        ".svg",
        "dist/",
    ):
        assert forbidden not in text.lower(), forbidden
    assert not re.search(r"\b[a-z_]+/[a-z_./]+\b", text.replace("https://", "")), "a path"


def test_font_group_holds_families_stacks_and_weights(root: Path) -> None:
    tokens = load_tokens(root / "identity.tokens.json")
    assert tokens.get("font.family.text").value == "Inter"
    assert tokens.get("font.family.code").value == "JetBrains Mono"
    assert isinstance(tokens.get("font.stack.text").value, tuple)
    weights = {t.name.split(".")[-1]: t for t in tokens if t.name.startswith("font.weight.")}
    assert {int(str(w.value)) for w in weights.values() if "text" in w.families} == {400, 500, 600, 700, 800}
    assert {int(str(w.value)) for w in weights.values() if "code" in w.families} == {400, 500}


@pytest.mark.parametrize(
    ("mutation", "key"),
    [
        (
            lambda d: d.__setitem__("layout", {"x": {"$type": "dimension", "$value": "1px", "$description": "x"}}),
            "layout",
        ),
        (lambda d: d["color"]["role"]["accent"]["$value"].__setitem__("light", "#2563eb"), "color.role.accent"),
        (lambda d: d["color"]["primitive"]["white"]["$value"].pop("dark"), "color.primitive.white"),
        (lambda d: d["color"]["role"]["ink"].pop("$description"), "color.role.ink"),
        (lambda d: d["color"]["role"]["ink"]["$extensions"]["idfkit"].pop("on"), "color.role.ink"),
    ],
)
def test_shape_violations_name_their_key(
    tmp_path: Path, root: Path, mutation: Callable[[dict[str, Any]], object], key: str
) -> None:
    document = json.loads((root / "identity.tokens.json").read_text(encoding="utf-8"))
    mutation(document)
    path = tmp_path / "identity.tokens.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ShapeError) as error:
        load_tokens(path)
    assert error.value.key == key
