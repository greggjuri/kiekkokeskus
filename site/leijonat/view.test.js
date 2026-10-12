import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { leijonatView } from "./view.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GOLDEN_PATH = path.resolve(HERE, "../../tests/golden/leijonat.json");
const GOLDEN = JSON.parse(fs.readFileSync(GOLDEN_PATH, "utf8"));

// --- count tiles ---

test("golden count tiles: 30 / 5 / 19 / 4", () => {
  for (const lang of ["en", "fi"]) {
    const v = leijonatView(GOLDEN, lang);
    assert.equal(v.tiles.skaters.value, "30");
    assert.equal(v.tiles.goalies.value, "5");
    assert.equal(v.tiles.teams.value, "19");
    assert.equal(v.tiles.rookies.value, "4");
  }
});

test("golden count tile labels EN", () => {
  const v = leijonatView(GOLDEN, "en");
  assert.equal(v.tiles.skaters.label, "Skaters");
  assert.equal(v.tiles.goalies.label, "Goalies");
  assert.equal(v.tiles.teams.label, "Teams");
  assert.equal(v.tiles.rookies.label, "Rookies");
});

test("golden count tile labels FI", () => {
  const v = leijonatView(GOLDEN, "fi");
  assert.equal(v.tiles.skaters.label, "Kenttäpelaajat");
  assert.equal(v.tiles.goalies.label, "Maalivahdit");
  assert.equal(v.tiles.teams.label, "Joukkueet");
  assert.equal(v.tiles.rookies.label, "Tulokkaat");
});

// --- lastNight heading ---

test("lastNight heading EN: 'Last night' + 'Oct 9, 2026 · 4 games'", () => {
  const v = leijonatView(GOLDEN, "en");
  assert.equal(v.lastNight.heading, "Last night");
  assert.equal(v.lastNight.subLine, "Oct 9, 2026 · 4 games");
  assert.equal(v.lastNight.empty, false);
});

test("lastNight heading FI: 'Viime yönä' + '9.10.2026 · 4 ottelua'", () => {
  const v = leijonatView(GOLDEN, "fi");
  assert.equal(v.lastNight.heading, "Viime yönä");
  assert.equal(v.lastNight.subLine, "9.10.2026 · 4 ottelua");
});

// --- lastNight cards ---

test("Granlund card EN", () => {
  const v = leijonatView(GOLDEN, "en");
  const g = v.lastNight.cards.find((c) => c.name === "Mikael Granlund");
  assert.ok(g, "Granlund card missing");
  assert.equal(g.team, "ANA");
  assert.equal(g.rookie, false);
  assert.equal(g.big, "1 G · 1 A");
  assert.equal(g.badge, "W");
  assert.equal(g.score, "5–1"); // U+2013
  assert.equal(g.suffix, "");
  assert.equal(g.oppLine, "at WPG");
});

test("Granlund card FI", () => {
  const v = leijonatView(GOLDEN, "fi");
  const g = v.lastNight.cards.find((c) => c.name === "Mikael Granlund");
  assert.equal(g.big, "1 M · 1 S");
  assert.equal(g.badge, "V");
  assert.equal(g.score, "5–1");
  assert.equal(g.oppLine, "WPG (vieras)");
});

test("Kakko card EN", () => {
  const v = leijonatView(GOLDEN, "en");
  const k = v.lastNight.cards.find((c) => c.name === "Kaapo Kakko");
  assert.ok(k, "Kakko card missing");
  assert.equal(k.team, "SEA");
  assert.equal(k.big, "0 G · 1 A");
  assert.equal(k.badge, "W");
  assert.equal(k.score, "6–3");
  assert.equal(k.oppLine, "at DET");
});

test("Kakko card FI", () => {
  const v = leijonatView(GOLDEN, "fi");
  const k = v.lastNight.cards.find((c) => c.name === "Kaapo Kakko");
  assert.equal(k.big, "0 M · 1 S");
  assert.equal(k.badge, "V");
  assert.equal(k.oppLine, "DET (vieras)");
});

// --- byTeam ---

test("byTeam EN first four rows + sort order", () => {
  const v = leijonatView(GOLDEN, "en");
  const first4 = v.byTeam.slice(0, 4);
  assert.equal(first4[0].name, "Dallas Stars");
  assert.equal(first4[0].total, 6);
  assert.equal(first4[0].finnNames, "Heiskanen, Hintz, Hyry, Kiviranta, Lindell, Rantanen");
  assert.equal(first4[1].name, "Florida Panthers");
  assert.equal(first4[1].total, 4);
  // Alphabetical: Lundell (lund) < Luostarinen (luos). The init-08 spec had these two in
  // the wrong order — the view sort is correct and this test is the authoritative check.
  assert.equal(first4[1].finnNames, "Barkov, Lundell, Luostarinen, Mikkola");
  // LAK and VAN tie at 3 → name asc tiebreaker; LAK before VAN
  assert.equal(first4[2].name, "Los Angeles Kings");
  assert.equal(first4[2].total, 3);
  assert.equal(first4[3].name, "Vancouver Canucks");
  assert.equal(first4[3].total, 3);
  assert.equal(first4[3].finnNames, "Lankinen, Meriläinen, Räty");
});

test("byTeam FI uses 'pelaajaa' plural; team names from localName (no fi key → default)", () => {
  const v = leijonatView(GOLDEN, "fi");
  const dal = v.byTeam[0];
  assert.equal(dal.name, "Dallas Stars"); // teams carry no fi key today
  assert.equal(dal.playersLabel, "6 pelaajaa");
});

test("byTeam players label singular vs plural (EN)", () => {
  // Make a synthetic row where a team has exactly 1 player
  const data = {
    ...GOLDEN,
    teams: [{ abbrev: "ZZZ", name: { default: "Zed" }, skaters: 1, goalies: 0 }],
    skaters: [{ team: "ZZZ", firstName: { default: "A" }, lastName: { default: "B" }, rookie: false }],
    goalies: [],
  };
  const v = leijonatView(data, "en");
  assert.equal(v.byTeam[0].playersLabel, "1 player");
});

// --- rookie counts + legend flags ---

test("rookie counts: 4 total, all skaters, no goalie rookies today", () => {
  const v = leijonatView(GOLDEN, "en");
  assert.equal(v.tiles.rookies.value, "4");
  assert.equal(v.skaterRookieLegend, true);
  assert.equal(v.goalieRookieLegend, false);
});

// --- gotcha rows ---

test("gotcha — lastNight: no games", () => {
  const data = { ...GOLDEN, lastNight: { date: "2026-10-10", gamesCompleted: 0, skaters: [], goalies: [] } };
  const v = leijonatView(data, "en");
  assert.equal(v.lastNight.empty, true);
  assert.equal(v.lastNight.message, "noGames");
});

test("gotcha — lastNight: games but no Finns", () => {
  const data = { ...GOLDEN, lastNight: { date: "2026-10-10", gamesCompleted: 5, skaters: [], goalies: [] } };
  const v = leijonatView(data, "en");
  assert.equal(v.lastNight.empty, true);
  assert.equal(v.lastNight.message, "noFinns");
});

test("gotcha — lastNight object missing entirely", () => {
  const data = { ...GOLDEN, lastNight: undefined };
  const v = leijonatView(data, "en");
  assert.equal(v.lastNight.empty, true);
  assert.equal(v.lastNight.message, "noGames");
});

test("gotcha — goalie with no shots: saves/sa/svPct all null", () => {
  const synthGoalie = {
    firstName: { default: "Noshot" },
    lastName: { default: "Mahvi" },
    team: "XXX",
    saves: null,
    shotsAgainst: null,
    svPct: null,
    rookie: false,
    game: {
      home: true,
      opponent: "YYY",
      teamScore: 0,
      oppScore: 2,
      result: "L",
      decidedIn: "REG",
    },
  };
  const data = { ...GOLDEN, lastNight: { date: "2026-10-10", gamesCompleted: 1, skaters: [], goalies: [synthGoalie] } };
  for (const [lang, expected] of [["en", "–/– saves · –"], ["fi", "–/– torjuntaa · –"]]) {
    const v = leijonatView(data, lang);
    const card = v.lastNight.cards[0];
    assert.equal(card.big, expected);
  }
});

test("gotcha — goalie badge comes from game.result, NEVER from decision", () => {
  const synthGoalie = {
    firstName: { default: "D" },
    lastName: { default: "Ciders" },
    team: "AAA",
    saves: 30,
    shotsAgainst: 32,
    svPct: 0.9375,
    rookie: false,
    decision: "W",         // view must ignore this
    game: {
      home: false,
      opponent: "BBB",
      teamScore: 2,
      oppScore: 3,
      result: "L",         // badge should be L (EN) / H (FI)
      decidedIn: "REG",
    },
  };
  const data = { ...GOLDEN, lastNight: { date: "2026-10-10", gamesCompleted: 1, skaters: [], goalies: [synthGoalie] } };
  assert.equal(leijonatView(data, "en").lastNight.cards[0].badge, "L");
  assert.equal(leijonatView(data, "fi").lastNight.cards[0].badge, "H");
});

test("gotcha — OT loss card: result OTL + decidedIn OT", () => {
  const row = {
    firstName: { default: "Pat" },
    lastName: { default: "Loser" },
    team: "CCC",
    g: 0, a: 0,
    rookie: false,
    game: {
      home: true,
      opponent: "DDD",
      teamScore: 2,
      oppScore: 3,
      result: "OTL",
      decidedIn: "OT",
    },
  };
  const data = { ...GOLDEN, lastNight: { date: "2026-10-10", gamesCompleted: 1, skaters: [row], goalies: [] } };
  const en = leijonatView(data, "en").lastNight.cards[0];
  assert.equal(en.badge, "OTL");
  assert.equal(en.suffix, "OT");
  const fi = leijonatView(data, "fi").lastNight.cards[0];
  assert.equal(fi.badge, "JH");
  assert.equal(fi.suffix, "JA");
});

test("gotcha — SO suffix also works", () => {
  const row = {
    firstName: { default: "SO" },
    lastName: { default: "Winner" },
    team: "EEE",
    g: 0, a: 0, rookie: false,
    game: { home: true, opponent: "FFF", teamScore: 3, oppScore: 2, result: "W", decidedIn: "SO" },
  };
  const data = { ...GOLDEN, lastNight: { date: "2026-10-10", gamesCompleted: 1, skaters: [row], goalies: [] } };
  assert.equal(leijonatView(data, "en").lastNight.cards[0].suffix, "SO");
  assert.equal(leijonatView(data, "fi").lastNight.cards[0].suffix, "VL");
});

// --- no placeholder backstop ---

function flatten(obj) {
  const out = [];
  (function walk(v) {
    if (v == null) return;
    if (typeof v === "string") out.push(v);
    else if (Array.isArray(v)) v.forEach(walk);
    else if (typeof v === "object") Object.values(v).forEach(walk);
  })(obj);
  return out;
}

test("no `{` or `}` placeholder leaks in any rendered view string (both langs)", () => {
  for (const lang of ["en", "fi"]) {
    for (const s of flatten(leijonatView(GOLDEN, lang))) {
      assert.ok(!s.includes("{"), `${lang}: '${s}' leaks a placeholder`);
      assert.ok(!s.includes("}"), `${lang}: '${s}' leaks a placeholder`);
    }
  }
});

test("leijonatView has NO 'definition' field (removed from init-08)", () => {
  for (const lang of ["en", "fi"]) {
    const v = leijonatView(GOLDEN, lang);
    assert.ok(!("definition" in v), `${lang}: view.definition should not exist`);
  }
});
