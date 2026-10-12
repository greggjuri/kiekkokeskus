import { test } from "node:test";
import assert from "node:assert/strict";

import { headerClickHandler, nameCellParts } from "./table.js";
import { SKATER_COLUMNS, GOALIE_COLUMNS, findColumn } from "./columns.js";
import { sortRows } from "./sort.js";

// `headerClickHandler` is the pure part of the header-click path. It reads the current
// { state, onSortChange } from a store that the DOM-side code updates on every render, so
// the second click on the same column always flips the latest direction (regression:
// previously the listener closed over the first-render state and flipped the same value
// forever).

function makeStore(initialState, onSortChange) {
  return { state: initialState, onSortChange };
}

function recorder() {
  const calls = [];
  function fn(x) {
    calls.push(x);
  }
  fn.calls = calls;
  return fn;
}

test("two clicks on the same column flip desc → asc then asc → desc", () => {
  const g = findColumn(SKATER_COLUMNS, "g");
  const sink = recorder();
  const store = makeStore({ sortKey: "p", dir: "desc" }, sink);

  // First click on G from the default (sort=p, dir=desc) → G desc (G.firstDir)
  headerClickHandler(() => store, g);
  assert.deepEqual(sink.calls[0], { sortKey: "g", dir: "desc" });

  // Caller applies the dispatch (just like controller does) and re-renders the table,
  // which bumps store.state to the new value.
  store.state = { sortKey: "g", dir: "desc" };

  // Second click on G → flip to asc
  headerClickHandler(() => store, g);
  assert.deepEqual(sink.calls[1], { sortKey: "g", dir: "asc" });

  store.state = { sortKey: "g", dir: "asc" };

  // Third click on G → flip back to desc
  headerClickHandler(() => store, g);
  assert.deepEqual(sink.calls[2], { sortKey: "g", dir: "desc" });
});

test("click on a new column uses that column's firstDir", () => {
  const p = findColumn(SKATER_COLUMNS, "p");
  const sink = recorder();
  const store = makeStore({ sortKey: "g", dir: "asc" }, sink);
  headerClickHandler(() => store, p);
  // p.firstDir is 'desc'
  assert.deepEqual(sink.calls[0], { sortKey: "p", dir: "desc" });
});

test("goalie gaa has firstDir 'asc' (ADR-038 — lower is better)", () => {
  const gaa = findColumn(GOALIE_COLUMNS, "gaa");
  const sink = recorder();
  const store = makeStore({ sortKey: "gp", dir: "desc" }, sink);
  headerClickHandler(() => store, gaa);
  assert.deepEqual(sink.calls[0], { sortKey: "gaa", dir: "asc" });
});

test("listener reads live state, not whatever was in the store at attach time", () => {
  // Simulates the regression: the closure held an initial `state`, then the store was later
  // updated. The fix passes a getter so the lookup happens at click time.
  const g = findColumn(SKATER_COLUMNS, "g");
  const sink = recorder();
  const store = makeStore({ sortKey: "p", dir: "desc" }, sink);
  const click = () => headerClickHandler(() => store, g);

  click();
  assert.deepEqual(sink.calls[0], { sortKey: "g", dir: "desc" });

  // Simulate the controller applying the dispatch: store.state updated BEFORE the next click.
  store.state = { sortKey: "g", dir: "desc" };
  click();
  assert.deepEqual(sink.calls[1], { sortKey: "g", dir: "asc" });

  store.state = { sortKey: "g", dir: "asc" };
  click();
  assert.deepEqual(sink.calls[2], { sortKey: "g", dir: "desc" });
});

test("missing store or onSortChange is a no-op (doesn't throw)", () => {
  const g = findColumn(SKATER_COLUMNS, "g");
  headerClickHandler(() => null, g); // getter returned null
  headerClickHandler(() => ({}), g); // store with no onSortChange
  headerClickHandler(() => ({ state: { sortKey: "p", dir: "desc" } }), g); // no cb
  // Reaching here means no throw.
  assert.ok(true);
});

// --- nameCellParts (init-08) ---
//
// Pure helper: the DOM renderer consults it to decide what goes in the name cell. When
// suffix is null the renderer MUST leave the cell as a bare text node, which keeps /bolts
// markup byte-identical to the pre-init-08 state. These tests cover the decision logic
// without touching the DOM.

const row = (first, last, extras = {}) => ({
  firstName: { default: first },
  lastName: { default: last, ...(extras.lastFi ? { fi: extras.lastFi } : {}) },
  rookie: extras.rookie ?? false,
});

test("nameCellParts: no decorateName → both suffix and title are null (/bolts path)", () => {
  const parts = nameCellParts(row("Olli", "Maatta"), "en", null);
  assert.deepEqual(parts, { name: "Olli Maatta", suffix: null, title: null });
});

test("nameCellParts: decorateName returning null → both null", () => {
  const parts = nameCellParts(row("Olli", "Maatta"), "en", () => null);
  assert.deepEqual(parts, { name: "Olli Maatta", suffix: null, title: null });
});

test("nameCellParts: rookie row → suffix + title", () => {
  const deco = (r, l) => r.rookie
    ? { suffix: " *", title: l === "fi" ? "Tulokas" : "Rookie" } : null;
  const parts = nameCellParts(row("Kieran", "Lambert", { rookie: true }), "en", deco);
  assert.deepEqual(parts, { name: "Kieran Lambert", suffix: " *", title: "Rookie" });
});

test("nameCellParts: non-rookie row with same decorateName → both null", () => {
  const deco = (r) => r.rookie ? { suffix: " *", title: "Rookie" } : null;
  const parts = nameCellParts(row("Sebastian", "Aho"), "en", deco);
  assert.deepEqual(parts, { name: "Sebastian Aho", suffix: null, title: null });
});

test("nameCellParts: FI lang threads through to decorateName", () => {
  const deco = (r, l) => r.rookie
    ? { suffix: " *", title: l === "fi" ? "Tulokas" : "Rookie" } : null;
  const parts = nameCellParts(row("Kieran", "Lambert", { rookie: true }), "fi", deco);
  assert.equal(parts.title, "Tulokas");
});

test("nameCellParts: FI name rendered via renderName (fi ?? default)", () => {
  const r = row("Olli", "Maatta", { lastFi: "Määttä" });
  assert.equal(nameCellParts(r, "en", null).name, "Olli Maatta");
  assert.equal(nameCellParts(r, "fi", null).name, "Olli Määttä");
});

test("nameCellParts: decorateName with suffix but no title keeps title null", () => {
  const parts = nameCellParts(row("A", "B"), "en", () => ({ suffix: " †" }));
  assert.deepEqual(parts, { name: "A B", suffix: " †", title: null });
});

test("name sort ignores the rookie marker (sort uses the raw name)", () => {
  // Helenius (rookie) should sort BEFORE Heiskanen (non-rookie)? No: alphabetical sort by
  // last name puts Heiskanen before Helenius (hei < hel). The '*' marker is DOM-only and
  // never affects comparison.
  const rows = [
    row("Kari", "Helenius", { rookie: true }),
    row("Miro", "Heiskanen"),
  ];
  const nameCol = findColumn(SKATER_COLUMNS, "name");
  const asc = sortRows(rows, nameCol, { dir: "asc", lang: "en" });
  assert.equal(asc[0].lastName.default, "Heiskanen");
  assert.equal(asc[1].lastName.default, "Helenius");
});
