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
| `touchpoints.toml` | the roster: the family links, the ownership line, every host, every root README and every published package's README, their exceptions. Never a level |
| `templates/` | the social images, the head fragment, the family links, the footer, the attribution line, the web manifest, the brand page |
| `build.py` | source to `dist/`: `css`, `material`, `envelop`, `stytch`, `hero`, `readme`, `repo-preview`, `avatar`, `hosts`, `brand-page`, and the local contact sheet `review/` |
| `providers/` | `stytch-styles.json`, the sign-in provider's widget style schema that `build.py` resolves into `dist/stytch/` |
| `tools/` | `validate_identity.py` (the gate), `check_touchpoint.py` (the six assertions a touchpoint's CI runs), `sweep_touchpoints.py` (who is behind), and the modules they share: `models.py` (typed records for the token file and the roster), `glyphs.py` (text set as outlines), `rasters.py` (PNG and ICO decoding, pixel comparison) |
| `tests/` | the pytest suite `make test` runs |
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
4. Open a pull request. The owner reviews changes to `identity.tokens.json`, `mark.py`, `marks/`,
   `touchpoints.toml` and `templates/` (`.github/CODEOWNERS`); no code owner is assigned to the
   other paths.

Nothing reaches a touchpoint until the change is tagged.

## 3. How to cut a tag

Tags are `identity-YYYY.N`: the next number within the year, the year resetting the counter. From
the merged commit on `main`, with `identity.yml` green:

```bash
git tag identity-YYYY.N && git push origin identity-YYYY.N
```

`identity.yml` builds `dist/` at the tag and creates the GitHub release with one archive per
mechanism directory and the six images attached loose for download, then deploys the brand page
from that build to brand.idfkit.com through GitHub Pages. A README addresses the masters
in `marks/` at the tag instead, since a browser will not display an SVG served as a release asset. A
tag never moves once a touchpoint declares it; a mistake is a new tag.

## 4. How to adopt one

Adoption is a procedure the maintainer runs through an agent, not a script in the touchpoint:

- **`identity-adopt`** (`.claude/skills/identity-adopt/`): given a touchpoint id and a tag, reads
  the roster entry, builds the tag here, copies `dist/` into the touchpoint's vendored paths, moves
  its declaration and its check workflow's ref, runs `tools/check_touchpoint.py` against the local
  `dist`, and opens the pull request. A README touchpoint changes three image addresses instead, and the package READMEs of its repository move with it.
- **`identity-sweep`** (`.claude/skills/identity-sweep/`): reads every touchpoint's declared tag
  from its own checkout and reports who is behind, with the stated lag or `unexplained`.

Both are project skills of this repository, so they are offered to an agent session whose working
directory is this checkout. The only code a touchpoint runs is the check: its
`.github/workflows/check-identity.yml` calls `check-touchpoint.yml` from this repository at the
tag it declares. The check runs six assertions (`tools/check_touchpoint.py`) and fails when the
repository is missing from the roster or exhibits other mechanisms than it records, when the
declared level does not resolve, differs from the tag checked or names no tag, when a vendored file
differs from the tag's, when an identity-bearing file carries a stray colour, font family, font face
or font host, when a README's header departs from the contract, or when a host does not load its
generated `lockup.css` from the file the roster names or draws the mark by hand.

## 5. Development

```bash
make install   # uv sync and the pre-commit hooks
make check     # lint, format, pyright, the validator, the mark check
make test      # pytest: the token file, the validator, the mark, the build, the check, the sweep
make build     # dist/ with the contact sheet (needs rsvg-convert from librsvg on PATH)
```

Standard library only, Python 3.12.
