# Changelog

All notable changes to the standard are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are the
`identity-YYYY.N` tags; the standard has no semantic version, since it has no API to break.

## [Unreleased]

### Added

- The standard: `identity.tokens.json` (both themes), `mark.py` with its committed masters, the
  self-hosted typefaces, `touchpoints.toml`, the templates, and `build.py`, which derives one form
  per rendering mechanism into `dist/`.
- `tools/validate_identity.py`, the gate every pull request runs; `tools/check_touchpoint.py`, the
  five assertions a touchpoint's CI runs at its pinned tag; `tools/sweep_touchpoints.py`, run by the
  maintainer through the `identity-sweep` skill.
- The `identity-adopt` skill, the procedure that brings one touchpoint to a tag.
