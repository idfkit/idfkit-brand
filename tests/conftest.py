"""Shared fixtures: the repository root, and a working copy of the standard a test may break."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def standard_copy(tmp_path: Path) -> Path:
    """A copy of the standard's source a test may edit: tokens, roster, templates, marks, mark.py."""
    for name in ("identity.tokens.json", "touchpoints.toml", "mark.py"):
        shutil.copy(ROOT / name, tmp_path / name)
    for directory in ("templates", "marks"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    return tmp_path


@pytest.fixture(scope="session")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One build of the standard at identity-2026.1, shared by the build and check tests."""
    pytest.importorskip("build")
    import build as build_module

    if shutil.which("rsvg-convert") is None:
        pytest.skip("rsvg-convert is not on PATH")
    out = tmp_path_factory.mktemp("dist")
    build_module.run(build_module.load_build(ROOT, out, "identity-2026.1"), with_archive=True)
    return out
