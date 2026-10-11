import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  NULL_DISPLAY,
  int,
  signed,
  rate3,
  pct1,
  pct1Sign,
  dec2,
  toi,
  date,
  gameTime,
  position,
  ordinal,
  season,
} from "./format.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));

// Run a snippet in a child Node with a fixed TZ. The snippet imports format.js and prints a
// JSON array of strings; we parse that and assert in the parent.
function runWithTz(tz, snippet) {
  const result = spawnSync(
    process.execPath,
    ["--input-type=module", "-e", snippet],
    {
      env: { ...process.env, TZ: tz },
      encoding: "utf8",
      cwd: HERE,
    },
  );
  if (result.status !== 0) {
    throw new Error(
      `child failed (status ${result.status}):\nstdout: ${result.stdout}\nstderr: ${result.stderr}`,
    );
  }
  return JSON.parse(result.stdout.trim());
}

// --- null fallback ---

test("every formatter returns '–' (U+2013) on null or undefined", () => {
  assert.equal(NULL_DISPLAY, "–");
  for (const lang of ["en", "fi"]) {
    assert.equal(int(null), NULL_DISPLAY);
    assert.equal(int(undefined), NULL_DISPLAY);
    assert.equal(signed(null, lang), NULL_DISPLAY);
    assert.equal(rate3(null, lang), NULL_DISPLAY);
    assert.equal(pct1(null, lang), NULL_DISPLAY);
    assert.equal(pct1Sign(null, lang), NULL_DISPLAY);
    assert.equal(dec2(null, lang), NULL_DISPLAY);
    assert.equal(toi(null, lang), NULL_DISPLAY);
    assert.equal(date(null, lang), NULL_DISPLAY);
    assert.equal(gameTime(null, lang), NULL_DISPLAY);
    assert.equal(position(null, lang), NULL_DISPLAY);
    assert.equal(ordinal(null, lang), NULL_DISPLAY);
  }
  assert.equal(season(null), NULL_DISPLAY);
  assert.equal(season(undefined), NULL_DISPLAY);
  assert.equal(season("202620"), NULL_DISPLAY); // wrong length
});

// --- int ---

test("int: 12 → '12'", () => {
  assert.equal(int(12), "12");
  assert.equal(int(0), "0");
});

// --- signed: U+2212 in both languages ---

test("signed: U+2212 in EN and FI; '+' for positive; '0' for zero", () => {
  assert.equal(signed(-1, "en"), "−1");
  assert.equal(signed(-1, "fi"), "−1");
  // Make sure the minus is U+2212, not U+002D.
  assert.equal(signed(-1, "en").charCodeAt(0), 0x2212);
  assert.equal(signed(-1, "fi").charCodeAt(0), 0x2212);
  assert.equal(signed(2, "en"), "+2");
  assert.equal(signed(2, "fi"), "+2");
  assert.equal(signed(0, "en"), "0");
  assert.equal(signed(0, "fi"), "0");
});

// --- rate3 ---

test("rate3 edges: EN .900/1.000/.000; FI 90,00/100,00/0,00", () => {
  assert.equal(rate3(0.9, "en"), ".900");
  assert.equal(rate3(1.0, "en"), "1.000");
  assert.equal(rate3(0.0, "en"), ".000");
  assert.equal(rate3(0.9, "fi"), "90,00");
  assert.equal(rate3(1.0, "fi"), "100,00");
  assert.equal(rate3(0.0, "fi"), "0,00");
});

test("rate3 precision: 0.9157 → EN '.916', FI '91,57' (exact, no trailing % or NBSP)", () => {
  assert.equal(rate3(0.9157, "en"), ".916");
  assert.equal(rate3(0.9157, "fi"), "91,57");
});

// --- pct1 (×100, no % sign) ---

test("pct1 ×100: 0.143 → EN '14.3', FI '14,3'", () => {
  assert.equal(pct1(0.143, "en"), "14.3");
  assert.equal(pct1(0.143, "fi"), "14,3");
  // A straight decimal format of the raw fraction would give '0.1'/'0,1'.
  assert.notEqual(pct1(0.143, "en"), "0.1");
  assert.notEqual(pct1(0.143, "fi"), "0,1");
});

// --- pct1Sign (NBSP in FI, tight in EN) ---

test("pct1Sign: EN '14.3%' (no space), FI '14,3 %' with NBSP U+00A0", () => {
  const en = pct1Sign(0.143, "en");
  assert.equal(en, "14.3%");
  const fi = pct1Sign(0.143, "fi");
  // Expect '14,3' + NBSP + '%'
  assert.equal(fi.length, 6);
  assert.equal(fi.charCodeAt(0), "1".charCodeAt(0));
  assert.equal(fi.charCodeAt(1), "4".charCodeAt(0));
  assert.equal(fi.charCodeAt(2), ",".charCodeAt(0));
  assert.equal(fi.charCodeAt(3), "3".charCodeAt(0));
  assert.equal(fi.charCodeAt(4), 0x00a0, "NBSP between number and %");
  assert.equal(fi.charCodeAt(5), "%".charCodeAt(0));
});

// --- dec2 ---

test("dec2: 2.05 → EN '2.05', FI '2,05'", () => {
  assert.equal(dec2(2.05, "en"), "2.05");
  assert.equal(dec2(2.05, "fi"), "2,05");
});

// --- toi ---

test("toi: 10552 → EN '175:52', FI '175.52'", () => {
  assert.equal(toi(10552, "en"), "175:52");
  assert.equal(toi(10552, "fi"), "175.52");
});

test("toi: 963 → EN '16:03'", () => {
  assert.equal(toi(963, "en"), "16:03");
  assert.equal(toi(963, "fi"), "16.03");
});

// --- position ---

test("position: EN C/L/R/D/G; FI KH/VL/OL/P/MV", () => {
  for (const [code, en, fi] of [
    ["C", "C", "KH"],
    ["L", "L", "VL"],
    ["R", "R", "OL"],
    ["D", "D", "P"],
    ["G", "G", "MV"],
  ]) {
    assert.equal(position(code, "en"), en);
    assert.equal(position(code, "fi"), fi);
  }
});

// --- date: UTC-noon parse ---

test("date: '2026-10-02' renders EN 'Oct 2, 2026', FI '2.10.2026'", () => {
  assert.equal(date("2026-10-02", "en"), "Oct 2, 2026");
  assert.equal(date("2026-10-02", "fi"), "2.10.2026");
});

test("date west of UTC: TZ=America/Los_Angeles still renders Oct 2, not Oct 1 (gotcha row)", () => {
  const [out] = runWithTz(
    "America/Los_Angeles",
    `import { date } from "./format.js";
     process.stdout.write(JSON.stringify([date("2026-10-02", "en")]));`,
  );
  assert.equal(out, "Oct 2, 2026");
});

test("date east of UTC: TZ=Pacific/Kiritimati still renders Oct 2", () => {
  // UTC+14 is the extreme east. Local midnight at UTC+14 is 10:00 UTC the previous day;
  // our UTC-noon parse puts the date safely at UTC noon so the day doesn't shift either way.
  const [out] = runWithTz(
    "Pacific/Kiritimati",
    `import { date } from "./format.js";
     process.stdout.write(JSON.stringify([date("2026-10-02", "en")]));`,
  );
  assert.equal(out, "Oct 2, 2026");
});

// --- gameTime: viewer-local tz, the day rolls over ---

test("gameTime FI under TZ=Europe/Helsinki: 2026-10-10T23:30:00Z → 'su 11.10. klo 2.30' (no leading zero, no zone)", () => {
  // The whole reason gameTime exists: for a Finnish viewer, a late Saturday-evening ET game
  // becomes Sunday 2:30 local time. hour: 'numeric' avoids the leading zero. No timeZoneName
  // in the output — FI's 'UTC+3' label adds nothing when the time is already viewer-local.
  const [out] = runWithTz(
    "Europe/Helsinki",
    `import { gameTime } from "./format.js";
     process.stdout.write(JSON.stringify([gameTime("2026-10-10T23:30:00Z", "fi")]));`,
  );
  // No leading zero on the hour
  assert.doesNotMatch(out, /klo 0\d/);
  // Weekday + date + hh.mm (minutes stay 2-digit for readability)
  assert.match(out, /^su 11\.10\. klo 2\.30$/u);
});

test("gameTime EN under TZ=America/New_York: 2026-10-10T23:30:00Z → '7:30 PM' with no leading zero and no zone", () => {
  const [out] = runWithTz(
    "America/New_York",
    `import { gameTime } from "./format.js";
     process.stdout.write(JSON.stringify([gameTime("2026-10-10T23:30:00Z", "en")]));`,
  );
  // No leading zero on the hour ('07:30' would fail)
  assert.doesNotMatch(out, /0\d:\d\d/);
  // Date is viewer-local (not the UTC date)
  assert.match(out, /10\/10/);
  // Hour is single-digit '7:30 PM', not '07:30 PM'
  assert.match(out, /\b7:30\s?PM/i);
  // No zone label (EDT/EST/UTC) — removed in Fix B
  assert.doesNotMatch(out, /EDT|EST|UTC[-+]?\d*/);
});

// --- ordinal ---

test("ordinal EN: Intl.PluralRules st/nd/rd/th", () => {
  const cases = [
    [1, "1st"],
    [2, "2nd"],
    [3, "3rd"],
    [4, "4th"],
    [11, "11th"],
    [12, "12th"],
    [13, "13th"],
    [21, "21st"],
    [22, "22nd"],
    [23, "23rd"],
    [30, "30th"],
    [101, "101st"],
    [111, "111th"],
  ];
  for (const [n, expected] of cases) {
    assert.equal(ordinal(n, "en"), expected, `ordinal(${n}, 'en')`);
  }
});

test("ordinal FI: always `${n}.`", () => {
  for (const n of [1, 2, 3, 4, 11, 21, 101, 111]) {
    assert.equal(ordinal(n, "fi"), `${n}.`);
  }
});

// --- season ---

test("season: '20262027' → '2026⁠–⁠27' with WORD JOINERs around the en-dash", () => {
  const out = season("20262027");
  // Characters: '2' '0' '2' '6' U+2060 U+2013 U+2060 '2' '7'
  assert.equal(out.length, 9);
  assert.equal(out.charCodeAt(0), "2".charCodeAt(0));
  assert.equal(out.charCodeAt(4), 0x2060); // WORD JOINER before dash
  assert.equal(out.charCodeAt(5), 0x2013); // EN DASH
  assert.equal(out.charCodeAt(6), 0x2060); // WORD JOINER after dash
  assert.equal(out.charCodeAt(7), "2".charCodeAt(0));
  // Visually: still reads as '2026–27' because U+2060 is zero-width.
  assert.equal(out.replace(/⁠/g, ""), "2026–27");
});

test("season: another season", () => {
  assert.equal(season("20252026").replace(/⁠/g, ""), "2025–26");
});

// --- signed negative-zero pin (PRP-07 gotcha row) ---

test("signed(-0) renders '0' (not '-0', not '+0') in EN and FI", () => {
  // Intl's exceptZero already handles this correctly in both locales. Lock it in so a future
  // rewrite can't regress. (-gap when gap === 0 produces -0 in JS; the view then calls signed.)
  const minusZero = -0;
  assert.equal(signed(minusZero, "en"), "0");
  assert.equal(signed(minusZero, "fi"), "0");
  assert.equal(signed(minusZero, "en").length, 1);
  assert.equal(signed(minusZero, "fi").length, 1);
});
