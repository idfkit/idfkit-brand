"use strict";
// The reference deck: every frame and component once, on the layout the system expects.
//
//   node example/build_example.js [out.pptx]

const fs = require("fs");
const path = require("path");
const ds = require("../lib/idfkit-slides.js");

const { SLIDE, TYPE } = ds;
const M = SLIDE.margin;
const W = SLIDE.contentW;
const TOP = SLIDE.contentTop;
const GAP = 0.3;
const section = "Reference";

const pres = ds.createDeck({ title: "idfkit slides", author: "idfkit", footer: "idfkit slides" });
pres.addSection({ title: section });

ds.addTitle(pres, {
  sectionTitle: section,
  eyebrow: "REFERENCE DECK",
  title: "idfkit slides",
  subtitle: "Every frame and component of the design system, once.",
  meta: `Identity ${ds.IDENTITY_TAG}`,
  notes: "The dark title frame: eyebrow, title, subtitle and a meta line over the bloom.",
});

ds.addDivider(pres, {
  sectionTitle: section,
  eyebrow: "PART 1",
  title: "A section divider",
  body: "One sentence that states what the section is for.",
  notes: "The dark divider frame.",
});

{
  const s = ds.addContent(pres, {
    sectionTitle: section,
    eyebrow: "CARDS AND FIGURES",
    title: "One message per slide, in one line",
    notes: "The light content frame with two cards and two figures.",
  });
  const w = (W - GAP) / 2;
  ds.card(pres, s, { x: M, y: TOP, w, h: 2.2, heading: "A card", body: "A raised panel for one idea, with a heading and a short body." });
  ds.card(pres, s, { x: M + w + GAP, y: TOP, w, h: 2.2, heading: "Another card", badge: "STEP 2", body: "A badge numbers the card when the order is real." });
  ds.stat(pres, s, { x: M, y: TOP + 2.6, w, value: "77.7", label: "Heating, kWh/m² per year" });
  ds.stat(pres, s, { x: M + w + GAP, y: TOP + 2.6, w, value: "50.7", label: "Cooling, kWh/m² per year" });
}

{
  const s = ds.addContent(pres, {
    sectionTitle: section,
    eyebrow: "CODE AND PROMPTS",
    title: "Commands in the code face, prompts as prose",
    notes: "The code block and the prompt block, with a chain beneath.",
  });
  const w = (W - GAP) / 2;
  ds.code(pres, s, { x: M, y: TOP, w, h: 1.6, label: "IN YOUR TERMINAL", lines: ["uv add idfkit", "uv run python model.py"] });
  ds.prompt(pres, s, { x: M + w + GAP, y: TOP, w, h: 1.6, label: "ASK CLAUDE", text: "Build a two-storey office in Montreal and simulate it." });
  ds.chain(pres, s, { x: M, y: TOP + 2.2, w: W, h: 0.9, items: ["Model", "Validate", "Simulate", "Review"] });
}

{
  const s = ds.addContent(pres, {
    sectionTitle: section,
    eyebrow: "TABLES AND CHARTS",
    title: "A ruled table beside a native chart",
    notes: "The table component and a bar chart using chartStyle.",
  });
  const w = (W - GAP) / 2;
  ds.table(pres, s, {
    x: M, y: TOP, w, colW: [w * 0.45, w * 0.55],
    header: ["Tool", "Purpose"],
    rows: [["uv", "Environments"], ["EnergyPlus", "Simulation"], ["idfkit", "Models in code"]],
  });
  s.addChart(pres.charts.BAR, [{ name: "kWh/m²", labels: ["Heating", "Cooling"], values: [77.7, 50.7] }], {
    x: M + w + GAP, y: TOP, w, h: 3.6, barDir: "col", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0",
    chartColors: [ds.THEME.colors.accent1], showLegend: false, objectName: "Chart: annual loads",
    ...ds.chartStyle(),
  });
  s.addText("Values are illustrative.", { x: M, y: TOP + 4.3, w: W, h: 0.4, fontSize: TYPE.caption, color: ds.HEX.muted, margin: 0, isTextBox: true });
}

const out = path.resolve(process.argv[2] || "idfkit-slides-reference.pptx");
fs.mkdirSync(path.dirname(out), { recursive: true });
ds.save(pres, out).then(() => console.log(`written ${out}`));
