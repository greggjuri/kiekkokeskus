import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { boltsView } from "./view.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GOLDEN_PATH = path.resolve(HERE, "../../tests/golden/bolts.json");
const GOLDEN = JSON.parse(fs.readFileSync(GOLDEN_PATH, "utf8"));

// --- golden expected-strings table (init-07 P0 / spec Fixtures and Gotchas) ---

test("golden view EN: record / division / division lead / playoff / last game / PP / PK", () => {
  const v = boltsView(GOLDEN, "en");
  assert.equal(v.tiles.record.label, "Record");
  assert.equal(v.tiles.record.value, "3–1–0");
  assert.equal(v.tiles.record.sub, "6 pts · streak W3");
  assert.equal(v.tiles.division.label, "Atlantic Division");
  assert.equal(v.tiles.division.value, "2nd");
  assert.equal(v.tiles.division.sub, "4th East · 8th NHL");
  assert.equal(v.tiles.divisionLead.value, "0");
  assert.equal(v.tiles.divisionLead.sub, "OTT · 6 pts");
  assert.equal(v.tiles.playoffLine.label, "Above the playoff line");
  assert.equal(v.tiles.playoffLine.value, "+2");
  assert.equal(v.tiles.playoffLine.sub, "NYI · 4 pts");
  assert.equal(v.lastGame.badge, "W");
  assert.equal(v.lastGame.score, "3–2");
  assert.equal(v.lastGame.suffix, "");
  assert.equal(v.lastGame.oppLine, "vs Wild");
  assert.equal(v.lastGame.dateStr, "Oct 8, 2026");
  assert.equal(v.special.pp.pct, "6.3%");
  assert.equal(v.special.pp.rank, "30th in NHL");
  assert.equal(v.special.pk.pct, "77.8%");
  assert.equal(v.special.pk.rank, "19th in NHL");
});

test("golden view FI: same cells, FI formatting", () => {
  const v = boltsView(GOLDEN, "fi");
  // init-08 renamed FI 'Saldo' → 'Tilanne'.
  assert.equal(v.tiles.record.label, "Tilanne");
  assert.equal(v.tiles.record.value, "3–1–0");
  assert.equal(v.tiles.record.sub, "6 p · putki V3");
  assert.equal(v.tiles.division.label, "Atlantin divisioona");
  assert.equal(v.tiles.division.value, "2.");
  assert.equal(v.tiles.division.sub, "Itä 4. · NHL 8.");
  assert.equal(v.tiles.divisionLead.value, "0");
  assert.equal(v.tiles.divisionLead.sub, "OTT · 6 p");
  assert.equal(v.tiles.playoffLine.label, "Pudotuspeliviivan yläpuolella");
  assert.equal(v.tiles.playoffLine.value, "+2");
  assert.equal(v.tiles.playoffLine.sub, "NYI · 4 p");
  assert.equal(v.lastGame.badge, "V");
  assert.equal(v.lastGame.score, "3–2");
  assert.equal(v.lastGame.suffix, "");
  assert.equal(v.lastGame.oppLine, "Wild (koti)");
  assert.equal(v.lastGame.dateStr, "8.10.2026");
  // FI pct uses comma + NBSP
  assert.equal(v.special.pp.pct, "6,3 %");
  assert.equal(v.special.pp.rank, "NHL:n 30.");
  assert.equal(v.special.pk.pct, "77,8 %");
  assert.equal(v.special.pk.rank, "NHL:n 19.");
});

// --- gotcha rows ---

const SYNTH_BASE = {
  schemaVersion: 1,
  generatedAt: "2026-10-11T14:00:00Z",
  dataDate: "2026-10-10",
  season: "20262027",
  team: { abbrev: "TBL", name: { default: "Lightning" } },
  standing: {
    gp: 10,
    w: 5,
    l: 4,
    otl: 1,
    pts: 11,
    streak: { code: "W", count: 2 },
    division: { abbrev: "A", rank: 2 },
    conference: { abbrev: "E", rank: 4 },
    leagueRank: 8,
    divisionLead: { leader: "OTT", leaderPts: 15, gap: 4, gamesInHand: 0 },
    playoffLine: { inPosition: true, team: "NYI", teamPts: 9, gap: 2, gamesInHand: 0 },
  },
  specialTeams: { ppPct: 0.2, ppRank: 10, pkPct: 0.8, pkRank: 5 },
  lastGame: null,
  nextGames: [],
  skaters: [],
  goalies: [],
};

function synth(overrides) {
  // Shallow + nested merge for standing/specialTeams/lastGame etc.
  const d = { ...SYNTH_BASE, ...overrides };
  if (overrides.standing) {
    d.standing = { ...SYNTH_BASE.standing, ...overrides.standing };
    if (overrides.standing.divisionLead)
      d.standing.divisionLead = { ...SYNTH_BASE.standing.divisionLead, ...overrides.standing.divisionLead };
    if (overrides.standing.playoffLine)
      d.standing.playoffLine = { ...SYNTH_BASE.standing.playoffLine, ...overrides.standing.playoffLine };
    if (overrides.standing.streak !== undefined) d.standing.streak = overrides.standing.streak;
  }
  if (overrides.specialTeams !== undefined) d.specialTeams = overrides.specialTeams;
  return d;
}

test("signed gaps from Tampa's view (ADR-036)", () => {
  const data = synth({ standing: {
    divisionLead: { leader: "OTT", leaderPts: 15, gap: 4, gamesInHand: 0 },
    playoffLine: { inPosition: false, team: "NYI", teamPts: 11, gap: 2, gamesInHand: 0 },
  }});
  const v = boltsView(data, "en");
  assert.equal(v.tiles.divisionLead.value, "−4"); // U+2212
  assert.equal(v.tiles.playoffLine.label, "Below the playoff line");
  assert.equal(v.tiles.playoffLine.value, "−2");
});

test("TBL leads division: value '0', label 'Division leader'", () => {
  const data = synth({ standing: {
    divisionLead: { leader: "TBL", leaderPts: 11, gap: 0, gamesInHand: 0 },
  }});
  const en = boltsView(data, "en");
  assert.equal(en.tiles.divisionLead.value, "0");
  assert.equal(en.tiles.divisionLead.label, "Division leader");
  const fi = boltsView(data, "fi");
  assert.equal(fi.tiles.divisionLead.label, "Divisioonan kärjessä");
});

test("games in hand: positive adds 'in hand', negative adds 'more games played', zero omits", () => {
  const dPos = synth({ standing: { divisionLead: { leader: "OTT", leaderPts: 15, gap: 4, gamesInHand: 1 } }});
  assert.equal(boltsView(dPos, "en").tiles.divisionLead.sub, "OTT · 15 pts · 1 game in hand");
  const dNeg = synth({ standing: { divisionLead: { leader: "OTT", leaderPts: 15, gap: 4, gamesInHand: -2 } }});
  assert.equal(boltsView(dNeg, "en").tiles.divisionLead.sub, "OTT · 15 pts · 2 more games played");
  const dZero = synth({ standing: { divisionLead: { leader: "OTT", leaderPts: 15, gap: 4, gamesInHand: 0 } }});
  assert.equal(boltsView(dZero, "en").tiles.divisionLead.sub, "OTT · 15 pts");
});

test("0 GP state: no streak text, lastGame null, nextGames empty, special values null", () => {
  const data = synth({
    standing: { gp: 0, w: 0, l: 0, otl: 0, pts: 0, streak: null },
    lastGame: null,
    nextGames: [],
    specialTeams: { ppPct: null, ppRank: null, pkPct: null, pkRank: null },
  });
  const v = boltsView(data, "en");
  assert.equal(v.tiles.record.value, "0–0–0");
  assert.equal(v.tiles.record.sub, "0 pts"); // no streak suffix
  assert.equal(v.lastGame, null);
  assert.equal(v.nextGames.length, 0);
  assert.equal(v.special.pp.pct, "–");
  assert.equal(v.special.pp.rank, null);
});

test("OT / SO suffix on last game", () => {
  const base = {
    date: "2026-10-10", home: true, opponent: { abbrev: "MIN", name: { default: "Wild" } },
    tblScore: 3, oppScore: 2, result: "W",
  };
  const otData = synth({ lastGame: { ...base, decidedIn: "OT" } });
  assert.equal(boltsView(otData, "en").lastGame.suffix, "OT");
  assert.equal(boltsView(otData, "fi").lastGame.suffix, "JA");
  const soData = synth({ lastGame: { ...base, decidedIn: "SO" } });
  assert.equal(boltsView(soData, "en").lastGame.suffix, "SO");
  assert.equal(boltsView(soData, "fi").lastGame.suffix, "VL");
  const regData = synth({ lastGame: { ...base, decidedIn: "REG" } });
  assert.equal(boltsView(regData, "en").lastGame.suffix, "");
});

test("result badges W/L/OTL in EN and FI", () => {
  const mk = (r) => ({ date:"2026-10-10", home:true, opponent:{abbrev:"MIN", name:{default:"Wild"}},
    tblScore:3, oppScore:2, result:r, decidedIn:"REG" });
  for (const [r, en, fi] of [["W", "W", "V"], ["L", "L", "H"], ["OTL", "OTL", "JH"]]) {
    assert.equal(boltsView(synth({lastGame: mk(r)}), "en").lastGame.badge, en);
    assert.equal(boltsView(synth({lastGame: mk(r)}), "fi").lastGame.badge, fi);
  }
});

test("opp.home vs opp.away with localName (not renderName)", () => {
  const mk = (home) => ({ date:"2026-10-10", home, opponent:{abbrev:"MIN", name:{default:"Wild"}},
    tblScore:3, oppScore:2, result:"W", decidedIn:"REG" });
  assert.equal(boltsView(synth({lastGame: mk(true)}), "en").lastGame.oppLine, "vs Wild");
  assert.equal(boltsView(synth({lastGame: mk(false)}), "en").lastGame.oppLine, "at Wild");
  assert.equal(boltsView(synth({lastGame: mk(true)}), "fi").lastGame.oppLine, "Wild (koti)");
  assert.equal(boltsView(synth({lastGame: mk(false)}), "fi").lastGame.oppLine, "Wild (vieras)");
});

// --- backstop: no literal {placeholder} in any rendered view string ---

function flatten(obj) {
  const out = [];
  function walk(v) {
    if (v == null) return;
    if (typeof v === "string") out.push(v);
    else if (Array.isArray(v)) v.forEach(walk);
    else if (typeof v === "object") Object.values(v).forEach(walk);
  }
  walk(obj);
  return out;
}

test("no `{` or `}` placeholder leaks in any rendered view string (both langs)", () => {
  for (const lang of ["en", "fi"]) {
    const strings = flatten(boltsView(GOLDEN, lang));
    for (const s of strings) {
      assert.ok(!s.includes("{"), `${lang}: '${s}' leaks a placeholder`);
      assert.ok(!s.includes("}"), `${lang}: '${s}' leaks a placeholder`);
    }
  }
});
