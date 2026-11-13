"use strict";
// PowerPoint design system derived from idfkit-brand by build.py (dist/slides/). Colours and
// spacing are read from the tag's identity.tokens.json in tokens/, never restated here. 1 token px = 1/96 in on the 1280 x 720 canvas.

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const ASSETS = path.join(ROOT, "assets");
const IDENTITY_TAG = fs.readFileSync(path.join(ROOT, "tokens", "IDENTITY_TAG"), "utf8").trim();
const raw = JSON.parse(fs.readFileSync(path.join(ROOT, "tokens", "identity.tokens.json"), "utf8"));

const px = (value) => parseFloat(value) / 96;
// Height over width of a PNG, from its IHDR chunk, so an image keeps the proportions build.py gave it.
const aspect = (file) => {
  const header = fs.readFileSync(file).subarray(16, 24);
  return header.readUInt32BE(4) / header.readUInt32BE(0);
};
const hex = (name) => raw.color.primitive[name].$value.light.replace("#", "").toUpperCase();
const SPACE = Object.fromEntries(
  Object.entries(raw.space).filter(([k]) => !k.startsWith("$")).map(([k, v]) => [k, px(v.$value)]),
);
const RADIUS = Object.fromEntries(
  Object.entries(raw.radius).filter(([k]) => !k.startsWith("$")).map(([k, v]) => [k, px(v.$value)]),
);

const FONT = { text: raw.font.family.text.$value, code: raw.font.family.code.$value };
const SLIDE = { w: 13.333, h: 7.5, margin: SPACE["6"], contentTop: 1.75, contentBottom: 6.75 };
SLIDE.contentW = SLIDE.w - 2 * SLIDE.margin;
SLIDE.contentH = SLIDE.contentBottom - SLIDE.contentTop;

const TYPE = { display: 54, title: 34, heading: 22, body: 18, small: 16, caption: 12, eyebrow: 13, code: 16 };

// Theme slots map brand roles, so a restyle happens in one place.
const THEME = {
  name: `idfkit ${IDENTITY_TAG}`,
  headFontFace: FONT.text,
  bodyFontFace: FONT.text,
  colors: {
    dk1: hex("slate-950"), // ink on light grounds
    lt1: hex("white"), // light ground
    dk2: hex("navy-950"), // dark ground
    lt2: hex("slate-100"), // raised surface on light
    accent1: hex("blue-600"), // accent on light
    accent2: hex("blue-500"), // accent on dark
    accent3: hex("violet-500"), // gradient only: never under text
    accent4: hex("red-600"), // error on light
    accent5: hex("slate-600"), // muted ink on light
    accent6: hex("slate-200"), // border on light, ink on dark
    hlink: hex("blue-600"),
    folHlink: hex("slate-600"),
  },
};

// Colours with no theme slot.
const HEX = {
  codeGround: hex("navy-900"),
  mutedOnDark: hex("slate-400"),
  success: hex("green-700"),
  warning: hex("amber-700"),
  heat: hex("red-600"),
  cool: hex("blue-600"),
  border: hex("slate-200"),
  ink: hex("slate-950"),
  muted: hex("slate-600"),
};

function createDeck({ title, author, subject, footer }) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = title;
  pres.author = author || "idfkit";
  pres.company = "idfkit";
  pres.subject = subject || title;
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const M = SLIDE.margin;
  const placeholder = (name, type, options) => ({ placeholder: { options: { name, type, margin: 0, align: "left", ...options }, text: "" } });

  pres.defineSlideMaster({
    title: "IF_TITLE",
    background: { color: C.text2 },
    objects: [
      { image: { path: path.join(ASSETS, "bloom.png"), x: 6.333, y: 0, w: 7, h: 7.5 } },
      { image: { path: path.join(ASSETS, "lockup-on-dark.png"), x: M, y: M, w: 2.3, h: 2.3 * aspect(path.join(ASSETS, "lockup-on-dark.png")) } },
      placeholder("eyebrow", "body", { x: M, y: 2.55, w: 9, h: 0.35, fontFace: FONT.code, fontSize: TYPE.eyebrow, color: C.accent2, valign: "middle" }),
      placeholder("title", "title", { x: M, y: 2.95, w: 10, h: 1.1, fontSize: TYPE.display, bold: true, color: C.background1, valign: "top" }),
      placeholder("subtitle", "body", { x: M, y: 4.1, w: 8.5, h: 0.95, fontSize: TYPE.heading, color: C.accent6, valign: "top" }),
      placeholder("meta", "body", { x: M, y: 6.3, w: 9, h: 0.4, fontSize: TYPE.small, color: HEX.mutedOnDark, valign: "middle" }),
    ],
  });

  pres.defineSlideMaster({
    title: "IF_DIVIDER",
    background: { color: C.text2 },
    objects: [
      { image: { path: path.join(ASSETS, "bloom.png"), x: 6.333, y: 0, w: 7, h: 7.5 } },
      { image: { path: path.join(ASSETS, "mark-on-dark.png"), x: M, y: M, w: 0.5, h: 0.5 } },
      placeholder("eyebrow", "body", { x: M, y: 2.5, w: 9, h: 0.35, fontFace: FONT.code, fontSize: TYPE.eyebrow, color: C.accent2, valign: "middle" }),
      placeholder("title", "title", { x: M, y: 2.9, w: 10.5, h: 1.0, fontSize: 44, bold: true, color: C.background1, valign: "top" }),
      placeholder("body", "body", { x: M, y: 3.95, w: 8.5, h: 1.3, fontSize: TYPE.heading, color: C.accent6, valign: "top" }),
    ],
    slideNumber: { x: 12.03, y: 6.95, w: 0.8, h: 0.3, fontFace: FONT.code, fontSize: TYPE.caption, color: HEX.mutedOnDark, align: "right" },
  });

  pres.defineSlideMaster({
    title: "IF_CONTENT",
    background: { color: C.background1 },
    objects: [
      placeholder("eyebrow", "body", { x: M, y: 0.42, w: SLIDE.contentW, h: 0.3, fontFace: FONT.code, fontSize: TYPE.eyebrow, color: C.accent1, valign: "middle" }),
      placeholder("title", "title", { x: M, y: 0.74, w: SLIDE.contentW, h: 0.75, fontSize: TYPE.title, bold: true, color: C.text1, valign: "middle" }),
      { image: { path: path.join(ASSETS, "mark-on-light.png"), x: M, y: 6.95, w: 0.28, h: 0.28 } },
      { text: { text: footer || "idfkit", options: { x: M + 0.38, y: 6.95, w: 8, h: 0.28, margin: 0, fontFace: FONT.code, fontSize: TYPE.caption, color: C.accent5, valign: "middle" } } },
    ],
    slideNumber: { x: 12.03, y: 6.95, w: 0.8, h: 0.28, fontFace: FONT.code, fontSize: TYPE.caption, color: C.accent5, align: "right" },
  });

  return pres;
}

function fill(slide, values) {
  for (const [placeholder, text] of Object.entries(values)) slide.addText(text, { placeholder });
}

function addTitle(pres, { eyebrow, title, subtitle, meta, notes, sectionTitle }) {
  const slide = pres.addSlide({ masterName: "IF_TITLE", sectionTitle });
  fill(slide, { eyebrow, title, subtitle, meta });
  if (notes) slide.addNotes(notes);
  return slide;
}

function addDivider(pres, { eyebrow, title, body, notes, sectionTitle }) {
  const slide = pres.addSlide({ masterName: "IF_DIVIDER", sectionTitle });
  fill(slide, { eyebrow, title, body });
  if (notes) slide.addNotes(notes);
  return slide;
}

function addContent(pres, { eyebrow, title, notes, sectionTitle }) {
  const slide = pres.addSlide({ masterName: "IF_CONTENT", sectionTitle });
  fill(slide, { eyebrow, title });
  if (notes) slide.addNotes(notes);
  return slide;
}

// Components. Each takes a fresh options object, because pptxgenjs mutates what it receives.

function surface(pres, slide, { x, y, w, h, color, name, radius }) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: radius === undefined ? RADIUS.lg : radius,
    fill: { color: color || pres.SchemeColor.background2 },
    line: { color: color || pres.SchemeColor.background2, width: 0 },
    objectName: name || "Surface",
  });
}

function card(pres, slide, { x, y, w, h, heading, body, badge, bodySize, name }) {
  const C = pres.SchemeColor;
  const pad = SPACE["3"];
  surface(pres, slide, { x, y, w, h, name: name || `Card: ${heading}` });
  let top = y + pad;
  if (badge) {
    slide.addText(badge, {
      x: x + pad, y: top, w: w - 2 * pad, h: 0.26, margin: 0, isTextBox: true,
      fontFace: FONT.code, fontSize: TYPE.caption, color: C.accent1, valign: "middle", objectName: "Card label",
    });
    top += 0.32;
  }
  slide.addText(heading, {
    x: x + pad, y: top, w: w - 2 * pad, h: 0.42, margin: 0, isTextBox: true,
    fontSize: TYPE.heading, bold: true, color: C.text1, valign: "top", objectName: "Card heading",
  });
  top += 0.48;
  if (body) {
    slide.addText(body, {
      x: x + pad, y: top, w: w - 2 * pad, h: y + h - top - pad, margin: 0, isTextBox: true,
      fontSize: bodySize || TYPE.small, color: C.accent5, valign: "top", paraSpaceAfter: 6, objectName: "Card body",
    });
  }
}

// lines: one string per line. A line starting with "#" reads as a comment.
function code(pres, slide, { x, y, w, h, lines, label, fontSize }) {
  const C = pres.SchemeColor;
  const pad = SPACE["3"];
  surface(pres, slide, { x, y, w, h, color: HEX.codeGround, name: `Code: ${label || "block"}` });
  let top = y + pad * 0.75;
  if (label) {
    slide.addText(label, {
      x: x + pad, y: top, w: w - 2 * pad, h: 0.26, margin: 0, isTextBox: true,
      fontFace: FONT.code, fontSize: TYPE.caption, color: HEX.mutedOnDark, valign: "middle", objectName: "Code label",
    });
    top += 0.34;
  }
  const runs = lines.map((line, index) => ({
    text: line,
    options: {
      color: line.trimStart().startsWith("#") ? HEX.mutedOnDark : C.accent6,
      breakLine: index < lines.length - 1,
    },
  }));
  slide.addText(runs, {
    x: x + pad, y: top, w: w - 2 * pad, h: y + h - top - pad * 0.6, margin: 0, isTextBox: true,
    fontFace: FONT.code, fontSize: fontSize || TYPE.code, valign: "top", objectName: "Code",
  });
}

function prompt(pres, slide, { x, y, w, h, text, label, fontSize }) {
  const C = pres.SchemeColor;
  const pad = SPACE["4"];
  surface(pres, slide, { x, y, w, h, name: "Prompt" });
  slide.addText(label || "PROMPT FOR CLAUDE CODE", {
    x: x + pad, y: y + 0.25, w: w - 2 * pad, h: 0.26, margin: 0, isTextBox: true,
    fontFace: FONT.code, fontSize: TYPE.caption, color: C.accent1, valign: "middle", objectName: "Prompt label",
  });
  slide.addText(text, {
    x: x + pad, y: y + 0.62, w: w - 2 * pad, h: h - 0.62 - 0.25, margin: 0, isTextBox: true,
    fontSize: fontSize || 20, color: C.text1, valign: "top", objectName: "Prompt text",
  });
}

function stat(pres, slide, { x, y, w, value, label, color, valueSize }) {
  const C = pres.SchemeColor;
  const size = valueSize || 44;
  const valueH = (size / 72) * 1.3;
  slide.addText(value, {
    x, y, w, h: valueH, margin: 0, isTextBox: true,
    fontSize: size, bold: true, color: color || C.accent1, valign: "top", objectName: "Stat value",
  });
  slide.addText(label, {
    x, y: y + valueH + 0.04, w, h: 0.6, margin: 0, isTextBox: true,
    fontSize: TYPE.small, color: C.accent5, valign: "top", objectName: "Stat label",
  });
}

function stepBadge(pres, slide, { x, y, size, text }) {
  const C = pres.SchemeColor;
  slide.addText(text, {
    shape: pres.ShapeType.ellipse, x, y, w: size, h: size, margin: 0,
    fill: { color: C.accent1 }, color: C.background1, fontSize: TYPE.small, bold: true,
    align: "center", valign: "middle", objectName: "Step number",
  });
}

function arrow(pres, slide, { x, y, w, h, flip }) {
  const C = pres.SchemeColor;
  slide.addShape(flip ? pres.ShapeType.leftArrow : pres.ShapeType.rightArrow, {
    x, y, w, h, fill: { color: C.accent5 }, line: { color: C.accent5, width: 0 }, objectName: "Arrow",
  });
}

// A horizontal chain of labelled boxes joined by arrows. reversed lists the gaps whose arrow points left.
function chain(pres, slide, { x, y, w, h, items, fontFace, fontSize, reversed }) {
  const C = pres.SchemeColor;
  const gap = 0.42;
  const boxW = (w - gap * (items.length - 1)) / items.length;
  items.forEach((item, index) => {
    const boxX = x + index * (boxW + gap);
    surface(pres, slide, { x: boxX, y, w: boxW, h, name: `Chain: ${item}`, radius: RADIUS.md });
    slide.addText(item, {
      x: boxX + 0.06, y, w: boxW - 0.12, h, margin: 0, isTextBox: true, align: "center", valign: "middle",
      fontFace: fontFace || FONT.code, fontSize: fontSize || TYPE.small, color: C.text1, objectName: "Chain label",
    });
    if (index < items.length - 1) {
      const flip = Boolean(reversed && reversed.includes(index));
      arrow(pres, slide, { x: boxX + boxW + 0.09, y: y + h / 2 - 0.12, w: 0.24, h: 0.24, flip });
    }
  });
}

function table(pres, slide, { x, y, w, colW, header, rows, fontSize, rowH }) {
  const C = pres.SchemeColor;
  const size = fontSize || TYPE.small;
  const edge = { type: "solid", pt: 1, color: HEX.border };
  const none = { type: "none" };
  const borders = [none, none, edge, none];
  const cell = (text, options) => ({ text, options: { border: borders, margin: [0.07, 0.12, 0.07, 0.12], valign: "middle", ...options } });
  const data = [
    header.map((text) => cell(text, { bold: true, color: C.text1, fontSize: size })),
    ...rows.map((row) => row.map((text, index) => cell(text, { color: index === 0 ? C.text1 : C.accent5, bold: index === 0, fontSize: size }))),
  ];
  slide.addTable(data, { x, y, w, colW, rowH, objectName: "Table" });
}

function chartStyle() {
  return {
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt",
    catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, dataLabelColor: HEX.ink, legendColor: HEX.muted,
    catAxisLabelFontSize: 14, valAxisLabelFontSize: 12, dataLabelFontSize: 14, legendFontSize: 14,
    valGridLine: { color: HEX.border, size: 1 }, catGridLine: { style: "none" },
  };
}

async function save(pres, fileName) {
  const { applyTheme } = require("./theme.js");
  await pres.writeFile({ fileName });
  await applyTheme(fileName, THEME);
}

module.exports = {
  IDENTITY_TAG, THEME, HEX, FONT, TYPE, SPACE, RADIUS, SLIDE, ASSETS,
  createDeck, addTitle, addDivider, addContent, surface, card, code, prompt, stat, stepBadge, arrow, chain, table, chartStyle, save,
};
