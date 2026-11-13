---
name: idfkit-slides
description: Build PowerPoint decks in the idfkit visual identity, using the slides derivation of idfkit-brand. Use when asked for an idfkit presentation, deck, slides, workshop or talk, or for a .pptx that should carry the idfkit brand.
---

# idfkit-slides

A PowerPoint design system derived from `idfkit-brand` by `build.py`. Its source is `slides/` in that
repository; each `identity-YYYY.N` release attaches it, with the tag's tokens, marks and fonts, as
`slides.tar.gz`. The tag this copy was built from is in `tokens/IDENTITY_TAG`. Colours and spacing are
read from `tokens/identity.tokens.json` and never restated in the library.

## 1. Install

Install it as a personal Claude Code skill, from a release:

```bash
TAG=identity-YYYY.N   # a release that attaches slides.tar.gz: identity-2026.6 or later
DEST=~/.claude/skills/idfkit-slides
mkdir -p "$DEST"
gh release download "$TAG" -R idfkit/idfkit-brand -p slides.tar.gz -O - | tar -xz -C "$DEST"
(cd "$DEST" && npm ci)
```

or from a checkout of `idfkit-brand`, which stamps the tag as `unreleased`: `make slides-install`.

## 2. Build a deck

Load the `pptx` skill when it is available, for its pptxgenjs rules. Then write a script:

```js
const os = require("os"), path = require("path");
const ds = require(path.join(os.homedir(), ".claude/skills/idfkit-slides/lib/idfkit-slides.js"));

const pres = ds.createDeck({ title: "Deck title", author: "Author", footer: "Footer text" });
pres.addSection({ title: "Introduction" });
ds.addTitle(pres, { sectionTitle: "Introduction", eyebrow: "EYEBROW", title: "Title", subtitle: "Subtitle", meta: "Name | Date", notes: "Speaker notes." });
const s = ds.addContent(pres, { sectionTitle: "Introduction", eyebrow: "EYEBROW", title: "One message", notes: "Speaker notes." });
ds.card(pres, s, { x: ds.SLIDE.margin, y: ds.SLIDE.contentTop, w: 6, h: 2.3, heading: "Heading", body: "Body." });
ds.save(pres, "deck.pptx");
```

Run it with `NODE_PATH=~/.claude/skills/idfkit-slides/node_modules node build_deck.js`. `save` also
writes the identity's colours into the deck's theme (`lib/theme.js`).

`example/build_example.js` builds the reference deck, which uses every frame and component once. Read
it before composing a slide the table in section 4 does not cover.

## 3. Check a deck

```bash
node ~/.claude/skills/idfkit-slides/bin/qa.js deck.pptx [out-dir]
```

It confirms that the theme carries the identity's colours and that every colour is six hex digits,
renders the deck to PDF with LibreOffice while Inter and JetBrains Mono are installed for that run
only, and confirms with `pdffonts` that both families are embedded. Then open the PDF and inspect every
slide. When the `pptx` skill is loaded, also run its schema validation.

## 4. What the system provides

| Export | Use |
| ------ | --- |
| `addTitle`, `addDivider`, `addContent` | The three slide frames: dark title, dark divider, light content |
| `card`, `surface` | Raised panels on the light ground |
| `code` | Commands and code, on the dark code ground, in JetBrains Mono |
| `prompt` | A prompt for an AI assistant, as readable text |
| `stat`, `stepBadge`, `chain`, `arrow` | A large figure, a step number, a sequence of named boxes |
| `table`, `chartStyle` | A ruled table, and shared options for native charts |
| `SLIDE`, `TYPE`, `SPACE`, `RADIUS`, `HEX`, `FONT`, `THEME` | The values, for composing anything else |

Content sits between `SLIDE.contentTop` and `SLIDE.contentBottom`. One token pixel is 1/96 inch, so a
brand spacing value keeps its size on the 13.333 x 7.5 inch slide.

## 5. Rules

These come from the token file's own usage notes, or from this system's choices where noted.

1. The gradient is a surface for nothing that must be read. It appears only as `assets/bloom.png` on
   dark frames.
2. Blue is the one accent. Use `accent1` on light grounds and `accent2` on dark grounds.
3. Text in the code face covers code, commands, eyebrows and captions. Everything else is Inter.
4. Never redraw, recolour or restate the mark. Use the files in `assets/`.
5. System choice: titles are one line, left aligned, with no period. At 34 pt, a title holds about
   50 characters.
6. System choice: use no accent rules under titles and no edge stripes on cards.
7. Eyebrows and numbering must state something true, such as a step or a section.

## 6. Fonts

The `pptx` file names the fonts but does not embed them. `fonts/` holds Inter and JetBrains Mono under
the SIL Open Font License. Install them before presenting from PowerPoint, or the machine substitutes
other fonts. A PDF export embeds them, so distribute the PDF.

## 7. Changing the system

This copy is generated; do not edit it. A change to the library, the example or this file is made in
`idfkit-brand/slides/`, reviewed like any change to the standard, and reaches this skill with the next
tag. A new tag changes nothing here until the skill is installed again from that tag's release.
