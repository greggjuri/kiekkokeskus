import { test } from "node:test";
import assert from "node:assert/strict";

import { readState, writeState } from "./url.js";
import { SKATER_COLUMNS, GOALIE_COLUMNS } from "./columns.js";

// /leijonat has `team` in skater columns; /bolts doesn't.
const BOLTS_SKATER_COLUMNS = SKATER_COLUMNS.filter((c) => c.key !== "team");
const LEIJONAT_SKATER_COLUMNS = SKATER_COLUMNS;

function fakeHistory() {
  const calls = [];
  return {
    calls,
    replaceState: (_data, _title, url) => calls.push(url),
  };
}

// --- defaults ---

test("readState: empty search returns all defaults, langExplicit=false", () => {
  const s = readState({
    search: "",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.deepEqual(s, {
    lang: "en",
    langExplicit: false,
    pos: "all",
    sort: "p",
    dir: "desc",
    gsort: "gp",
    gdir: "desc",
  });
});

test("readState: resolvedLang=fi (from storage/nav) still has langExplicit=false", () => {
  const s = readState({
    search: "",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "fi",
  });
  assert.equal(s.lang, "fi");
  assert.equal(s.langExplicit, false);
});

// --- URL ?lang= ---

test("readState: ?lang=fi sets lang and langExplicit=true", () => {
  const s = readState({
    search: "?lang=fi",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.equal(s.lang, "fi");
  assert.equal(s.langExplicit, true);
});

test("readState: unknown ?lang=xx falls through to resolvedLang (not explicit)", () => {
  const s = readState({
    search: "?lang=xx",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "fi",
  });
  assert.equal(s.lang, "fi");
  assert.equal(s.langExplicit, false);
});

// --- page-scoped column validation ---

test("readState: ?sort=team on /bolts (no team column) falls back to default 'p'", () => {
  const s = readState({
    search: "?sort=team",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.equal(s.sort, "p");
});

test("readState: ?sort=team on /leijonat (has team) returns 'team'", () => {
  const s = readState({
    search: "?sort=team",
    columns: LEIJONAT_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.equal(s.sort, "team");
});

test("readState: unknown ?sort=moonshot falls back to 'p'", () => {
  const s = readState({
    search: "?sort=moonshot",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.equal(s.sort, "p");
});

test("readState: invalid ?pos=x and ?dir=sideways drop to defaults", () => {
  const s = readState({
    search: "?pos=x&dir=sideways",
    columns: BOLTS_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.equal(s.pos, "all");
  assert.equal(s.dir, "desc");
});

// --- writeState: no implicit ?lang= on default load ---

test("writeState: all-defaults + langExplicit=false → clean URL (no query)", () => {
  const history = fakeHistory();
  const state = {
    lang: "en",
    pos: "all",
    sort: "p",
    dir: "desc",
    gsort: "gp",
    gdir: "desc",
  };
  const url = writeState(state, {
    history,
    pathname: "/bolts",
    langExplicit: false,
  });
  assert.equal(url, "/bolts");
  assert.deepEqual(history.calls, ["/bolts"]);
});

test("writeState: FI resolved by nav but not explicit → no ?lang=fi written", () => {
  const history = fakeHistory();
  const state = {
    lang: "fi",
    pos: "all",
    sort: "p",
    dir: "desc",
    gsort: "gp",
    gdir: "desc",
  };
  const url = writeState(state, {
    history,
    pathname: "/leijonat",
    langExplicit: false,
  });
  assert.equal(url, "/leijonat");
});

// --- writeState: toggled lang is explicit ---

test("writeState: toggling EN at a default-FI page writes ?lang=en", () => {
  const history = fakeHistory();
  const state = {
    lang: "en",
    pos: "all",
    sort: "p",
    dir: "desc",
    gsort: "gp",
    gdir: "desc",
  };
  const url = writeState(state, {
    history,
    pathname: "/leijonat",
    langExplicit: true,
  });
  assert.equal(url, "/leijonat?lang=en");
});

// --- explicit round-trip ---

test("writeState round-trip: ?pos=d&sort=toiPerGame&dir=desc&lang=fi", () => {
  // Note: dir=desc is actually the default so it would be dropped. Use dir=asc for a real
  // round-trip test, since that's non-default.
  const history = fakeHistory();
  const state = {
    lang: "fi",
    pos: "d",
    sort: "toiPerGame",
    dir: "asc",
    gsort: "gp",
    gdir: "desc",
  };
  const url = writeState(state, {
    history,
    pathname: "/leijonat",
    langExplicit: true,
  });
  const params = new URLSearchParams(url.split("?")[1]);
  assert.equal(params.get("pos"), "d");
  assert.equal(params.get("sort"), "toiPerGame");
  assert.equal(params.get("dir"), "asc");
  assert.equal(params.get("lang"), "fi");
  // defaults dropped
  assert.equal(params.get("gsort"), null);
  assert.equal(params.get("gdir"), null);

  const back = readState({
    search: `?${params.toString()}`,
    columns: LEIJONAT_SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    resolvedLang: "en",
  });
  assert.equal(back.lang, "fi");
  assert.equal(back.langExplicit, true);
  assert.equal(back.pos, "d");
  assert.equal(back.sort, "toiPerGame");
  assert.equal(back.dir, "asc");
  assert.equal(back.gsort, "gp");
  assert.equal(back.gdir, "desc");
});
