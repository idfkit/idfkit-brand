# The design record

Two PDFs record how the standard's direction and mark were chosen. Nothing is derived from either:
`identity.tokens.json` is the record of the values and `mark.py` is the record of the geometry.

## `2026-09-11-direction-comparison.pdf`

The comparison FR-001a requires. Three directions then in use across the family were drawn side by
side on the same content (a navigation bar, a hero, a card, a primary action, a code block, a
footer): the marketing site's navy ground with the blue-to-violet-to-red sweep and Inter with
JetBrains Mono; shoebox's drafting sheet, bond paper with graphite ink and a redline accent in IBM
Plex; and the sign-in page's indigo-black with a copper accent. The marketing site's direction was
chosen on 2026-09-11 (spec, Clarifications), with two costs carried into the standard as
requirements: a light theme designed under FR-014, and no readable text on the gradient under
FR-015. The PDF was rendered on 2026-10-30 from the three hosts' stylesheets as they stood on that
date, so that the comparison the decision was made on survives in the repository.

## `2026-10-30-mark-exploration.pdf`

The nine boards of the canvas [idfkit Brand Mark](https://claude.ai/artifact/GdC1DUcYxgFBRL2DyvxS76),
exported on 2026-10-30: the overview, the six directions each on dark and light at 160, 48, 32, 24
and 16 pixels (Block Bolt, a geometric lightning cut-out; Part, a block with one piece lifted out;
Zone, a half-filled isometric block; Semicolon, the IDF terminator squared off; an "ik" monogram;
Boundary, a diagonal split), the suite lockups, and the refinement board with the construction
grid, the radius options and the small-size redraw.

Part was chosen because it describes the suite (a kit of parts that fit together) and the format
(an IDF model is objects assembled into a building), because it is the only one of the six that can
be described in one sentence excluding every neighbouring mark that was found, and because it
survives 16 pixels without a redraw of its idea. A trademark image search on 2026-10-30 found
nothing comparable (research R5). The canvas is a working surface; the geometry it settled on is
written once, in `mark.py`.
