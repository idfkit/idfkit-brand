# idfkit-brand

The idfkit visual identity standard: one token file, one mark, two typefaces, a roster of the
surfaces that render them, and a build that derives one form per rendering mechanism. Every idfkit
web host and every public README obtains its identity values from a released tag of this
repository and nowhere else.

## 1. What the standard is

| Path | Holds |
| ---- | ----- |
| `identity.tokens.json` | every colour (both themes), type, spacing, radius, elevation and motion value, in the Design Tokens Community Group format |
| `mark.py`, `marks/` | the mark's geometry and the SVG masters generated from it; `marks/wordmark.svg` is the one outlined, committed master |
| `fonts/` | Inter and JetBrains Mono as Latin woff2 subsets with their licences, and TTF copies the build sets text with |
| `touchpoints.toml` | the roster: the family links, the ownership line, every host and README, their exceptions. Never a level |
| `templates/` | the social images, the head fragment, the family links, the footer, the brand page |
| `build.py` | source to `dist/`: `css`, `material`, `envelop`, `stytch`, `hero`, `readme`, `repo-preview`, `hosts`, `brand-page`, and the local contact sheet `review/` |
| `tools/` | `validate_identity.py` (the gate), `check_touchpoint.py` (the six assertions a touchpoint's CI runs), `sweep_touchpoints.py` (who is behind) |
| `design/` | the direction comparison and the mark exploration, as PDF |

The contracts that fix each of these are in the planning repository, under
`specs/008-unified-visual-identity/contracts/`: `identity-standard.md`, `derivations.md`,
`touchpoint-check.md` and `readme-header.md`.

## 2. How to change a value

1. Edit `identity.tokens.json`. A colour role aliases a primitive; a new primitive carries both
   themes and a usage. The mark's shapes are edited in `mark.py` only, then `python mark.py --write`
   regenerates `marks/`.
2. Run `make check`: the quality tools, then `tools/validate_identity.py`, which parses the file,
   resolves every alias, measures every text-on-ground pair in both themes against its threshold,
   scans the templates for literals, checks the roster, and compares the committed masters with
   `mark.py`'s output. A pair under its threshold is a failure, not a note.
3. Run `make build` and open `dist/review/index.html`, the contact sheet of every image produced,
   on the light ground and the dark ground. The owner reviews it before any tag that changes a
   template or a mark.
4. Open a pull request. The owner reviews the source files (`.github/CODEOWNERS`).

Nothing reaches a touchpoint until the change is tagged.

## 3. How to cut a tag

Tags are `identity-YYYY.N`: the next number within the year, the year resetting the counter. From
the merged commit on `main`, with `identity.yml` green:

```bash
git tag identity-2026.1 && git push origin identity-2026.1
```

`identity.yml` builds `dist/` at the tag and creates the GitHub release with one archive per
mechanism directory and the five images attached loose for download. A README addresses the masters
in `marks/` at the tag instead, since a browser will not display an SVG served as a release asset. A
tag never moves once a touchpoint declares it; a mistake is a new tag.

## 4. How to adopt one

Adoption is a procedure the maintainer runs through an agent, not a script in the touchpoint:

- **`identity-adopt`** (`.claude/skills/identity-adopt/`): given a touchpoint id and a tag, reads
  the roster entry, builds the tag here, copies `dist/` into the touchpoint's vendored paths, moves
  its declaration and its check workflow's ref, runs `tools/check_touchpoint.py` against the local
  `dist`, and opens the pull request. A README touchpoint changes three image addresses instead.
- **`identity-sweep`** (`.claude/skills/identity-sweep/`): reads every touchpoint's declared tag
  from its own checkout and reports who is behind, with the stated lag or `unexplained`.

Both are offered whenever the workspace is open. The only code a touchpoint runs is the check: its
`.github/workflows/check-identity.yml` calls `check-touchpoint.yml` from this repository at the
tag it declares, which fails when a vendored file differs from the tag's, when its own stylesheet
carries a stray colour or font literal, or when a README's header departs from the contract.

## 5. Development

```bash
make install   # uv sync and the pre-commit hooks
make check     # lint, format, pyright, the validator, the mark check
make test      # pytest: the token file, the validator, the mark, the build, the check, the sweep
make build     # dist/ with the contact sheet (needs rsvg-convert from librsvg on PATH)
```

Standard library only, Python 3.12.
