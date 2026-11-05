"use strict";
// Writes the identity's colours and name into a deck's theme parts. pptxgenjs sets the theme's two
// fonts but always writes Office's stock colour scheme, so without this step every scheme colour in
// the deck resolves to Office blue and orange.

const fs = require("fs");
const JSZip = require("jszip");

const SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
const HEX6 = /^[0-9A-Fa-f]{6}$/;
const THEME_PART = /^ppt\/theme\/theme\d+\.xml$/;
const CHECKED_PART = /^ppt\/(slides|slideLayouts|slideMasters|charts)\/[^/]+\.xml$/;

function escapeXml(value) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function colourScheme(theme) {
  const entries = SLOTS.map((slot) => {
    const value = theme.colors[slot];
    if (!HEX6.test(value || "")) throw new Error(`theme colour ${slot} is ${JSON.stringify(value)}, not six hex digits`);
    return `<a:${slot}><a:srgbClr val="${value.toUpperCase()}"/></a:${slot}>`;
  });
  return `<a:clrScheme name="${escapeXml(theme.name)}">${entries.join("")}</a:clrScheme>`;
}

// A scheme colour name passed to an option that only takes hex is written as an invalid srgbClr,
// which PowerPoint rejects. Refuse the deck, unchanged, and name the part.
async function rejectInvalidColours(zip) {
  for (const name of Object.keys(zip.files).filter((part) => CHECKED_PART.test(part))) {
    const xml = await zip.file(name).async("string");
    for (const match of xml.matchAll(/<a:srgbClr val="([^"]*)"/g)) {
      if (!HEX6.test(match[1])) {
        throw new Error(`${name}: colour "${match[1]}" is not six hex digits; a scheme colour was given to an option that takes hex`);
      }
    }
  }
}

async function applyTheme(fileName, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(fileName));
  const parts = Object.keys(zip.files).filter((part) => THEME_PART.test(part));
  if (parts.length === 0) throw new Error(`${fileName} has no theme part`);
  await rejectInvalidColours(zip);
  const scheme = colourScheme(theme);
  for (const name of parts) {
    const xml = await zip.file(name).async("string");
    const updated = xml
      .replace(/<a:clrScheme\b[^>]*>[\s\S]*?<\/a:clrScheme>/, scheme)
      .replace(/(<a:theme\b[^>]*\bname=")[^"]*(")/, `$1${escapeXml(theme.name)}$2`);
    zip.file(name, updated);
  }
  fs.writeFileSync(fileName, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

module.exports = { applyTheme };
