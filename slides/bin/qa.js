#!/usr/bin/env node
"use strict";
// Checks a deck built on this system and renders it to PDF for inspection.
//
//   node bin/qa.js deck.pptx [out-dir]
//
// 1. The theme carries this system's colours, and every colour in the deck is six hex digits.
// 2. LibreOffice renders the deck to PDF with Inter and JetBrains Mono installed for the run only,
//    so the preview measures text with the real fonts. The PDF lands in out-dir (default: beside the deck).
// 3. pdffonts, when present, confirms that both families are embedded.
// Exit status 1 on any failure. Needs LibreOffice; pdffonts (poppler) is optional.

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");
const JSZip = require("jszip");
const { THEME } = require("../lib/idfkit-slides.js");

const FONTS = path.resolve(__dirname, "..", "fonts");
const HEX6 = /^[0-9A-Fa-f]{6}$/;

function fail(message) {
  console.error(`qa: FAIL ${message}`);
  process.exitCode = 1;
}

async function checkColours(deck) {
  const zip = await JSZip.loadAsync(fs.readFileSync(deck));
  const theme = zip.file(/^ppt\/theme\/theme\d+\.xml$/)[0];
  if (!theme) return fail("the deck has no theme part");
  const xml = await theme.async("string");
  const accent = xml.match(/<a:accent1><a:srgbClr val="([0-9A-Fa-f]{6})"/);
  if (!accent || accent[1].toUpperCase() !== THEME.colors.accent1) fail("the theme's accent1 is not the identity accent; build the deck with ds.save");
  for (const part of zip.file(/^ppt\/(slides|slideLayouts|slideMasters|charts)\/[^/]+\.xml$/)) {
    for (const match of (await part.async("string")).matchAll(/<a:srgbClr val="([^"]*)"/g)) {
      if (!HEX6.test(match[1])) fail(`${part.name}: colour "${match[1]}" is not six hex digits`);
    }
  }
  console.log("qa: theme and colours checked");
}

function soffice() {
  const candidates = ["soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice"];
  return candidates.find((candidate) => spawnSync(candidate, ["--version"], { stdio: "ignore" }).status === 0);
}

function userFontDir() {
  const base = process.platform === "darwin" ? path.join(os.homedir(), "Library", "Fonts") : path.join(os.homedir(), ".local", "share", "fonts");
  return path.join(base, "idfkit-slides-qa");
}

function render(deck, outDir) {
  const binary = soffice();
  if (!binary) return fail("LibreOffice (soffice) was not found; install it to render the deck");
  // A PDF left by an earlier run would otherwise pass for this one when LibreOffice writes nothing.
  const pdf = path.join(outDir, `${path.basename(deck, path.extname(deck))}.pdf`);
  fs.rmSync(pdf, { force: true });
  const fontDir = userFontDir();
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "idfkit-slides-lo-"));
  fs.mkdirSync(fontDir, { recursive: true });
  for (const name of fs.readdirSync(FONTS).filter((file) => file.endsWith(".ttf"))) fs.copyFileSync(path.join(FONTS, name), path.join(fontDir, name));
  try {
    execFileSync(binary, [`-env:UserInstallation=file://${profile}`, "--headless", "--convert-to", "pdf", "--outdir", outDir, deck], { stdio: "ignore", timeout: 180000 });
  } finally {
    fs.rmSync(fontDir, { recursive: true, force: true });
    fs.rmSync(profile, { recursive: true, force: true });
  }
  if (!fs.existsSync(pdf)) return fail("LibreOffice wrote no PDF");
  console.log(`qa: rendered ${pdf}`);
  return pdf;
}

function checkFonts(pdf) {
  const result = spawnSync("pdffonts", [pdf], { encoding: "utf8" });
  if (result.status !== 0) return console.log("qa: pdffonts not found; embedded fonts not checked");
  // Columns are fixed-width under a row of dashes; the fourth is "emb". A type such as "Type 1C" holds a space.
  const [, dashes = "", ...rows] = result.stdout.split("\n");
  const columns = [...dashes.matchAll(/-+/g)].map((match) => [match.index, match.index + match[0].length]);
  const cell = (row, index) => (columns[index] ? row.slice(...columns[index]).trim() : "");
  const embedded = rows.filter((row) => cell(row, 3) === "yes").map((row) => cell(row, 0));
  for (const family of ["Inter", "JetBrainsMono"]) {
    if (!embedded.some((name) => name.replace(/^[A-Z]{6}\+/, "").startsWith(family))) {
      fail(`${family} is not embedded in the PDF; the renderer substituted another font or left it out`);
    }
  }
  console.log("qa: fonts checked");
}

async function main() {
  const [deckArg, outArg] = process.argv.slice(2);
  if (!deckArg) {
    console.error("usage: node bin/qa.js deck.pptx [out-dir]");
    process.exit(2);
  }
  const deck = path.resolve(deckArg);
  const outDir = path.resolve(outArg || path.dirname(deck));
  fs.mkdirSync(outDir, { recursive: true });
  await checkColours(deck);
  const pdf = render(deck, outDir);
  if (pdf) checkFonts(pdf);
  if (!process.exitCode) console.log("qa: passed; open the PDF and inspect every slide");
}

main().catch((error) => fail(error.message));
