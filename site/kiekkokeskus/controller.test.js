import { test } from "node:test";
import assert from "node:assert/strict";

import { pageReducer, createController } from "./controller.js";
import { SKATER_COLUMNS, GOALIE_COLUMNS } from "./columns.js";

// --- pageReducer ---

test("pageReducer: setLang sets langExplicit true", () => {
  const next = pageReducer({ lang: "en", langExplicit: false }, { type: "setLang", lang: "fi" });
  assert.equal(next.lang, "fi");
  assert.equal(next.langExplicit, true);
});

test("pageReducer: setPos leaves langExplicit untouched", () => {
  const next = pageReducer({ lang: "en", langExplicit: false, pos: "all" }, { type: "setPos", pos: "d" });
  assert.equal(next.pos, "d");
  assert.equal(next.langExplicit, false);
});

test("pageReducer: setSort/setGsort leave langExplicit untouched", () => {
  const a = pageReducer({ lang: "en", langExplicit: false }, { type: "setSort", sortKey: "g", dir: "desc" });
  assert.equal(a.sort, "g");
  assert.equal(a.dir, "desc");
  assert.equal(a.langExplicit, false);
  const b = pageReducer({ lang: "en", langExplicit: false }, { type: "setGsort", sortKey: "gaa", dir: "asc" });
  assert.equal(b.gsort, "gaa");
  assert.equal(b.gdir, "asc");
  assert.equal(b.langExplicit, false);
});

// --- helpers for createController tests ---

function makeLocation(pathname = "/bolts", search = "") {
  return {
    pathname,
    search,
    href: `http://127.0.0.1${pathname}${search}`,
  };
}

function makeHistory() {
  const calls = [];
  return {
    calls,
    replaceState: (_state, _title, url) => calls.push(url),
  };
}

function makeStorage(opts = {}) {
  const map = new Map();
  const setErr = opts.throwOnSet ?? null;
  return {
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => {
      if (setErr) throw setErr;
      map.set(k, v);
    },
    _map: map,
  };
}

function makeFetchFn(response) {
  // response: either a plain object (treated as body) or a thrown-value factory
  let count = 0;
  const fn = async () => {
    count += 1;
    return {
      ok: response.ok ?? true,
      status: response.status ?? 200,
      json: async () => response.body,
    };
  };
  fn.getCallCount = () => count;
  return fn;
}

function makeRecorder() {
  const calls = [];
  function render(state, data, meta) {
    calls.push({ state, data, meta });
  }
  render.calls = calls;
  return render;
}

// --- createController ---

test("createController: fetch once across many dispatches (fetch-once contract)", async () => {
  const render = makeRecorder();
  const fetchFn = makeFetchFn({ body: { schemaVersion: 1, foo: "bar" } });
  const ctrl = createController({
    dataPath: "/data/kiekkokeskus/bolts.json",
    expectedSchemaVersion: 1,
    columns: SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    fetchFn,
    history: makeHistory(),
    storage: makeStorage(),
    location: makeLocation(),
    nav: { language: "en-US" },
    render,
  });

  await ctrl.start();
  ctrl.dispatch({ type: "setLang", lang: "fi" });
  ctrl.dispatch({ type: "setPos", pos: "d" });
  ctrl.dispatch({ type: "setSort", sortKey: "g", dir: "desc" });
  ctrl.dispatch({ type: "setGsort", sortKey: "gaa", dir: "asc" });

  assert.equal(fetchFn.getCallCount(), 1, "fetchFn must be called exactly once");
  assert.equal(render.calls.length, 5, "render called once per state transition (1 start + 4 dispatches)");
  // Every render receives the same cached data object identity
  const firstData = render.calls[0].data;
  for (const c of render.calls) assert.equal(c.data, firstData);
  assert.equal(firstData.foo, "bar");
});

test("createController: langExplicit survives subsequent dispatches (URL keeps ?lang=)", async () => {
  const render = makeRecorder();
  const history = makeHistory();
  const fetchFn = makeFetchFn({ body: { schemaVersion: 1 } });
  const ctrl = createController({
    dataPath: "/x",
    expectedSchemaVersion: 1,
    columns: SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    fetchFn,
    history,
    storage: makeStorage(),
    location: makeLocation("/bolts", ""),
    nav: { language: "en-US" },
    render,
  });

  await ctrl.start();
  ctrl.dispatch({ type: "setLang", lang: "fi" });
  ctrl.dispatch({ type: "setPos", pos: "d" });
  ctrl.dispatch({ type: "setSort", sortKey: "g", dir: "desc" });

  // Last URL written must still carry lang=fi (langExplicit persists in state)
  const last = history.calls.at(-1);
  assert.match(last, /lang=fi/);
  assert.match(last, /pos=d/);
  assert.match(last, /sort=g/);
});

test("createController: no implicit ?lang= on default load", async () => {
  const render = makeRecorder();
  const history = makeHistory();
  const fetchFn = makeFetchFn({ body: { schemaVersion: 1 } });
  const ctrl = createController({
    dataPath: "/x",
    expectedSchemaVersion: 1,
    columns: SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    fetchFn,
    history,
    storage: makeStorage(),
    location: makeLocation("/bolts", ""),
    nav: { language: "en-US" },
    render,
  });

  await ctrl.start();
  ctrl.dispatch({ type: "setPos", pos: "d" }); // non-lang action; URL must not sprout ?lang=
  const last = history.calls.at(-1);
  assert.doesNotMatch(last, /lang=/);
});

test("createController: HTTP error path — render(state, null, {error: 'http'})", async () => {
  const render = makeRecorder();
  const fetchFn = makeFetchFn({ ok: false, status: 500, body: null });
  const ctrl = createController({
    dataPath: "/x",
    expectedSchemaVersion: 1,
    columns: SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    fetchFn,
    history: makeHistory(),
    storage: makeStorage(),
    location: makeLocation(),
    nav: { language: "en-US" },
    render,
  });

  await ctrl.start();
  assert.equal(render.calls.length, 1);
  assert.equal(render.calls[0].data, null);
  assert.equal(render.calls[0].meta.error, "http");

  // Subsequent dispatches keep rendering with the cached null data — no retry
  ctrl.dispatch({ type: "setLang", lang: "fi" });
  assert.equal(fetchFn.getCallCount(), 1);
  assert.equal(render.calls[1].data, null);
  assert.equal(render.calls[1].meta.error, "http");
});

test("createController: schema mismatch → render(state, null, {error: 'schema'}), no throw", async () => {
  const render = makeRecorder();
  const fetchFn = makeFetchFn({ body: { schemaVersion: 2 } });
  const ctrl = createController({
    dataPath: "/x",
    expectedSchemaVersion: 1,
    columns: SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    fetchFn,
    history: makeHistory(),
    storage: makeStorage(),
    location: makeLocation(),
    nav: { language: "en-US" },
    render,
  });

  await ctrl.start();
  assert.equal(render.calls[0].data, null);
  assert.equal(render.calls[0].meta.error, "schema");
});

test("createController: localStorage.setItem throwing on setLang doesn't break rendering", async () => {
  const render = makeRecorder();
  const storage = makeStorage({ throwOnSet: new Error("quota exceeded") });
  const fetchFn = makeFetchFn({ body: { schemaVersion: 1 } });
  const ctrl = createController({
    dataPath: "/x",
    expectedSchemaVersion: 1,
    columns: SKATER_COLUMNS,
    goalieColumns: GOALIE_COLUMNS,
    fetchFn,
    history: makeHistory(),
    storage,
    location: makeLocation(),
    nav: { language: "en-US" },
    render,
  });

  await ctrl.start();
  // Should not throw
  ctrl.dispatch({ type: "setLang", lang: "fi" });
  assert.equal(render.calls.length, 2);
  assert.equal(render.calls[1].state.lang, "fi");
});
