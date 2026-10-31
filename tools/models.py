"""Typed records for the token file and the roster.

Every model in this repository is a frozen dataclass with the fields of data-model.md; nothing
downstream reads a raw dictionary. The two readers at the bottom, `load_tokens` and `load_roster`,
are the only places the JSON and TOML shapes are interpreted, and both raise `ShapeError` naming
the key that violated the contract (`contracts/identity-standard.md` section 2 and
`contracts/touchpoint-check.md` section 1).
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ThemeId = Literal["light", "dark"]
THEMES: tuple[ThemeId, ...] = ("light", "dark")

#: The only groups the token file may carry (contract section 2).
TOKEN_GROUPS: tuple[str, ...] = ("color", "font", "space", "radius", "elevation", "motion")
#: The DTCG types the standard uses (data-model, Token).
TOKEN_TYPES: tuple[str, ...] = ("color", "dimension", "fontFamily", "fontWeight", "duration", "cubicBezier", "shadow")
#: Mechanisms `contracts/derivations.md` defines; a roster entry may name no other.
MECHANISMS: tuple[str, ...] = ("css", "material", "envelop", "stytch", "hero", "readme")
DECLARATION_FORMS: tuple[str, ...] = ("toml-key", "json-pointer", "image-url")
README_KINDS: tuple[str, ...] = ("library", "service", "site", "plugin", "profile")
TOUCHPOINT_KINDS: tuple[str, ...] = ("host", "readme")
LAG_KINDS: tuple[str, ...] = ("not-yet", "deliberate")
#: Hosts no touchpoint may link (FR-021).
RETIRED_HOSTS: tuple[str, ...] = ("py.idfkit.com", "js.idfkit.com")
#: Words that make an exception's reason a lag in disguise (contract section 6).
LAG_WORDS: tuple[str, ...] = ("yet", "later", "todo")

LEVEL_PATTERN = re.compile(r"^identity-[0-9]{4}\.[0-9]+$")
HEX_PATTERN = re.compile(r"^#[0-9a-f]{6}$")
ALIAS_PATTERN = re.compile(r"^\{([a-z0-9.-]+)\}$")


class ShapeError(ValueError):
    """A token file or roster that does not have the shape the contract gives it.

    `key` is the dotted path (tokens) or the TOML path (roster) of the offending entry, so that the
    validator can name it.
    """

    def __init__(self, key: str, message: str) -> None:
        super().__init__(f"{key}: {message}")
        self.key = key
        self.message = message


# 1. Tokens


@dataclass(frozen=True, slots=True)
class ColorValue:
    """A colour token's value: one hex string or alias per theme."""

    light: str
    dark: str

    def for_theme(self, theme: ThemeId) -> str:
        return self.light if theme == "light" else self.dark


@dataclass(frozen=True, slots=True)
class Shadow:
    """One box shadow, the DTCG shadow shape with an 8-digit hex colour."""

    color: str
    offset_x: str
    offset_y: str
    blur: str
    spread: str

    def css(self) -> str:
        return f"{self.offset_x} {self.offset_y} {self.blur} {self.spread} {self.color}"


@dataclass(frozen=True, slots=True)
class Token:
    """A named identity value (data-model, Token).

    `value` is a `ColorValue` for colours (hex on a primitive, an alias on a role), a string for
    dimensions and durations, a tuple of strings for a font stack, an int for a weight, a tuple of
    floats for an easing, and a per-theme mapping of `Shadow` for an elevation.
    """

    name: str
    type: str
    value: ColorValue | str | int | tuple[str, ...] | tuple[float, ...] | Mapping[ThemeId, Shadow]
    description: str
    tier: Literal["primitive", "role"] | None = None
    min_contrast: float | None = None
    on: tuple[str, ...] = ()
    families: tuple[str, ...] = ()

    @property
    def group(self) -> str:
        return self.name.split(".", 1)[0]

    @property
    def css_name(self) -> str:
        """`--idfkit-<group>-<name>`; a role drops its `role` segment, a primitive keeps `primitive`."""
        parts = self.name.split(".")
        if self.tier == "role":
            parts = [parts[0], *parts[2:]]
        return "--idfkit-" + "-".join(parts)


@dataclass(frozen=True, slots=True)
class Pair:
    """A foreground and a ground the standard says may be used together (FR-015)."""

    foreground: str
    background: str
    threshold: float


@dataclass(frozen=True, slots=True)
class TokenFile:
    """The parsed token file: every token by dotted name, in file order."""

    path: Path
    tokens: Mapping[str, Token]

    def __iter__(self) -> Iterator[Token]:
        return iter(self.tokens.values())

    def get(self, name: str) -> Token:
        try:
            return self.tokens[name]
        except KeyError:
            raise ShapeError(name, "no such token") from None

    def colors(self, tier: Literal["primitive", "role"] | None = None) -> list[Token]:
        return [t for t in self if t.type == "color" and (tier is None or t.tier == tier)]

    def resolve(self, name: str, theme: ThemeId) -> str:
        """The hex value a colour token has in `theme`, following one alias if it is a role."""
        token = self.get(name)
        if not isinstance(token.value, ColorValue):
            raise ShapeError(name, "not a colour token")
        raw = token.value.for_theme(theme)
        alias = ALIAS_PATTERN.match(raw)
        if alias is None:
            return raw
        target = self.get(alias.group(1))
        if not isinstance(target.value, ColorValue):
            raise ShapeError(name, f"aliases {alias.group(1)}, which is not a colour")
        resolved = target.value.for_theme(theme)
        if ALIAS_PATTERN.match(resolved):
            raise ShapeError(name, f"aliases {alias.group(1)}, which is itself an alias; a role aliases a primitive")
        return resolved

    def pairs(self) -> list[Pair]:
        """Every Pair the file names: one per entry of an ink role's `on` list."""
        return [
            Pair(t.name, f"color.role.{ground}", t.min_contrast)
            for t in self.colors("role")
            if t.min_contrast
            for ground in t.on
        ]


# 2. The mark and the typefaces


@dataclass(frozen=True, slots=True)
class MarkVariant:
    """One file `mark.py` writes under `marks/` (data-model, Mark)."""

    id: str
    file: str


@dataclass(frozen=True, slots=True)
class Typeface:
    role: Literal["text", "code"]
    family: str
    weights: tuple[int, ...]
    fallback: tuple[str, ...]

    @property
    def stack(self) -> str:
        quoted = [f'"{name}"' if " " in name else name for name in (self.family, *self.fallback)]
        return ", ".join(quoted)


# 3. The roster


@dataclass(frozen=True, slots=True)
class FamilyLink:
    order: int
    label: str
    href: str


@dataclass(frozen=True, slots=True)
class Declaration:
    path: str
    locator: str
    form: str


@dataclass(frozen=True, slots=True)
class Lag:
    kind: str
    issue: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TouchpointException:
    """A part of the standard one touchpoint cannot express (data-model, Exception).

    Named `TouchpointException` rather than `Exception` because the latter is the builtin.
    """

    part: str
    reason: str
    since: str


@dataclass(frozen=True, slots=True)
class Touchpoint:
    id: str
    kind: str
    repository: str
    mechanisms: tuple[str, ...]
    declared_at: Declaration
    host: str | None = None
    property_name: str | None = None
    vendored: tuple[str, ...] = ()
    identity_bearing: tuple[str, ...] = ()
    lockup_at: tuple[str, ...] = ()
    readme_kind: str | None = None
    sentence: str | None = None
    notes: str | None = None
    exceptions: tuple[TouchpointException, ...] = ()

    @property
    def host_name(self) -> str | None:
        """The host without its scheme, which names `dist/hosts/<host>/`."""
        if self.host is None:
            return None
        return self.host.removeprefix("https://").removeprefix("http://").rstrip("/")


@dataclass(frozen=True, slots=True)
class Roster:
    path: Path
    family_links: tuple[FamilyLink, ...]
    ownership: str
    touchpoints: tuple[Touchpoint, ...]

    def by_id(self, touchpoint_id: str) -> Touchpoint | None:
        return next((t for t in self.touchpoints if t.id == touchpoint_id), None)

    def by_repository(self, repository: str, kind: str | None = None) -> list[Touchpoint]:
        return [t for t in self.touchpoints if t.repository == repository and (kind is None or t.kind == kind)]

    def hosts(self) -> list[Touchpoint]:
        return [t for t in self.touchpoints if t.kind == "host"]

    def readmes(self) -> list[Touchpoint]:
        return [t for t in self.touchpoints if t.kind == "readme"]


@dataclass(frozen=True, slots=True)
class Derivation:
    """One mechanism's form of the standard under `dist/` (data-model, Derivation)."""

    mechanism: str
    files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Standard:
    """One released definition of the identity (data-model, Standard)."""

    level: str
    tokens: TokenFile
    roster: Roster
    marks: tuple[MarkVariant, ...] = ()
    typefaces: tuple[Typeface, ...] = ()

    @property
    def family_links(self) -> tuple[FamilyLink, ...]:
        return self.roster.family_links

    @property
    def ownership(self) -> str:
        return self.roster.ownership


# 4. Readers


def _require(mapping: Mapping[str, Any], key: str, where: str, kind: type | tuple[type, ...]) -> Any:
    if key not in mapping:
        raise ShapeError(where, f"missing {key}")
    value = mapping[key]
    if not isinstance(value, kind):
        raise ShapeError(
            where, f"{key} must be {kind if isinstance(kind, type) else kind[0]}, found {type(value).__name__}"
        )
    return value


def _color_value(raw: Any, name: str, tier: str) -> ColorValue:
    if not isinstance(raw, Mapping):
        raise ShapeError(name, 'a colour $value is {"light": ..., "dark": ...}')
    values: dict[str, str] = {}
    for theme in THEMES:
        if theme not in raw:
            raise ShapeError(name, f"missing the {theme} value; both themes are required")
        value = raw[theme]
        if not isinstance(value, str):
            raise ShapeError(name, f"the {theme} value must be a string")
        if tier == "primitive" and not HEX_PATTERN.match(value):
            raise ShapeError(name, f"a primitive's {theme} value is six-digit lowercase hex, found {value!r}")
        if tier == "role" and not ALIAS_PATTERN.match(value):
            raise ShapeError(name, f"a role's {theme} value is an alias of a primitive, found {value!r}")
        values[theme] = value
    return ColorValue(light=values["light"], dark=values["dark"])


def _shadow(raw: Any, name: str) -> Shadow:
    if not isinstance(raw, Mapping):
        raise ShapeError(name, "a shadow is an object with color, offsetX, offsetY, blur and spread")
    fields = {k: _require(raw, k, name, str) for k in ("color", "offsetX", "offsetY", "blur", "spread")}
    return Shadow(fields["color"], fields["offsetX"], fields["offsetY"], fields["blur"], fields["spread"])


def _token(name: str, raw: Mapping[str, Any]) -> Token:
    token_type = _require(raw, "$type", name, str)
    if token_type not in TOKEN_TYPES:
        raise ShapeError(name, f"$type {token_type!r} is not one of {', '.join(TOKEN_TYPES)}")
    description = _require(raw, "$description", name, str)
    if not description.strip():
        raise ShapeError(name, "$description is empty; every token states its usage")
    if "$value" not in raw:
        raise ShapeError(name, "missing $value")
    extensions = raw.get("$extensions", {})
    if not isinstance(extensions, Mapping):
        raise ShapeError(name, "$extensions must be an object")
    idfkit: Mapping[str, Any] = (
        extensions.get("idfkit", {}) if isinstance(extensions.get("idfkit", {}), Mapping) else {}
    )
    tier: Literal["primitive", "role"] | None = None
    if name.startswith("color.primitive."):
        tier = "primitive"
    elif name.startswith("color.role."):
        tier = "role"
    value: Any
    if token_type == "color":
        if tier is None:
            raise ShapeError(name, "a colour token lives under color.primitive or color.role")
        value = _color_value(raw["$value"], name, tier)
    elif token_type == "shadow":
        shadows = raw["$value"]
        if not isinstance(shadows, Mapping):
            raise ShapeError(name, 'a shadow $value is {"light": {...}, "dark": {...}}')
        value = {theme: _shadow(shadows.get(theme), f"{name}.{theme}") for theme in THEMES}
    elif token_type == "fontFamily":
        value = tuple(raw["$value"]) if isinstance(raw["$value"], list) else str(raw["$value"])
    elif token_type == "cubicBezier":
        points = raw["$value"]
        if not isinstance(points, list) or len(points) != 4:
            raise ShapeError(name, "a cubicBezier $value is a list of four numbers")
        value = tuple(float(p) for p in points)
    elif token_type == "fontWeight":
        value = int(raw["$value"])
    else:
        value = str(raw["$value"])
    min_contrast = idfkit.get("minContrast")
    if min_contrast is not None and min_contrast not in (4.5, 3):
        raise ShapeError(name, f"minContrast is 4.5 or 3, found {min_contrast!r}")
    on = tuple(idfkit.get("on", ()))
    if min_contrast is not None and not on:
        raise ShapeError(name, "an ink role with minContrast lists the grounds it sits on under `on`")
    return Token(
        name=name,
        type=token_type,
        value=value,
        description=description,
        tier=tier,
        min_contrast=float(min_contrast) if min_contrast is not None else None,
        on=on,
        families=tuple(idfkit.get("families", ())),
    )


def _walk(group: Mapping[str, Any], prefix: str, out: dict[str, Token]) -> None:
    for key, raw in group.items():
        if key.startswith("$"):
            continue
        name = f"{prefix}.{key}" if prefix else key
        if not isinstance(raw, Mapping):
            raise ShapeError(name, "a group holds tokens or groups, not a bare value")
        if "$value" in raw or "$type" in raw:
            out[name] = _token(name, raw)
        else:
            _walk(raw, name, out)


def load_tokens(path: Path) -> TokenFile:
    """Read `identity.tokens.json` under contract section 2, or raise `ShapeError` naming the key."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ShapeError(str(path), f"not valid JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise ShapeError(str(path), "the token file is an object of groups")
    for group in document:
        if group.startswith("$"):
            continue
        if group not in TOKEN_GROUPS:
            raise ShapeError(group, f"not one of the six groups {', '.join(TOKEN_GROUPS)}")
    tokens: dict[str, Token] = {}
    _walk(document, "", tokens)
    for required in (
        "color.primitive",
        "color.role",
        "font.family.text",
        "font.family.code",
        "font.stack.text",
        "font.stack.code",
    ):
        if not any(name == required or name.startswith(required + ".") for name in tokens):
            raise ShapeError(required, "required and missing")
    return TokenFile(path=path, tokens=tokens)


def _declaration(raw: Any, where: str) -> Declaration:
    if not isinstance(raw, Mapping):
        raise ShapeError(where, "declared_at is a table with path, locator and form")
    form = _require(raw, "form", where, str)
    if form not in DECLARATION_FORMS:
        raise ShapeError(f"{where}.form", f"{form!r} is not one of {', '.join(DECLARATION_FORMS)}")
    return Declaration(_require(raw, "path", where, str), _require(raw, "locator", where, str), form)


def _exception(raw: Mapping[str, Any], where: str) -> TouchpointException:
    part = _require(raw, "part", where, str)
    reason = _require(raw, "reason", where, str)
    since = _require(raw, "since", where, str)
    if not reason.strip():
        raise ShapeError(f"{where}.reason", "an exception states its reason")
    if any(re.search(rf"\b{word}\b", reason, re.IGNORECASE) for word in LAG_WORDS):
        raise ShapeError(f"{where}.reason", '"not done yet" is a Lag, never an Exception (contract section 6)')
    if not LEVEL_PATTERN.match(since):
        raise ShapeError(f"{where}.since", f"{since!r} is not identity-YYYY.N")
    return TouchpointException(part, reason, since)


def _touchpoint(raw: Mapping[str, Any], index: int) -> Touchpoint:
    where = f"touchpoint[{index}]"
    touchpoint_id = _require(raw, "id", where, str)
    where = f"touchpoint.{touchpoint_id}"
    kind = _require(raw, "kind", where, str)
    if kind not in TOUCHPOINT_KINDS:
        raise ShapeError(f"{where}.kind", f"{kind!r} is not host or readme")
    mechanisms = tuple(_require(raw, "mechanisms", where, list))
    for mechanism in mechanisms:
        if mechanism not in MECHANISMS:
            raise ShapeError(f"{where}.mechanisms", f"{mechanism!r} is not a mechanism derivations.md defines")
    host = raw.get("host")
    property_name = raw.get("property_name")
    readme_kind = raw.get("readme_kind")
    sentence = raw.get("sentence")
    if kind == "host":
        if not isinstance(host, str) or not host:
            raise ShapeError(f"{where}.host", "a host touchpoint names its host")
        if not isinstance(property_name, str):
            raise ShapeError(
                f"{where}.property_name", 'a host touchpoint names its property, or "" for the marketing site'
            )
        if any(retired in host for retired in RETIRED_HOSTS):
            raise ShapeError(f"{where}.host", f"{host} is a retired host")
    else:
        if readme_kind not in README_KINDS:
            raise ShapeError(
                f"{where}.readme_kind", f"a readme touchpoint carries readme_kind, one of {', '.join(README_KINDS)}"
            )
        if not isinstance(sentence, str) or not sentence.strip():
            raise ShapeError(f"{where}.sentence", "a readme touchpoint carries the one sentence its header shows")
        if not sentence.rstrip().endswith("."):
            raise ShapeError(f"{where}.sentence", "the sentence ends in a full stop")
    exceptions = tuple(_exception(e, f"{where}.exception[{i}]") for i, e in enumerate(raw.get("exception", [])))
    return Touchpoint(
        id=touchpoint_id,
        kind=kind,
        repository=_require(raw, "repository", where, str),
        mechanisms=mechanisms,
        declared_at=_declaration(raw.get("declared_at"), f"{where}.declared_at"),
        host=host if isinstance(host, str) else None,
        property_name=property_name if isinstance(property_name, str) else None,
        vendored=tuple(raw.get("vendored", ())),
        identity_bearing=tuple(raw.get("identity_bearing", ())),
        lockup_at=tuple(raw.get("lockup_at", ())),
        readme_kind=readme_kind if isinstance(readme_kind, str) else None,
        sentence=sentence if isinstance(sentence, str) else None,
        notes=raw.get("notes") if isinstance(raw.get("notes"), str) else None,
        exceptions=exceptions,
    )


def load_roster(path: Path) -> Roster:
    """Read `touchpoints.toml` under contract section 1, or raise `ShapeError` naming the key."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ShapeError(str(path), f"not valid TOML: {error}") from error
    raw_links: Sequence[Mapping[str, Any]] = document.get("family_link", [])
    links = tuple(
        FamilyLink(
            _require(raw, "order", f"family_link[{i}]", int),
            _require(raw, "label", f"family_link[{i}]", str),
            _require(raw, "href", f"family_link[{i}]", str),
        )
        for i, raw in enumerate(raw_links)
    )
    if len(links) != 7 or sorted(link.order for link in links) != list(range(1, 8)):
        raise ShapeError("family_link", "exactly seven family links with orders 1 to 7")
    if len({link.label for link in links}) != 7 or len({link.href for link in links}) != 7:
        raise ShapeError("family_link", "family links have distinct labels and hosts")
    for link in links:
        if any(retired in link.href for retired in RETIRED_HOSTS):
            raise ShapeError("family_link", f"{link.href} is a retired host")
    ownership = _require(document, "ownership", "ownership", str)
    touchpoints = tuple(_touchpoint(t, i) for i, t in enumerate(document.get("touchpoint", [])))
    ids = [t.id for t in touchpoints]
    if len(set(ids)) != len(ids):
        duplicate = next(i for i in ids if ids.count(i) > 1)
        raise ShapeError(f"touchpoint.{duplicate}", "id is not unique")
    if "level" in document:
        raise ShapeError("level", "the roster never states a level; a tool that wants one follows declared_at")
    return Roster(
        path=path,
        family_links=tuple(sorted(links, key=lambda link: link.order)),
        ownership=ownership,
        touchpoints=touchpoints,
    )


def load_standard(root: Path, level: str) -> Standard:
    """The standard at `root`, named `level` (the tag, or `unreleased` for a working tree)."""
    return Standard(
        level=level, tokens=load_tokens(root / "identity.tokens.json"), roster=load_roster(root / "touchpoints.toml")
    )


__all__ = [
    "ALIAS_PATTERN",
    "DECLARATION_FORMS",
    "HEX_PATTERN",
    "LAG_KINDS",
    "LEVEL_PATTERN",
    "MECHANISMS",
    "README_KINDS",
    "RETIRED_HOSTS",
    "THEMES",
    "TOKEN_GROUPS",
    "ColorValue",
    "Declaration",
    "Derivation",
    "FamilyLink",
    "Lag",
    "MarkVariant",
    "Pair",
    "Roster",
    "Shadow",
    "ShapeError",
    "Standard",
    "ThemeId",
    "Token",
    "TokenFile",
    "Touchpoint",
    "TouchpointException",
    "Typeface",
    "load_roster",
    "load_standard",
    "load_tokens",
]
