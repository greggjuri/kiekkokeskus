import { test } from "node:test";
import assert from "node:assert/strict";

import { headerClickHandler } from "./table.js";
import { SKATER_COLUMNS, GOALIE_COLUMNS, findColumn } from "./columns.js";

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
