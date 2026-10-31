"""Every touchpoint's declared level, read from where it lives, against the latest tag.

Run by the maintainer through the `identity-sweep` skill, never on a schedule (research R3):

    python idfkit-brand/tools/sweep_touchpoints.py --workspace ..

For every touchpoint in the roster: find its checkout in the workspace, read its declaration where
`declared_at` says, compare with the latest `identity-` tag of this checkout, and say so. A host
that is behind writes a Lag beside its declaration or is `unexplained`; a README behind the latest
is `behind` and not a failure, since it adopts a tag by changing three addresses and nothing waits
on it. A checkout missing from the workspace is `unreachable` and not a failure either: the sweep
reports what it could not see rather than counting it as fine.

Writes `sweep-report.json` in the workspace and prints one line per touchpoint. Exit 1 only when a
host is behind without a Lag; 2 when the roster or the tags could not be read.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_touchpoint import read_declaration
from models import LAG_KINDS, PRIVATE_REPOSITORIES, Lag, Roster, Touchpoint, load_roster

STANDARD_ROOT = Path(__file__).resolve().parent.parent
EXIT_UNEXPLAINED = 1
EXIT_UNREADABLE = 2
UNRELEASED = "unreleased"
#: Workspace folders that are not named after their repository.
FOLDER_ALIASES: dict[str, str] = {"idfkit-app": "envelop", ".github": "idfkit-org"}


@dataclass(frozen=True, slots=True)
class Swept:
    id: str
    repository: str
    kind: str
    folder: str
    declared: str | None
    latest: str
    status: str
    lag: Lag | None = None
    note: str | None = None

    def render(self) -> str:
        lag = f"{self.lag.kind}: {self.lag.reason or self.lag.issue}" if self.lag else ""
        return f"{self.id:<26} {self.declared or '-':<16} {self.latest:<16} {self.status}{(' (' + lag + ')') if lag else ''}{(' ' + self.note) if self.note else ''}"


@dataclass(frozen=True, slots=True)
class Report:
    identity_latest: str
    swept_at: str
    touchpoints: tuple[Swept, ...]

    @property
    def unexplained(self) -> list[Swept]:
        return [t for t in self.touchpoints if t.status == "unexplained"]

    @property
    def unreachable(self) -> list[Swept]:
        return [t for t in self.touchpoints if t.status == "unreachable"]


def latest_tag(standard: Path) -> str | None:
    """The newest identity-YYYY.N tag of the checkout, by year then number; None when there is none."""
    result = subprocess.run(
        ["git", "-C", str(standard), "tag", "--list", "identity-*"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "git tag failed")
    tags = [t for t in result.stdout.split() if t.startswith("identity-")]
    if not tags:
        return None

    def key(tag: str) -> tuple[int, int]:
        year, number = tag.removeprefix("identity-").split(".")
        return int(year), int(number)

    return max(tags, key=key)


def level_key(level: str) -> tuple[int, int]:
    year, number = level.removeprefix("identity-").split(".")
    return int(year), int(number)


def folder_for(touchpoint: Touchpoint, workspace: Path) -> Path:
    name = touchpoint.repository.split("/", 1)[1]
    return workspace / FOLDER_ALIASES.get(name, name)


def read_lag(root: Path, touchpoint: Touchpoint) -> Lag | None:
    """The Lag beside the declaration: `tool.idfkit.identity.lag` or `/idfkit/identityLag`."""
    declaration = touchpoint.declared_at
    path = root / declaration.path
    if not path.exists():
        return None
    raw: object = None
    if declaration.form == "toml-key":
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        node: object = document
        for key in declaration.locator.split(".")[:-1]:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        raw = node.get("lag") if isinstance(node, dict) else None
    elif declaration.form == "json-pointer":
        document = json.loads(path.read_text(encoding="utf-8"))
        node = document
        for key in declaration.locator.strip("/").split("/")[:-1]:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        raw = node.get("identityLag") if isinstance(node, dict) else None
    if not isinstance(raw, dict) or raw.get("kind") not in LAG_KINDS:
        return None
    return Lag(kind=str(raw["kind"]), issue=raw.get("issue"), reason=raw.get("reason"))


def sweep_one(touchpoint: Touchpoint, workspace: Path, latest: str) -> Swept:
    folder = folder_for(touchpoint, workspace)

    def swept(declared: str | None, status: str, lag: Lag | None = None, note: str | None = None) -> Swept:
        return Swept(
            id=touchpoint.id,
            repository=touchpoint.repository,
            kind="package" if touchpoint.readme_kind == "package" else touchpoint.kind,
            folder=str(folder),
            declared=declared,
            latest=latest,
            status=status,
            lag=lag,
            note=note,
        )

    if not folder.is_dir():
        private = "a private repository, with " if touchpoint.repository in PRIVATE_REPOSITORIES else ""
        return swept(None, "unreachable", note=f"{private}no checkout in the workspace")
    declared, error = read_declaration(folder, touchpoint)
    if declared is None:
        return swept(None, "unexplained" if touchpoint.kind == "host" else "behind", note=f"undeclared: {error}")
    if latest == UNRELEASED or level_key(declared) >= level_key(latest):
        return swept(declared, "current")
    if touchpoint.kind == "readme":
        return swept(declared, "behind")
    lag = read_lag(folder, touchpoint)
    if lag is None:
        return swept(declared, "unexplained")
    return swept(declared, "lagging", lag=lag)


def sweep(roster: Roster, workspace: Path, latest: str) -> Report:
    swept = tuple(sweep_one(t, workspace, latest) for t in roster.touchpoints)
    return Report(
        identity_latest=latest, swept_at=datetime.now(UTC).replace(microsecond=0).isoformat(), touchpoints=swept
    )


def write_report(report: Report, path: Path) -> None:
    payload = {
        "identity_latest": report.identity_latest,
        "swept_at": report.swept_at,
        "touchpoints": [asdict(t) for t in report.touchpoints],
        "unexplained": [t.id for t in report.unexplained],
        "unreachable": [t.id for t in report.unreachable],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Every touchpoint's declared identity level, against the latest tag.")
    parser.add_argument(
        "--workspace", type=Path, default=STANDARD_ROOT.parent, help="the root the checkouts are siblings under"
    )
    parser.add_argument(
        "--standard", type=Path, default=STANDARD_ROOT, help="the idfkit-brand checkout: the roster and the tags"
    )
    parser.add_argument("--report", type=Path, help="where to write sweep-report.json (default: the workspace)")
    args = parser.parse_args(list(argv) if argv is not None else None)
    standard = args.standard.resolve()
    workspace = args.workspace.resolve()
    try:
        roster = load_roster(standard / "touchpoints.toml")
        latest = latest_tag(standard) or UNRELEASED
    except (OSError, ValueError) as error:
        print(f"the roster or the tags could not be read at {standard}: {error}. Nothing was swept.")
        return EXIT_UNREADABLE
    report = sweep(roster, workspace, latest)
    report_path = args.report or workspace / "sweep-report.json"
    write_report(report, report_path)
    print(f"latest tag: {latest}")
    for swept in report.touchpoints:
        print(swept.render())
    print(f"report: {report_path}")
    if report.unexplained:
        print(
            f"{len(report.unexplained)} host(s) behind without a stated Lag: "
            + ", ".join(t.id for t in report.unexplained)
        )
        return EXIT_UNEXPLAINED
    return 0


if __name__ == "__main__":
    sys.exit(main())
