# Changelog

All notable changes to the standard are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are the
`identity-YYYY.N` tags; the standard has no semantic version, since it has no API to break.

## [Unreleased]

## [identity-2026.1] - 2026-10-31

The first release of the standard. The owner reviewed every graphic on the contact sheet on both
grounds and then the hosts rendering them, and accepted them after the corrections below were made.

### Added

- The standard: `identity.tokens.json` for both themes, the mark and its masters, the self-hosted
  typefaces, the family links, the ownership line and the roster of touchpoints.
- `build.py`, which derives one form per rendering mechanism: hand-written sites, MkDocs Material and
  Zensical sites, the application, the sign-in widget, the marketing site's scene, README images,
  repository social previews, per-host files and the brand page.
- A lockup generated for every host, with its name outlined and its gap and size fixed, which
  `lockup.css` paints in the standard's ink on any header and under forced colours.
- `tools/validate_identity.py`, the gate every pull request runs, which measures every text pair in
  both themes against its contrast threshold.
- `tools/check_touchpoint.py` and the reusable `check-touchpoint.yml`, the six assertions a touchpoint's
  CI runs at its pinned tag, including that a host loads its lockup and draws no mark by hand.
- The `identity-adopt` and `identity-sweep` skills: the procedure that brings a touchpoint to a tag, and
  the report of who is behind.
- Exceptions recorded in the roster: ten parts the hosted sign-in widget cannot express, the stock API
  pages of the MCP deployment, and the application's dark accent on its own raised surface.

[Unreleased]: https://github.com/idfkit/idfkit-brand/compare/identity-2026.1...HEAD
[identity-2026.1]: https://github.com/idfkit/idfkit-brand/releases/tag/identity-2026.1
