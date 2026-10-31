# The masters

Every file in this directory except `wordmark.svg` is written by `mark.py` from the geometry that
module records; `python mark.py --check` fails when a committed file differs from that output, and
`identity.yml` runs it on every pull request. Edit `mark.py`, run `python mark.py --write`, and
commit the result. Never edit a generated master.

| File | Content |
| ---- | ------- |
| `mark.svg` | The mark in `currentColor`, 48-unit grid |
| `mark-on-light.svg`, `mark-on-dark.svg` | The mark with a fixed ink (`#0b1020`, `#e2e8f0`) for tools that cannot inherit colour |
| `mark-small.svg` | The 16-unit redraw with integer edges, in `currentColor`; the source of the 16 and 32 px rasters |
| `tile.svg` | The mark reversed out of the navy ground, 512 units, corners at 22 percent |
| `lockup.svg`, `lockup-on-light.svg`, `lockup-on-dark.svg` | Mark and wordmark, cropped to the ink |
| `wordmark.svg` | The outlined wordmark alone, in `currentColor`; committed, not generated |

## The wordmark

`wordmark.svg` is "idfkit", lowercase, set in Inter ExtraBold with letter spacing of -0.035 em,
shaped with HarfBuzz and converted to outlines on 2026-10-30, so that it renders without the font
installed. Its `data-baseline` attribute carries the baseline the lockup aligns the mark to. To
re-outline it, set the same string in the same face and tracking, convert to outlines, and replace
the file keeping `data-baseline`, `viewBox` and the single `<path>`; `mark.py` reads those.

The property lockups (the lockup, a divider, and a property name in the label face) are not
masters: `build.py` composes them for each host's social image from `mark.py`'s
`svg_property_lockup`.
