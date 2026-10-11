import { test } from "node:test";
import assert from "node:assert/strict";

import {
  SKATER_COLUMNS,
  GOALIE_COLUMNS,
  findColumn,
  POSITION_ORDER,
} from "./columns.js";

test("every skater column has all four labels (parity)", () => {
  for (const col of SKATER_COLUMNS) {
    for (const field of ["en", "enTitle", "fi", "fiTitle"]) {
      assert.ok(
        typeof col[field] === "string" && col[field].length > 0,
        `skater column ${col.key} missing ${field}`,
      );
    }
  }
});

test("every goalie column has all four labels (parity)", () => {
  for (const col of GOALIE_COLUMNS) {
    for (const field of ["en", "enTitle", "fi", "fiTitle"]) {
      assert.ok(
        typeof col[field] === "string" && col[field].length > 0,
        `goalie column ${col.key} missing ${field}`,
      );
    }
  }
});

test("every column has a known format and valid firstDir", () => {
  const formats = new Set([
    "name",
    "text",
    "int",
    "signed",
    "toi",
    "pct1",
    "rate3",
    "dec2",
    "position",
  ]);
  for (const col of [...SKATER_COLUMNS, ...GOALIE_COLUMNS]) {
    assert.ok(formats.has(col.format), `${col.key} unknown format ${col.format}`);
    assert.ok(["asc", "desc"].includes(col.firstDir), `${col.key} bad firstDir`);
  }
});

test("only `gaa` has firstDir asc among numeric columns", () => {
  for (const col of SKATER_COLUMNS) {
    if (["int", "signed", "toi", "pct1", "rate3", "dec2"].includes(col.format)) {
      assert.equal(col.firstDir, "desc", `skater ${col.key} should sort desc first`);
    }
  }
  const gaa = findColumn(GOALIE_COLUMNS, "gaa");
  assert.equal(gaa.firstDir, "asc");
});

// Pin ADR-038 FI abbreviations so a rename shows up as a visible test diff rather than silent
// drift. If liiga.fi ever updates its glossary, update ADR-038 and these pins together.
test("FI skater abbreviations match ADR-038", () => {
  const expected = {
    name: "Pelaaja",
    team: "Joukkue",
    positionCode: "PP",
    gp: "O",
    g: "M",
    a: "S",
    p: "P",
    pm: "+/−",
    pim: "R",
    toiPerGame: "Aika/O",
    sog: "L",
    shootingPct: "L%",
    ppg: "YV",
    ppp: "YVP",
    shg: "AV",
    gwg: "VM",
    faceoffPct: "A%",
    hits: "TAK",
    blocks: "BL",
  };
  for (const [key, abbr] of Object.entries(expected)) {
    const col = findColumn(SKATER_COLUMNS, key);
    assert.ok(col, `missing skater column ${key}`);
    assert.equal(col.fi, abbr, `skater ${key} FI abbr changed`);
  }
});

test("FI goalie abbreviations match ADR-038", () => {
  const expected = {
    name: "Maalivahti",
    team: "Joukkue",
    gp: "PO",
    gs: "AK",
    w: "V",
    l: "H",
    otl: "JH",
    svPct: "T%",
    gaa: "KA",
    so: "NP",
    toi: "Aika",
  };
  for (const [key, abbr] of Object.entries(expected)) {
    const col = findColumn(GOALIE_COLUMNS, key);
    assert.ok(col, `missing goalie column ${key}`);
    assert.equal(col.fi, abbr, `goalie ${key} FI abbr changed`);
  }
});

test("POSITION_ORDER is C L R D G", () => {
  assert.deepEqual(POSITION_ORDER, ["C", "L", "R", "D", "G"]);
});
