"""One touchpoint's check: does this tree render what it declares? (contracts/touchpoint-check.md section 4)

Run by `check-touchpoint.yml` at the touchpoint's pinned tag, against the tag's release archives,
and from the workspace by the identity-adopt skill against a `dist` built from the checkout:

    python idfkit-brand/tools/check_touchpoint.py --root idfkit.com --level identity-2026.1 --dist idfkit-brand/dist

Five assertions, each a function returning typed findings:

  1. The repository is in the roster, with the kind and mechanisms the tree exhibits.
  2. The value at `declared_at` resolves, equals `--level`, and the tag exists.
  3. Every file under every vendored path is byte-identical to the tag's dist for that mechanism
     and host; rasters compare by decoded pixels.
  4. No identity-bearing file carries a colour literal, a font family, a font face or a font host,
     outside the vendored paths and outside a line marked `identity-exception: <part>` that matches
     an exception in the roster.
  5. For a readme touchpoint, the root README conforms to readme-header.md, its sentence equals the
     roster's, and a library README keeps its parity statement.

It never compares `--level` against the latest tag (a touchpoint may be behind; the sweep says who
is) and never reads the network. Exit 0 when every assertion holds; 1 naming every finding with its
file and place; 2 when the standard or the dist could not be read, which is never a pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models import LEVEL_PATTERN, MECHANISMS, Roster, Touchpoint, load_roster
from rasters import RasterError, compare_ico, compare_png

STANDARD_ROOT = Path(__file__).resolve().parent.parent
EXIT_FINDINGS = 1
EXIT_UNREADABLE = 2

RELEASE_HOST = "https://github.com/idfkit/idfkit-brand/releases/download/"
HEX_LITERAL = re.compile(r"(?<![\w&{-])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
FUNCTION_LITERAL = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab)\(")
JS_HEX_LITERAL = re.compile(r"\b0x[0-9a-fA-F]{6}\b")
FONT_FAMILY = re.compile(
    r"""font-family\s*:\s*(?!\s*(?:var\(|inherit|initial|unset|monospace\b|sans-serif\b|serif\b|system-ui\b))"""
)
FONT_FACE = re.compile(r"@font-face|@import\s+url\(|fonts\.googleapis\.com|fonts\.gstatic\.com")
EXCEPTION_MARKER = re.compile(r"identity-exception:\s*([A-Za-z0-9_./-]+)")
TEXT_SUFFIXES = frozenset({
    ".css",
    ".html",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".svg",
})
#: Container directories under a vendored path are named for what they hold.
VENDORED_DIRS: tuple[str, ...] = (*MECHANISMS, "hosts", "brand-page")
FAMILY_SEPARATOR = " · "


@dataclass(frozen=True, slots=True)
class Finding:
    assertion: int
    message: str
    file: str | None = None
    place: str | None = None

    def render(self) -> str:
        where = ""
        if self.file:
            where = self.file + (f":{self.place}" if self.place else "") + ": "
        return f"assertion {self.assertion}: {where}{self.message}"


# 1. Roster membership


def exhibited_mechanisms(root: Path) -> set[str]:
    found: set[str] = set()
    if (root / "mkdocs.yml").exists() or (root / "zensical.toml").exists():
        found.add("material")
    package = root / "package.json"
    if package.exists() and "@stytch/react" in package.read_text(encoding="utf-8"):
        found.add("stytch")
    return found


def check_membership(
    roster: Roster, repository: str, root: Path, kind: str | None
) -> tuple[list[Touchpoint], list[Finding]]:
    entries = roster.by_repository(repository, kind)
    if not entries:
        return [], [
            Finding(
                1,
                f"{repository} is not in the roster{f' as a {kind} touchpoint' if kind else ''}. A public surface that renders the identity is a touchpoint; add it to touchpoints.toml in idfkit-brand.",
            )
        ]
    findings: list[Finding] = []
    for entry in entries:
        if entry.kind == "host":
            missing = exhibited_mechanisms(root) - set(entry.mechanisms)
            for mechanism in sorted(missing):
                findings.append(
                    Finding(
                        1,
                        f"the tree exhibits the {mechanism} mechanism and the roster entry {entry.id} does not list it; change the roster in the same pull request.",
                    )
                )
        else:
            if not (root / entry.declared_at.path).exists():
                findings.append(Finding(1, "the README the roster names does not exist", entry.declared_at.path))
    return entries, findings


# 2. The declaration


def read_declaration(root: Path, entry: Touchpoint) -> tuple[str | None, str | None]:
    """(value, error). An image-url declaration must carry one tag in every address."""
    declaration = entry.declared_at
    path = root / declaration.path
    if not path.exists():
        return None, "the file does not exist"
    text = path.read_text(encoding="utf-8")
    if declaration.form == "toml-key":
        try:
            document = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            return None, f"not valid TOML: {error}"
        node: object = document
        for key in declaration.locator.split("."):
            if not isinstance(node, dict) or key not in node:
                return None, f"{declaration.locator} does not resolve"
            node = node[key]
        return (node, None) if isinstance(node, str) else (None, f"{declaration.locator} is not a string")
    if declaration.form == "json-pointer":
        try:
            node = json.loads(text)
        except json.JSONDecodeError as error:
            return None, f"not valid JSON: {error}"
        for key in declaration.locator.strip("/").split("/"):
            if not isinstance(node, dict) or key not in node:
                return None, f"{declaration.locator} does not resolve"
            node = node[key]
        return (node, None) if isinstance(node, str) else (None, f"{declaration.locator} is not a string")
    matches = re.findall(declaration.locator, text)
    if not matches:
        return None, f"no address matches {declaration.locator}"
    if len(set(matches)) > 1:
        return None, f"the image addresses carry different tags: {', '.join(sorted(set(matches)))}"
    return matches[0], None


def tag_exists(standard: Path, level: str) -> bool | None:
    """True or False from `git tag`; None when git cannot answer (then the tag is not judged)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(standard), "tag", "--list", level], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return level in result.stdout.split()


def check_declaration(root: Path, entry: Touchpoint, level: str, standard: Path, require_tag: bool) -> list[Finding]:
    value, error = read_declaration(root, entry)
    where = f"{entry.declared_at.path} at {entry.declared_at.locator}"
    if error is not None:
        return [Finding(2, f"{where}: {error}", entry.declared_at.path)]
    if value != level:
        return [
            Finding(
                2,
                f"{where} reads {value!r}, and the check runs at {level}; the declaration and the uses: ref are one fact",
                entry.declared_at.path,
            )
        ]
    if require_tag:
        exists = tag_exists(standard, level)
        if exists is False:
            return [
                Finding(
                    2,
                    f"{level} is not a tag of idfkit-brand (checked in {standard}); a touchpoint declares a released tag",
                    entry.declared_at.path,
                )
            ]
    return []


# 3. Vendored derivations


def _normalise_head(text: str) -> str:
    """head.html with its path prefix reduced to `/`, since a host may serve the directory elsewhere."""
    match = re.search(r'rel="icon" href="([^"]*?)favicon\.svg"', text)
    if not match or match.group(1) == "/":
        return text
    prefix = match.group(1)
    return text.replace(prefix, "/")


def _compare_file(vendored: Path, reference: Path, rasters: str) -> str | None:
    if vendored.suffix in (".png", ".ico"):
        if rasters == "skip":
            return None
        try:
            difference = (
                compare_png(vendored.read_bytes(), reference.read_bytes())
                if vendored.suffix == ".png"
                else compare_ico(vendored.read_bytes(), reference.read_bytes())
            )
        except RasterError as error:
            return f"could not be decoded: {error}"
        if difference is None:
            return None
        return difference if isinstance(difference, str) else f"first differing {difference.render()}"
    a, b = vendored.read_bytes(), reference.read_bytes()
    if vendored.name == "head.html":
        a, b = _normalise_head(a.decode("utf-8")).encode(), b
    if a == b:
        return None
    offset = next((i for i, (x, y) in enumerate(zip(a, b, strict=False)) if x != y), min(len(a), len(b)))
    return f"differs from the tag's file at byte offset {offset}"


def _dist_for(vendored_dir: Path, entry: Touchpoint, dist: Path) -> dict[Path, Path]:
    """Map each vendored directory to the dist directory it must equal."""
    pairs: dict[Path, Path] = {}
    name = vendored_dir.name
    host = entry.host_name or ""
    if name in VENDORED_DIRS:
        pairs[vendored_dir] = (
            dist / "hosts" / host
            if name == "hosts" and (vendored_dir / host).exists() is False and not any(vendored_dir.iterdir())
            else dist / name
        )
        if name == "hosts":
            pairs[vendored_dir] = dist / "hosts"
        return pairs
    if vendored_dir.is_dir():
        for child in sorted(p for p in vendored_dir.iterdir() if p.is_dir()):
            if child.name in VENDORED_DIRS:
                pairs[child] = dist / child.name
    return pairs


def check_vendored(root: Path, entry: Touchpoint, dist: Path, rasters: str) -> list[Finding]:
    findings: list[Finding] = []
    host = entry.host_name or ""
    for vendored_path in entry.vendored:
        vendored_dir = root / vendored_path
        if not vendored_dir.exists():
            findings.append(
                Finding(
                    3,
                    "the vendored directory does not exist; adopt the tag through the identity-adopt skill",
                    vendored_path,
                )
            )
            continue
        pairs = _dist_for(vendored_dir, entry, dist)
        if not pairs:
            findings.append(
                Finding(3, "holds no mechanism directory; expected one of " + ", ".join(VENDORED_DIRS), vendored_path)
            )
            continue
        for local, reference in pairs.items():
            reference_root = reference
            local_root = local
            if reference.name == "hosts":
                reference_root = reference / host
                local_root = local / host if (local / host).is_dir() else local
            if not reference_root.is_dir():
                findings.append(
                    Finding(
                        3,
                        f"the tag's dist has no {reference_root.relative_to(dist)}; the mechanism is not one of this touchpoint's",
                        str(local.relative_to(root)),
                    )
                )
                continue
            local_files = {
                p.relative_to(local_root) for p in local_root.rglob("*") if p.is_file() and not p.name.startswith(".")
            }
            reference_files = {p.relative_to(reference_root) for p in reference_root.rglob("*") if p.is_file()}
            for missing in sorted(reference_files - local_files):
                findings.append(
                    Finding(3, "is in the tag's dist and not vendored", str((local_root / missing).relative_to(root)))
                )
            for extra in sorted(local_files - reference_files):
                findings.append(
                    Finding(
                        3,
                        "is vendored and not in the tag's dist; a vendored directory holds derived files only",
                        str((local_root / extra).relative_to(root)),
                    )
                )
            for shared in sorted(local_files & reference_files):
                difference = _compare_file(local_root / shared, reference_root / shared, rasters)
                if difference:
                    findings.append(Finding(3, difference, str((local_root / shared).relative_to(root))))
    return findings


# 4. Stray identity values


def _is_vendored(path: Path, root: Path, entry: Touchpoint) -> bool:
    rel = path.relative_to(root).as_posix()
    return any(rel.startswith(v.rstrip("/") + "/") for v in entry.vendored)


def scan_line(line: str, suffix: str) -> str | None:
    """The first literal on the line, or None."""
    for pattern in (HEX_LITERAL, FUNCTION_LITERAL, FONT_FACE):
        match = pattern.search(line)
        if match:
            return match.group(0)
    if suffix in (".js", ".mjs", ".ts", ".tsx", ".jsx"):
        match = JS_HEX_LITERAL.search(line)
        if match:
            return match.group(0)
    match = FONT_FAMILY.search(line)
    if match:
        return "font-family naming a family"
    return None


def _head_lines(entry: Touchpoint, dist: Path | None) -> frozenset[str]:
    """The lines of the host's head.html at the tag, stripped: the standard's own lines, pasted where a host
    cannot include a file (a Material override, a static page). A theme-color meta carries a hex value, and a
    line that is verbatim one of these is not a stray literal."""
    if dist is None or not entry.host_name:
        return frozenset()
    head = dist / "hosts" / entry.host_name / "head.html"
    if not head.is_file():
        return frozenset()
    return frozenset(line.strip() for line in head.read_text(encoding="utf-8").splitlines() if line.strip())


def check_literals(root: Path, entry: Touchpoint, dist: Path | None = None) -> list[Finding]:
    findings: list[Finding] = []
    allowed = {e.part for e in entry.exceptions}
    head_lines = _head_lines(entry, dist)
    seen: set[Path] = set()
    for pattern in entry.identity_bearing:
        for path in sorted(root.glob(pattern)):
            if (
                path in seen
                or not path.is_file()
                or path.suffix not in TEXT_SUFFIXES
                or _is_vendored(path, root, entry)
            ):
                continue
            seen.add(path)
            if any(part in ("node_modules", ".git", "dist", "site") for part in path.relative_to(root).parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(lines, start=1):
                literal = scan_line(line, path.suffix)
                if literal is None or line.strip() in head_lines:
                    continue
                marker = EXCEPTION_MARKER.search(line)
                if marker and marker.group(1) in allowed:
                    continue
                if marker:
                    findings.append(
                        Finding(
                            4,
                            f"{literal!r} is marked identity-exception: {marker.group(1)}, and the roster records no such exception for {entry.id}",
                            str(path.relative_to(root)),
                            str(number),
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            4,
                            f"{literal!r} is an identity value outside the vendored derivation; read it through a property",
                            str(path.relative_to(root)),
                            str(number),
                        )
                    )
    return findings


# 5. The README header


BADGES_BY_KIND: dict[str, int] = {"library": 5, "service": 3, "site": 2, "plugin": 2, "profile": 0}
LABELS: tuple[str, ...] = ("idfkit", "Developers", "EnergyPlus docs", "Envelop", "MCP", "Shoebox", "GitHub")


def _strip_fences(lines: list[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(lines, start=1):
        if line.strip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            out.append((number, line))
    return out


def _check_picture_block(
    lines: list[str], entry: Touchpoint, level: str, file: str
) -> tuple[list[Finding], int | None]:
    """Findings on the picture block, and the index of its closing line."""
    findings: list[Finding] = []
    profile = entry.readme_kind == "profile"
    picture_start = next((i for i, line in enumerate(lines) if line.strip().startswith('<p align="center">')), None)
    if picture_start is None or any(lines[i].strip() for i in range(picture_start)):
        findings.append(Finding(5, "nothing precedes the picture block, which opens the file", file, "1"))
        picture_start = picture_start or 0
    picture_end = next((i for i in range(picture_start, len(lines)) if lines[i].strip() == "</p>"), None)
    if picture_end is None:
        return [*findings, Finding(5, "the picture block does not close", file, str(picture_start + 1))], None
    block = "\n".join(lines[picture_start : picture_end + 1])
    addresses = re.findall(r'(?:srcset|src)="([^"]+)"', block)
    expected_files = (
        ("lockup-on-dark.svg", "lockup-on-light.svg", "tile.svg")
        if profile
        else ("mark-on-dark.svg", "mark-on-light.svg", "tile.svg")
    )
    if len(addresses) != 3:
        findings.append(
            Finding(
                5,
                f"the picture block carries three image addresses, found {len(addresses)}",
                file,
                str(picture_start + 1),
            )
        )
    for address, expected in zip(addresses, expected_files, strict=False):
        if address != f"{RELEASE_HOST}{level}/{expected}":
            findings.append(
                Finding(5, f"expected {RELEASE_HOST}{level}/{expected}, found {address}", file, str(picture_start + 1))
            )
    width = re.search(r'width="(\d+)"', block)
    expected_width = "240" if profile else "72"
    if not width or width.group(1) != expected_width:
        findings.append(Finding(5, f"the fallback image's width is {expected_width}", file, str(picture_start + 1)))
    if 'media="(prefers-color-scheme: dark)"' not in block or 'media="(prefers-color-scheme: light)"' not in block:
        findings.append(
            Finding(
                5, "the picture block selects by prefers-color-scheme, dark and light", file, str(picture_start + 1)
            )
        )
    return findings, picture_end


def check_readme(root: Path, entry: Touchpoint, roster: Roster, level: str) -> list[Finding]:
    path = root / entry.declared_at.path
    file = entry.declared_at.path
    if not path.exists():
        return [Finding(5, "the README does not exist", file)]
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[Finding] = []
    profile = entry.readme_kind == "profile"
    visible = _strip_fences(lines)
    headings = [(number, line) for number, line in visible if re.match(r"^#\s", line)]
    if len(headings) != 1 and not profile:
        findings.append(
            Finding(
                5,
                f"exactly one top-level heading outside code blocks, found {len(headings)}",
                file,
                str(headings[1][0]) if len(headings) > 1 else None,
            )
        )
    picture_findings, picture_end = _check_picture_block(lines, entry, level, file)
    findings += picture_findings
    if picture_end is None:
        return findings
    rest = [(i + picture_end + 2, line) for i, line in enumerate(lines[picture_end + 1 :])]
    content = [(number, line) for number, line in rest if line.strip()]
    cursor = 0
    if not profile:
        if not content or not re.match(r"^#\s+\S", content[0][1]):
            findings.append(
                Finding(5, "the heading follows the picture block", file, str(content[0][0]) if content else None)
            )
        else:
            name = entry.repository.split("/", 1)[1]
            if content[0][1].strip() != f"# {name}":
                findings.append(
                    Finding(
                        5, f"the heading names the repository as GitHub names it: # {name}", file, str(content[0][0])
                    )
                )
            cursor = 1
    if len(content) <= cursor:
        return [*findings, Finding(5, "the sentence, the family links and the badge row follow", file)]
    sentence_number, sentence = content[cursor]
    if sentence.strip() != (entry.sentence or ""):
        findings.append(
            Finding(
                5,
                f"the sentence is the roster's: {entry.sentence!r}; found {sentence.strip()!r}",
                file,
                str(sentence_number),
            )
        )
    cursor += 1
    if len(content) <= cursor:
        return [*findings, Finding(5, "the family links follow the sentence", file)]
    links_number, links_line = content[cursor]
    labels = re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", links_line)
    expected_links = [(link.label, link.href) for link in roster.family_links]
    if (
        labels != expected_links
        or FAMILY_SEPARATOR.join(f"[{a}]({b})" for a, b in expected_links) != links_line.strip()
    ):
        findings.append(
            Finding(
                5,
                "the family links line is the seven links, in order, with the standard's labels, separated by ' · '",
                file,
                str(links_number),
            )
        )
    cursor += 1
    expected_badges = BADGES_BY_KIND.get(entry.readme_kind or "", 0)
    header_end = links_number
    if expected_badges:
        if len(content) <= cursor:
            findings.append(Finding(5, "the badge row follows the family links", file))
        else:
            badge_number, badge_line = content[cursor]
            header_end = badge_number
            badges = re.findall(r"!\[[^\]]*\]\([^)]+\)", badge_line)
            if len(badges) != expected_badges:
                findings.append(
                    Finding(
                        5,
                        f"the {entry.readme_kind} badge set has {expected_badges} badges on one line, found {len(badges)}",
                        file,
                        str(badge_number),
                    )
                )
    if entry.readme_kind == "library":
        # The statement lives below the header, at its own prominence (FR-033); the parity badge is not it.
        parity_lines = [
            number
            for number, line in visible
            if number > header_end and "parity" in line.lower() and re.search(r"\]\(https?://[^)]*parity[^)]*\)", line)
        ]
        if not parity_lines:
            findings.append(
                Finding(
                    5,
                    "a library README keeps its parity statement: the word parity and a link to the capability-parity page (FR-033)",
                    file,
                )
            )
    return findings


# 6. Entry point


def detect_repository(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    match = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?\s*$", result.stdout)
    return match.group(1) if match else None


def check(
    roster: Roster,
    repository: str,
    root: Path,
    level: str,
    dist: Path | None,
    standard: Path,
    rasters: str,
    kind: str | None,
    require_tag: bool,
) -> list[Finding]:
    entries, findings = check_membership(roster, repository, root, kind)
    for entry in entries:
        findings += check_declaration(root, entry, level, standard, require_tag)
        if entry.kind == "host":
            if dist is None:
                findings.append(
                    Finding(3, "no dist to compare against: pass --dist, a dist built from idfkit-brand at the tag")
                )
            else:
                findings += check_vendored(root, entry, dist, rasters)
            findings += check_literals(root, entry, dist)
        else:
            findings += check_readme(root, entry, roster, level)
    return findings


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check one touchpoint against its declared identity tag.")
    parser.add_argument("--repository", help="owner/name; read from the git remote when omitted")
    parser.add_argument("--level", required=True, help="the identity-YYYY.N tag the touchpoint declares")
    parser.add_argument("--root", type=Path, default=Path("."), help="the touchpoint's checkout")
    parser.add_argument(
        "--dist", type=Path, help="the tag's dist: the release archives in CI, a local build from the workspace"
    )
    parser.add_argument(
        "--standard",
        type=Path,
        default=STANDARD_ROOT,
        help="the idfkit-brand checkout holding touchpoints.toml (default: this one)",
    )
    parser.add_argument("--rasters", choices=("compare", "skip"), default="compare")
    parser.add_argument("--kind", choices=("host", "readme"), help="check only this kind of entry for the repository")
    parser.add_argument(
        "--allow-untagged",
        action="store_true",
        help="do not require the level to be a tag of the standard (a rehearsal before the tag is cut)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not LEVEL_PATTERN.match(args.level):
        print(f"{args.level} is not identity-YYYY.N")
        return EXIT_UNREADABLE
    root = args.root.resolve()
    try:
        roster = load_roster(args.standard / "touchpoints.toml")
    except (OSError, ValueError) as error:
        print(f"the roster could not be read at {args.standard}: {error}. Nothing was checked.")
        return EXIT_UNREADABLE
    dist = args.dist.resolve() if args.dist else None
    if dist is not None and not dist.is_dir():
        print(
            f"{dist} is not a directory. Build it with `python build.py --out {dist}` in idfkit-brand at {args.level}, or download the tag's archives. Nothing was checked."
        )
        return EXIT_UNREADABLE
    repository = args.repository or detect_repository(root)
    if repository is None:
        print("pass --repository owner/name; the git remote of the root did not name one")
        return EXIT_UNREADABLE
    findings = check(
        roster,
        repository,
        root,
        args.level,
        dist,
        args.standard.resolve(),
        args.rasters,
        args.kind,
        not args.allow_untagged,
    )
    for finding in findings:
        print("FAIL " + finding.render())
    if findings:
        print(f"{repository}: {len(findings)} findings at {args.level}")
        return EXIT_FINDINGS
    print(f"{repository}: conforms to {args.level}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
