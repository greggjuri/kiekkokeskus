import { test } from "node:test";
import assert from "node:assert/strict";

import { sortRows, filterSkaters, nextSort } from "./sort.js";
import { SKATER_COLUMNS, GOALIE_COLUMNS, findColumn } from "./columns.js";

const name = (first, last) => ({
  firstName: { default: first },
  lastName: { default: last },
});

// --- nulls last ---

test("nulls sort last in both directions (ADR-015 gotcha)", () => {
  const col = findColumn(SKATER_COLUMNS, "faceoffPct");
  const rows = [
    { playerId: 1, faceoffPct: 0.6, ...name("A", "A") },
    { playerId: 2, faceoffPct: null, ...name("B", "B") },
    { playerId: 3, faceoffPct: 0.4, ...name("C", "C") },
    { playerId: 4, faceoffPct: null, ...name("D", "D") },
  ];
  const desc = sortRows(rows, col, { dir: "desc", lang: "en" });
  assert.deepEqual(desc.map((r) => r.playerId), [1, 3, 2, 4]);
  const asc = sortRows(rows, col, { dir: "asc", lang: "en" });
  assert.deepEqual(asc.map((r) => r.playerId), [3, 1, 2, 4]);
});

// --- stability ---

test("sort is stable on ties (equal keys preserve input order)", () => {
  const col = findColumn(SKATER_COLUMNS, "g");
  const rows = [
    { playerId: 1, g: 2, ...name("A", "A") },
    { playerId: 2, g: 2, ...name("B", "B") },
    { playerId: 3, g: 2, ...name("C", "C") },
    { playerId: 4, g: 5, ...name("D", "D") },
  ];
  const out = sortRows(rows, col, { dir: "desc", lang: "en" });
  assert.deepEqual(out.map((r) => r.playerId), [4, 1, 2, 3]);
});

// --- locale compare for FI ---

test("FI locale: Ö sorts after Z (so Öberg after Zuccarello)", () => {
  const col = findColumn(SKATER_COLUMNS, "name");
  const rows = [
    { playerId: 1, ...name("Mats", "Zuccarello") },
    { playerId: 2, ...name("Rasmus", "Öberg") },
  ];
  const asc = sortRows(rows, col, { dir: "asc", lang: "fi" });
  assert.deepEqual(asc.map((r) => r.playerId), [1, 2]);
});

// --- numeric desc ---

test("sorts numeric columns descending", () => {
  const col = findColumn(SKATER_COLUMNS, "p");
  const rows = [
    { playerId: 1, p: 3, ...name("A", "A") },
    { playerId: 2, p: 9, ...name("B", "B") },
    { playerId: 3, p: 6, ...name("C", "C") },
  ];
  const out = sortRows(rows, col, { dir: "desc", lang: "en" });
  assert.deepEqual(out.map((r) => r.playerId), [2, 3, 1]);
});

// --- position type ---

test("positionCode sorts C,L,R,D,G in that order", () => {
  const col = findColumn(SKATER_COLUMNS, "positionCode");
  const rows = [
    { playerId: 1, positionCode: "D" },
    { playerId: 2, positionCode: "C" },
    { playerId: 3, positionCode: "R" },
    { playerId: 4, positionCode: "L" },
  ];
  const out = sortRows(rows, col, { dir: "asc", lang: "en" });
  assert.deepEqual(out.map((r) => r.positionCode), ["C", "L", "R", "D"]);
});

// --- goalie column ---

test("GAA sorts ascending with nulls last (goalie column)", () => {
  const col = findColumn(GOALIE_COLUMNS, "gaa");
  const rows = [
    { playerId: 1, gaa: 2.5 },
    { playerId: 2, gaa: null },
    { playerId: 3, gaa: 1.9 },
    { playerId: 4, gaa: 2.1 },
  ];
  const asc = sortRows(rows, col, { dir: "asc", lang: "en" });
  assert.deepEqual(asc.map((r) => r.playerId), [3, 4, 1, 2]);
});

// --- filterSkaters ---

test("filterSkaters: all=pass-through, f=C+L+R, d=D", () => {
  const rows = [
    { playerId: 1, positionCode: "C" },
    { playerId: 2, positionCode: "L" },
    { playerId: 3, positionCode: "R" },
    { playerId: 4, positionCode: "D" },
  ];
  assert.equal(filterSkaters(rows, "all").length, 4);
  assert.deepEqual(filterSkaters(rows, "f").map((r) => r.playerId), [1, 2, 3]);
  assert.deepEqual(filterSkaters(rows, "d").map((r) => r.playerId), [4]);
});

// --- nextSort ---

test("nextSort: new column uses its firstDir", () => {
  const g = findColumn(SKATER_COLUMNS, "g");
  const out = nextSort({ sortKey: "p", dir: "desc" }, g);
  assert.deepEqual(out, { sortKey: "g", dir: "desc" });
});

test("nextSort: same column flips dir", () => {
  const p = findColumn(SKATER_COLUMNS, "p");
  const flipped = nextSort({ sortKey: "p", dir: "desc" }, p);
  assert.deepEqual(flipped, { sortKey: "p", dir: "asc" });
  const back = nextSort(flipped, p);
  assert.deepEqual(back, { sortKey: "p", dir: "desc" });
});

test("nextSort: respects asc firstDir (gaa)", () => {
  const gaa = findColumn(GOALIE_COLUMNS, "gaa");
  const out = nextSort({ sortKey: "gp", dir: "desc" }, gaa);
  assert.deepEqual(out, { sortKey: "gaa", dir: "asc" });
});
