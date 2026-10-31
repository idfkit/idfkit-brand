# Changelog

All notable changes to the standard are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are the
`identity-YYYY.N` tags; the standard has no semantic version, since it has no API to break.

## [Unreleased]

### Review

- 2026-10-31: the owner reviewed every graphic on the contact sheet on both grounds: the mark
  variants, the favicons at 16 and 32 px, the tiles, the host social images, the repository
  previews, the README images and the brand-page assets. Two corrections followed and were
  rebuilt: the property lockup's viewBox now covers the label's descenders, and the word space
  inside a two-word property name is 0.3 em. Every graphic is accepted; the first tag may be cut.

### Added

- The standard: `identity.tokens.json` (both themes), `mark.py` with its committed masters, the
  self-hosted typefaces, `touchpoints.toml`, the templates, and `build.py`, which derives one form
  per rendering mechanism into `dist/`.
- `tools/validate_identity.py`, the gate every pull request runs; `tools/check_touchpoint.py`, the
  five assertions a touchpoint's CI runs at its pinned tag; `tools/sweep_touchpoints.py`, run by the
  maintainer through the `identity-sweep` skill.
- The `identity-adopt` skill, the procedure that brings one touchpoint to a tag.
- Assertion 4 of `tools/check_touchpoint.py` treats a line that is verbatim a line of the host's
  `head.html` as the standard's own, so a host that cannot include the fragment may paste it, theme-color
  metas included, without a finding.
- `manifest.webmanifest` names its icons by addresses relative to itself, so a host that serves
  `hosts/<host>/` under a prefix (the marketing site at `/brand/hosts/idfkit.com/`) resolves them.
- The material derivation's `logo.svg` is the mark in the on-dark ink: the theme renders it through an
  `<img>`, where `currentColor` is black, and the header is navy in both schemes.
